# ── AlphaMind backend (FastAPI) ──────────────────────────────────────────────
# Multi-stage: build wheels, then a slim non-root runtime.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt gunicorn uvicorn[standard]


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    LOG_JSON=true ENVIRONMENT=production API_HOST=0.0.0.0 API_PORT=8000
WORKDIR /app

# Non-root user
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels \
    -r requirements.txt gunicorn uvicorn[standard] && rm -rf /wheels

COPY alphamind ./alphamind
COPY api ./api

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

# Gunicorn with uvicorn workers for production concurrency.
CMD ["gunicorn", "api.main:app", "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-"]
