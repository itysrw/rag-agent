FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt ./frontend/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install pip==25.3 \
    && python -m pip install -r frontend/requirements.txt \
    && python -m pip check

RUN groupadd --system rag \
    && useradd --system --gid rag --create-home rag

COPY --from=streamlit_config config.toml ./.streamlit/config.toml
COPY --from=document_formats document_formats.py ./backend/app/document_formats.py
COPY *.py ./frontend/

USER rag
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "frontend/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--browser.gatherUsageStats=false"]
