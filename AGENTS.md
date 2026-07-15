# AGENTS.md

## Project

Enterprise knowledge-base RAG Agent built with FastAPI, LangGraph,
PostgreSQL, Qdrant and Streamlit.

## Development rules

- Use Python 3.11.
- Backend code lives under backend/.
- Do not implement features beyond the requested PLAN.md day.
- Use type hints for public functions.
- Use pytest for tests.
- Run pytest before completing a task.
- Never commit .env or API keys.
- Do not modify PLAN.md unless explicitly requested.

## Commands

Install:
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt

Run backend:
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload

Test:
.\.venv\Scripts\python.exe -m pytest backend/tests -v
