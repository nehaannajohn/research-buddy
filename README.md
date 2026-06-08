# Research Buddy

Milestone 1: paper discovery & ranking. A FastAPI backend retrieves the top 200
arXiv papers for a query from OpenAlex (which provides relevance ranking,
citation counts, and dates in one call), and the React frontend lets the user
re-sort that pool by citations or recency and shows the top N (default 10).

OpenAlex needs no API key. Set the optional `OPENALEX_MAILTO` env var to your
email to use OpenAlex's faster "polite pool".

## Backend

    cd backend
    python3 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
    .venv/bin/uvicorn app.main:app --reload   # serves http://localhost:8000

Run tests: `.venv/bin/pytest`
Run live smoke tests (hits real APIs): `.venv/bin/pytest --run-live`
Run a single test: `.venv/bin/pytest tests/test_ranker.py::test_final_score_applies_weights -v`

## Frontend

    cd frontend
    npm install
    npm run dev   # serves http://localhost:5173

Run tests: `npm test`
Build: `npm run build`
