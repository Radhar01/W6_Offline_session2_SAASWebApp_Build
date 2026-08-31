# backend/Dockerfile
# Multi-stage build for the ClipCreator FastAPI backend.
# Stage 1 compiles Python dependencies (needs build tools + Postgres headers).
# Stage 2 is the slim runtime image; it adds ffmpeg for video processing
# and runs the app as a non-root user.

# ---------- Stage 1: builder ----------
FROM python:3.11-slim AS builder

WORKDIR /app

# Build deps needed to compile psycopg2-binary and friends.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

WORKDIR /app

# ffmpeg is required at runtime for video transcoding/segmentation.
# libpq5 is the runtime (non-dev) Postgres client library for psycopg2-binary.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Bring in compiled Python packages from the builder stage.
COPY --from=builder /install /usr/local

# Application source.
COPY ./app ./app

# alembic migrations, if present at build time (DATABASE-AGENT scaffolds these).
COPY alembic.ini ./alembic.ini
COPY ./alembic ./alembic

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FFMPEG_PATH=/usr/bin/ffmpeg \
    MEDIA_STORAGE_PATH=/app/storage

# Non-root user; own the app dir and the media storage mount point.
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/storage \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
