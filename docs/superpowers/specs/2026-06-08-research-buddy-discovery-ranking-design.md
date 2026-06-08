# Research Buddy — Milestone 1: Paper Discovery & Ranking

> ⚠️ **SUPERSEDED (2026-06-08).** This original design used a weighted score
> (relevance/citations/recency with sliders) and Semantic Scholar for citations.
> Both have been replaced. The current Milestone 1 design is
> **[`2026-06-08-research-buddy-retrieve-then-sort-redesign.md`](2026-06-08-research-buddy-retrieve-then-sort-redesign.md)**
> (retrieve top 200 by relevance → user sorts by citations or recency; no
> weighting; OpenAlex for citations). This file is kept only for historical
> context — do not implement from it.

**Date:** 2026-06-08
**Status:** Superseded — see the retrieve-then-sort redesign
**Scope:** First of five milestones. This milestone covers paper discovery and ranking only. Later milestones (interactive refinement, PDF summarization, AWS experiment orchestration, results dashboard) each get their own design → plan → build cycle.

## Goal

Given a free-text research prompt (e.g. "scaling laws") and a number N, return the top N papers from open archives, ranked by a weighted combination of **relevance**, **citation count**, and **recency**.

## Ranking Philosophy

Three signals, combined as a weighted score after each is normalized to 0–1:

```
score = w_rel · relevance + w_cit · citations + w_rec · recency
```

Default weights reflect the priority **relevance > citations > recency**:

- `w_rel = 0.5`
- `w_cit = 0.3`
- `w_rec = 0.2`

Weights are overridable per search (UI sliders) so the user can experiment.

## Data Sources (two-stage)

1. **arXiv API — candidate finder.** Full-text relevance search against the query, sorted by relevance. Returns matching papers with arXiv ID, title, authors, abstract, published date, arXiv URL, and relevance rank. Provides the **relevance** and **recency** signals.
2. **Semantic Scholar — enricher.** Batch lookup of the arXiv IDs (accepts `ARXIV:<id>`, has a batch endpoint) to attach **citation counts**.

We fetch a wider candidate pool from arXiv — `max(50, N × 5)` — then narrow to the top N *after* citation enrichment, so the citation ranking has real depth to work with.

## Signal Normalization

- **relevance** — derived from arXiv result rank (top candidate = 1.0, scaled down by position). May upgrade to embedding-based similarity later if too coarse (YAGNI for v1).
- **citations** — **log-scaled then normalized** across the pool. Citation counts are heavily skewed; log-scaling compresses the top end so a few blockbuster papers don't flatten the meaningful differences among normal-but-strong papers. Each paper's `log(citations)` is mapped to 0–1 relative to the pool max.
- **recency** — newer = higher, normalized across the pool's publication-date range.

## Architecture & Components

A FastAPI backend exposing a search API, a React frontend (search box + result cards), and an internal pipeline of focused, independently-testable units:

- **`ArxivClient`** — query + pool size → candidate papers (arXiv ID, title, authors, abstract, published date, arXiv URL, relevance rank).
- **`CitationClient`** — list of arXiv IDs → `{arxiv_id → citation_count}` via Semantic Scholar batch call. Unmatched IDs → citation count 0, flagged.
- **`Ranker`** — **pure function** (no I/O). Candidates + citation data + weights → normalized, scored, sorted top-N. Trivially unit-testable.
- **`SearchService`** — orchestrates: arXiv → enrich → rank → return. Called by the API endpoint.

Each unit has one job and communicates through plain data structures, so the `Ranker` is testable without network calls and either data source can be swapped later.

## Data Flow

1. User submits **query** + **N** + optional **weights** from the React UI.
2. `SearchService` asks `ArxivClient` for a candidate pool of `max(50, N × 5)`.
3. `CitationClient` batch-enriches candidates with Semantic Scholar citation counts (one batched call; unresolved IDs → 0, flagged).
4. `Ranker` normalizes the three signals, computes the weighted score, returns the top N with full metadata **plus the individual sub-scores** (so the UI can show *why* a paper ranked where it did).
5. `SearchService` returns the result set.

## API (FastAPI)

- `POST /api/search` — body `{ query, n, weights? }` → returns `{ search_id, results: [...], pool_size, warnings }`.
  - Each result: title, authors, abstract, published date, arXiv URL, citation count, the three sub-scores, final score, and a citation-data-missing flag.
- Each search gets a **`search_id`**; the result set is held **server-side (in-memory store for v1)**. Not needed for ranking itself — it is the hook milestones 2–3 bolt onto ("refine search X", "summarize paper 2 from search X") without re-running the pipeline.

## Frontend (React)

- **Search bar**: query input + "how many results" number input.
- **Advanced panel** (optional): three weight sliders, defaulting 0.5 / 0.3 / 0.2.
- **Result cards**: title (linked to arXiv), authors, date, citation count, and a small score breakdown showing the three sub-scores. A flag badge appears when citation data was missing.
- Loading, empty, and error states.

## Error Handling

External failure modes dominate:

- **arXiv returns nothing** → empty result set with a clear "no matches, try broadening your query" message (not an error).
- **arXiv down / times out** → clean "search source unavailable, retry" error; one retry with backoff before giving up.
- **Semantic Scholar fails / rate-limits** → **degrade gracefully**: still return arXiv results ranked on relevance + recency only, with a warning that citation data was unavailable. Citation enrichment is additive, never a hard dependency.
- **Some papers missing citation data** → citation 0 + per-card flag.

## Testing

- **`Ranker`** — heavily unit-tested (pure function): log-scaling, normalization edge cases (all-same citations, single result, zero citations), weight application, correct top-N ordering.
- **`ArxivClient` / `CitationClient`** — unit-tested against recorded/mocked API responses (no live calls in the default run), including failure and partial-data paths.
- **`SearchService`** — integration test with both clients mocked, asserting graceful degradation when Semantic Scholar fails.
- **Live smoke tests** — opt-in (not in the default run), hitting the real APIs to catch upstream changes.

## Out of Scope (future milestones)

- Interactive refinement (re-running discovery with a narrowed query).
- PDF summarization reports.
- AWS experiment orchestration (provision, run, monitor).
- Results dashboard.

The `search_id` + server-side result store is the deliberate seam that lets those milestones attach cleanly.

## Amendment — Citation source: Semantic Scholar → OpenAlex (2026-06-08)

During implementation, Semantic Scholar's unauthenticated batch endpoint proved
unreliable: its rate limit is a 5,000-requests-per-5-minutes pool *shared across
all anonymous callers*, so live searches intermittently failed with HTTP 429. We
swapped the citation source to **OpenAlex**, which needs no API key and offers far
more generous limits.

The two-stage design made this a contained change — only `CitationClient`'s
internals changed; its interface (`get_citation_counts(arxiv_ids) -> {arxiv_id:
count}`, raising `CitationUnavailable`), and therefore `Ranker`, `SearchService`,
and the API, were untouched.

OpenAlex specifics:
- Looked up by arXiv DOI (`10.48550/arXiv.<id>`), OR-filtered up to 50 IDs per
  request; citation count read from `cited_by_count`.
- IDs OpenAlex doesn't resolve (e.g. preprints deduped into their published
  version) are omitted and treated as missing — identical to the prior behavior.
- Optional `OPENALEX_MAILTO` env var opts into OpenAlex's faster "polite pool".

Everything else in this design (signals, weights, normalization, graceful
degradation, the `search_id` seam) is unchanged.
