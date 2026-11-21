FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TIKTOKEN_CACHE_DIR=/app/data/tiktoken-cache

WORKDIR /app

COPY requirements.txt ./backend/requirements.txt
# BGE embedding and reranking run on CPU.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install pip==25.3 \
    && python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.13.0 \
    && python -m pip install -r backend/requirements.txt \
    && python -m pip check

RUN groupadd --system rag \
    && useradd --system --gid rag --create-home rag \
    && mkdir -p /app/data/uploads /app/data/models /app/data/tiktoken-cache \
    && chown -R rag:rag /app/data

COPY app ./backend/app

USER rag
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
