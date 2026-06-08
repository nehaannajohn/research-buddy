# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Early stage. The Milestone 1 design is approved (`docs/superpowers/specs/2026-06-08-research-buddy-discovery-ranking-design.md`) but code is not yet scaffolded. When scaffolding, update the Commands section below with the real commands.

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
- **`CitationClient`** — batch-looks-up arXiv IDs in Semantic Scholar (`ARXIV:<id>`) for **citation counts**. Unmatched IDs → 0, flagged.
- **`Ranker`** — **pure function, no I/O.** Normalizes each signal to 0–1 and computes `score = 0.5·relevance + 0.3·citations + 0.2·recency` (weights overridable). Returns the sorted top-N. Keep it I/O-free so it stays unit-testable in isolation.
- **`SearchService`** — orchestrates arXiv → enrich → rank → return.

### Load-bearing design decisions (do not violate without updating the spec)

- **Two-stage sourcing:** arXiv finds candidates, Semantic Scholar only enriches with citations. Fetch a wide pool (`max(50, N×5)`) from arXiv, *then* narrow to top-N after enrichment.
- **Citations are log-scaled before normalizing** — citation counts are heavily skewed; log-scaling stops a few blockbuster papers from flattening everyone else.
- **Citation enrichment is additive, never a hard dependency.** If Semantic Scholar fails or rate-limits, degrade gracefully: return arXiv results ranked on relevance + recency only, with a warning. The search must still succeed.
- **Sub-scores are returned to the UI**, not just the final score, so result cards can show *why* a paper ranked where it did.
- **`search_id` + server-side result store** (in-memory for v1) is a deliberate seam. Milestones 2–3 attach to it ("refine search X", "summarize paper 2 from search X") to avoid re-running the pipeline. Preserve it.

## Commands

Pending scaffolding — fill in once the backend and frontend exist (build, test, run, single-test). Until then there are no project commands.
