# Research Buddy — Milestone 1 Redesign: Retrieve-then-Sort Discovery

**Date:** 2026-06-08
**Status:** Approved design
**Supersedes:** the weighted-ranking approach in
`2026-06-08-research-buddy-discovery-ranking-design.md` (and its OpenAlex
amendment). The discovery/two-stage-sourcing and OpenAlex citation-source
decisions from that document still hold; only the *ranking* model changes.

## Why this redesign

The original design combined relevance, citations, and recency into a single
weighted score (`0.5·rel + 0.3·cit + 0.2·rec`, weights overridable via sliders).
In use, this proved both hard to reason about and ineffective at its core goal:

- **Relevance was position-based** (a paper's rank in arXiv's relevance results),
  which is coarse. Canonical papers fall outside arXiv's top results entirely —
  e.g. "Scaling Laws for Neural Language Models" (arXiv:2001.08361) sits at
  arXiv-rank ~335 for the query "scaling laws", so no weighting could surface it.
- **Blending three normalized signals into one number** made it unclear *why* a
  paper ranked where it did, and tuning weights was guesswork.

The new model is a transparent two-stage process: cast a wide net by relevance,
then let the user sort that net by a single, concrete dimension.

## The model

1. **Retrieve (relevance):** Query arXiv (relevance-sorted) and take the top
   **200** candidates. This is the eligible pool. Casting wide (200 vs the old
   ~50) means high-impact papers buried in arXiv's relevance order are still
   included for the sort stage to surface.
2. **Enrich (once):** Fetch OpenAlex citation counts for **all 200** candidates
   and store the enriched pool server-side under a `search_id`.
3. **Sort (user choice):** The user sorts the stored pool by **citations**
   (most-cited first) or **recency** (newest first), and sees the top **N**
   (configurable, default 10). The initial view is arXiv **relevance order**.

There is **no weighting, no normalization, and no composite score.** Sorting is
by a single raw field. Re-sorting reorders the already-stored, already-enriched
pool with **no new network calls**.

## Components

- **`ArxivClient`** — unchanged. Query + pool size → candidate papers with
  relevance rank (0-based, = arXiv order). Pool size is now a fixed 200.
- **`CitationClient`** — unchanged. OpenAlex lookup by arXiv DOI, chunked at 50
  per request (200 candidates = 4 requests). Returns `{arxiv_id: count}`;
  unmatched IDs omitted (treated as missing).
- **`Sorter`** (replaces `Ranker`) — **pure function, no I/O.**
  `sort_papers(papers, sort_key, n) -> list[ResultItem]` where
  `sort_key ∈ {"relevance", "citations", "recency"}`:
  - `relevance` → original arXiv order (identity; the list is already in rank order).
  - `citations` → stable sort by `citation_count` descending.
  - `recency` → stable sort by `published` descending.
  - All sorts are **stable**, so ties preserve the underlying arXiv relevance
    order (e.g. many papers with 0 citations stay in relevance order).
  - Returns the top `n`.
- **`ResultStore`** — unchanged interface (`save`/`get`), now actively used by the
  re-sort path. In-memory for v1 (pool is lost on restart).
- **`SearchService`** — orchestrates: arXiv (200) → enrich all → store →
  return relevance-order top N. Plus a re-sort path: read stored pool → sort → top N.

## Removed from the previous design

- `Weights` model and the three weight sliders.
- Weighted/normalized scoring; per-signal normalization (log-scaling, date-range,
  rank-scaling).
- `SubScores` and `final_score` on results, and the per-card score breakdown in
  the UI. Ordering is self-evident from the chosen sort, so no "why it ranked
  here" breakdown is needed.

## Data shapes

`ResultItem` (returned to the UI):
- `arxiv_id`, `title`, `authors`, `abstract`, `published` (ISO date), `url`,
  `citation_count` (int), `citation_data_missing` (bool).

(No `sub_scores`, no `final_score`.)

## API (FastAPI)

- `POST /api/search` — body `{ query, n? }` (n default 10) →
  `{ search_id, results, pool_size, warnings }`.
  - Retrieves 200, enriches all, stores under `search_id`, returns the top `n` in
    **relevance order**. `pool_size` is the number of candidates actually stored
    (≤ 200; arXiv may return fewer).
- `GET /api/search/{search_id}` — query params `sort` (`citations` | `recency` |
  `relevance`, default `relevance`) and `n` (default 10) →
  `{ search_id, results, warnings }`.
  - Reads the stored pool, sorts by `sort`, returns top `n`. **No network calls.**
  - **404** if `search_id` is unknown or expired (in-memory store lost on restart).
  - Invalid `sort` value → 422 (FastAPI validation).

This `GET /api/search/{search_id}` endpoint is the first concrete use of the
`search_id` + store seam, and previews the attach pattern for Milestones 2–3.

## Frontend (React)

- **Search bar:** query input + a result-count selector (5 / 10 / 25, default 10).
  (The weight sliders are removed.)
- **Sort control:** a two-option toggle — **Citations** and **Recency**. The
  initial results render in relevance order (as returned by the POST); choosing a
  toggle calls the GET re-sort endpoint. There is intentionally no UI control to
  return to relevance order once a sort is chosen.
- **Result cards:** title (linked to arXiv), authors, published date,
  citation count, and a flag badge when citation data is missing. No score
  breakdown.
- Changing the sort toggle or the result-count selector issues
  `GET /api/search/{search_id}?sort=…&n=…` and re-renders. If the stored search
  has expired (404), prompt the user to search again.
- Loading, empty, and error states.

## Error handling

- **arXiv returns nothing** → empty results with a friendly "no matches, try
  broadening your query" message (not an error).
- **arXiv down / times out** → 503 "search source unavailable, please retry"
  (one retry with backoff in the client before giving up).
- **OpenAlex fails during enrichment** → degrade gracefully: store the pool with
  citation counts missing (every paper flagged, count 0), and attach a warning
  ("citation data unavailable — sorting by citations may be incomplete"). The
  search still succeeds. Recency and relevance sorts are unaffected; a citations
  sort falls back to relevance order (all-equal counts, stable sort).
- **Re-sort with an unknown/expired `search_id`** → 404 "search expired, please
  search again."

## Testing

- **`Sorter`** — heavily unit-tested (pure function): citations-desc ordering,
  recency-desc ordering, relevance identity, stable tie-breaking (equal citation
  counts keep relevance order), top-N truncation, N greater than pool size, empty
  pool.
- **`ArxivClient` / `CitationClient`** — unit-tested against recorded/mocked
  responses (unchanged behavior; clients are reused as-is).
- **`SearchService`** — retrieves 200 and enriches all then stores; returns
  relevance order from `POST`; re-sort path returns correctly ordered results
  from the store; graceful degradation when OpenAlex fails.
- **Re-sort endpoint** — correct re-ordering for each sort key; 404 on unknown
  `search_id`; 422 on invalid `sort`.
- **Frontend** — sort toggle and count selector call the GET endpoint with the
  right params and re-render; expired-search (404) handling.
- **Live smoke tests** — opt-in (unchanged): real arXiv retrieval and real
  OpenAlex citation lookup.

## Out of scope (unchanged from the original milestone)

Interactive query refinement, PDF summarization, AWS experiment orchestration,
results dashboard. The `search_id` + store seam remains the attach point for
Milestones 2–3.

## Amendment — OpenAlex as the single source (retrieval + sorting) (2026-06-08)

The retrieve-by-arXiv design above hit a wall: arXiv's relevance ranking is weak.
For "scaling laws", arXiv ranks the canonical "Scaling Laws for Neural Language
Models" at position **335** (out of 434,384 keyword matches) — outside any
reasonable pool — so the citation sort could never surface it. Measured against
the same query, **OpenAlex ranks that paper #1**, because its relevance model
folds in impact signals.

So retrieval moves to **OpenAlex as the single source**: it provides relevance
ranking, citation counts, and publication dates in one response. arXiv's API is
no longer called.

**Retrieval:** `GET https://api.openalex.org/works` with `search=<query>`,
`filter=primary_location.source.id:s4306400194` (arXiv-hosted works only),
`per-page=200` (OpenAlex's max; one call — no pagination needed), and a `select`
of `doi,title,authorships,publication_date,cited_by_count,abstract_inverted_index,primary_location`.
Results come back in OpenAlex relevance order. Optional `mailto` (from
`OPENALEX_MAILTO`) for the polite pool.

**Mapping a work → `SearchResultItem`:** `arxiv_id` from the DOI
(`10.48550/arXiv.<id>`); `url` from `primary_location.landing_page_url`; `authors`
from `authorships[].author.display_name`; `published` parsed from
`publication_date`; `citation_count` from `cited_by_count`; `abstract`
reconstructed from `abstract_inverted_index` (word→positions). Works without an
arXiv DOI are skipped.

**Components changed:**
- **New `OpenAlexClient`** — `search(query, pool_size) -> list[SearchResultItem]`;
  raises `OpenAlexUnavailable`. Includes the abstract-reconstruction helper.
- **`ArxivClient` and the DOI-roundtrip `CitationClient` are removed** (along with
  their tests and the arXiv XML fixture). One source, one call.
- **`Sorter`** keeps `sort_papers`; `build_result_items` is removed (the client now
  produces `SearchResultItem` directly). `CandidatePaper` model is removed.
- **`SearchService`** takes a single `openalex_client` + `store`. `OpenAlexUnavailable`
  → `SearchSourceUnavailable` (503). Empty results → "broaden" warning.
- **Error handling simplifies:** there is no longer a separate citation-enrichment
  step, so the "citations unavailable, degrade with warning" path goes away — if
  OpenAlex is down the search fails (503). `citation_data_missing` is retained on
  `SearchResultItem` (always `False` here) so the result shape and frontend are
  unchanged.

**Unchanged:** `sort_papers`, `ResultStore`, the `resort()` path, the
`POST /api/search` + `GET /api/search/{search_id}` endpoints, and the entire
frontend. `POOL_SIZE` stays 200 (ample, since OpenAlex ranks canonical papers
near the top). The trade-offs: OpenAlex can lag arXiv by a few days for
brand-new papers, and abstracts require reconstruction from the inverted index.

## Amendment — Authoritative abstracts from arXiv (2026-06-08)

OpenAlex's `abstract_inverted_index` is occasionally wrong (observed: the record
for arXiv:2001.08361 reconstructs to an unrelated abstract). Since correct
abstracts matter for the result cards, we keep OpenAlex for identifying / ranking /
citing records, but fetch **authoritative abstracts from arXiv**.

**New `ArxivAbstractClient`** — `get_abstracts(arxiv_ids) -> {arxiv_id: abstract}`.
Calls the arXiv API by `id_list` (chunked at 100 ids/request; `max_results=len`),
parses each entry's `summary` (whitespace-normalized), keying by the bare arXiv id
(version suffix stripped). HTTPS + follow-redirects. Empty input → `{}` (no call).
HTTP error → `ArxivAbstractsUnavailable`.

**Wiring:** `SearchService(openalex_client, abstract_client, store)`. After OpenAlex
returns the pool, fetch arXiv abstracts for the pool's ids and overlay them onto
each `SearchResultItem` (replacing the OpenAlex-reconstructed abstract). This
overlay happens once, at search time, before the pool is stored — so re-sorting
still reads correct abstracts from the store with no new calls.

**Graceful degradation:** if `ArxivAbstractsUnavailable`, keep the OpenAlex
abstract as a fallback and attach a warning ("Abstracts may be incomplete"). The
search still succeeds. (OpenAlex remains the only hard dependency: if OpenAlex is
down → 503; arXiv affects only abstract text.)

This adds one (chunked) arXiv call per search; re-sort is unaffected.
