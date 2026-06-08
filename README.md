# Research Buddy

Milestone 1: paper discovery & ranking. A FastAPI backend queries arXiv and
Semantic Scholar, ranks results by relevance + citations + recency, and a React
frontend renders ranked result cards with per-signal score breakdowns.

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
