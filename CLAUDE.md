# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Milestone 1 (paper discovery & ranking) is implemented: a FastAPI backend (`backend/`) and a React + TypeScript frontend (`frontend/`). See the Commands section below. Milestones 2–5 are not yet started.

## What This Is

Research Buddy is a research assistant built in five milestones, each designed and built independently:

1. **Paper discovery & ranking** (current milestone) — query open archives, return top-N papers ranked by relevance + citations + recency.
2. Interactive search refinement.
3. PDF summarization reports.
4. AWS experiment orchestration (provision, run, monitor).
5. Results dashboard.

Only Milestone 1 is in scope right now. Do not build later-milestone functionality unless that milestone has its own approved spec.

## Stack

- **Backend:** Python + FastAPI.
- **Frontend:** React.
- Python is the deliberate choice because later milestones (PDF generation, AWS orchestration, experiment running) live most comfortably there.

## Architecture (Milestone 1)

A **retrieve-then-sort** pipeline behind a FastAPI endpoint. Current design:
`docs/superpowers/specs/2026-06-08-research-buddy-retrieve-then-sort-redesign.md`
(the original weighted-ranking spec is superseded). Focused, independently-testable units:

- **`OpenAlexClient`** — single source for discovery/ranking/citations. `search(query, pool_size)` queries OpenAlex (`/works`, `search=`, filtered to arXiv-hosted works via `primary_location.source.id`), returning `list[SearchResultItem]` with title, authors, published date, arXiv URL, and `cited_by_count` — all in one call (`per-page` caps at 200). Raises `OpenAlexUnavailable`.
- **`ArxivAbstractClient`** — fetches authoritative abstracts from arXiv by `id_list` (chunked at 100), keyed by arXiv id. `SearchService` overlays these onto the pool (OpenAlex's reconstructed abstracts are unreliable). Raises `ArxivAbstractsUnavailable`; abstract failure degrades gracefully (keeps OpenAlex text + warning) — OpenAlex stays the only hard dependency.
- **`Sorter`** — **pure function, no I/O.** `sort_papers(items, sort_key, n)` returns the top N by a single key: `relevance` (input/OpenAlex order), `citations`, or `recency` (stable descending; ties keep relevance order). No weighting, no normalization.
- **`SearchService`** — orchestrates: OpenAlex retrieve (fixed 200 pool) → store full pool under `search_id` → return relevance-order top N. A `resort(search_id, sort_key, n)` path re-sorts the stored pool with no new network calls.
- **`ResultStore`** — in-memory store keyed by `search_id`.

### Load-bearing design decisions (do not violate without updating the spec)

- **OpenAlex is the single source for retrieval *and* sorting.** It provides relevance ranking, citation counts, and dates in one response. (arXiv's own relevance was too weak — it buried canonical papers past rank 300; OpenAlex ranks them near the top.)
- **Retrieve-then-sort, no weighting:** fetch a fixed pool of 200 by relevance, then the user sorts that stored pool by citations or recency (top N, default 10).
- **Re-sort reads the stored pool**, never re-queries — the `search_id` + in-memory store is the seam Milestones 2–3 attach to ("refine search X", "summarize paper 2 from search X"). Preserve it.
- **Graceful failure:** if OpenAlex is down the search returns 503; an empty result set returns a friendly "broaden your query" message, not an error.

## Commands

### Backend (`backend/`)
- Setup: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
- Run: `.venv/bin/uvicorn app.main:app --reload` (http://localhost:8000)
- Test: `.venv/bin/pytest`
- Single test: `.venv/bin/pytest tests/test_sorter.py::test_sort_citations_descending -v`
- Live smoke tests (hit OpenAlex): `.venv/bin/pytest --run-live`
- API: `POST /api/search {query, n}` returns a `search_id` + relevance-ordered results; `GET /api/search/{search_id}?sort=citations|recency&n=10` re-sorts the stored pool. Set `OPENALEX_MAILTO` to use OpenAlex's faster polite pool.

### Frontend (`frontend/`)
- Setup: `npm install`
- Run: `npm run dev` (http://localhost:5173)
- Test: `npm test`
- Build: `npm run build`
