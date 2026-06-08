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

A two-stage data pipeline behind a FastAPI endpoint. Four focused, independently-testable units:

- **`ArxivClient`** — calls the arXiv API (relevance-sorted) for a candidate pool; returns paper metadata + relevance rank. Provides the **relevance** and **recency** signals.
- **`CitationClient`** — batch-looks-up arXiv IDs in OpenAlex by arXiv DOI (`10.48550/arXiv.<id>`, OR-filtered ≤50 per request) for **citation counts** (`cited_by_count`). Unmatched IDs → 0, flagged. (Originally Semantic Scholar — swapped to OpenAlex; see the design spec's provider note.)
- **`Ranker`** — **pure function, no I/O.** Normalizes each signal to 0–1 and computes `score = 0.5·relevance + 0.3·citations + 0.2·recency` (weights overridable). Returns the sorted top-N. Keep it I/O-free so it stays unit-testable in isolation.
- **`SearchService`** — orchestrates arXiv → enrich → rank → return.

### Load-bearing design decisions (do not violate without updating the spec)

- **Two-stage sourcing:** arXiv finds candidates, the citation source (OpenAlex) only enriches with citations. Fetch a wide pool (`max(50, N×5)`) from arXiv, *then* narrow to top-N after enrichment.
- **Citations are log-scaled before normalizing** — citation counts are heavily skewed; log-scaling stops a few blockbuster papers from flattening everyone else.
- **Citation enrichment is additive, never a hard dependency.** If the citation source fails or rate-limits, degrade gracefully: return arXiv results ranked on relevance + recency only, with a warning. The search must still succeed.
- **Sub-scores are returned to the UI**, not just the final score, so result cards can show *why* a paper ranked where it did.
- **`search_id` + server-side result store** (in-memory for v1) is a deliberate seam. Milestones 2–3 attach to it ("refine search X", "summarize paper 2 from search X") to avoid re-running the pipeline. Preserve it.

## Commands

### Backend (`backend/`)
- Setup: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
- Run: `.venv/bin/uvicorn app.main:app --reload` (http://localhost:8000)
- Test: `.venv/bin/pytest`
- Single test: `.venv/bin/pytest tests/test_ranker.py::test_final_score_applies_weights -v`
- Live smoke tests: `.venv/bin/pytest --run-live`

### Frontend (`frontend/`)
- Setup: `npm install`
- Run: `npm run dev` (http://localhost:5173)
- Test: `npm test`
- Build: `npm run build`
