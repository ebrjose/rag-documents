# syntax=docker/dockerfile:1.7
#
# Multi-stage build:
#   - base:           backend FastAPI + dependencias (target por defecto en compose)
#   - frontend-build: compila el SPA (Vite) en /app/dist
#   - prod:           backend + dist baked-in, sirve `/api` y la SPA en `/`
#
# Comandos:
#   Dev (default, sólo backend):
#     docker compose --profile app build backend
#     docker compose --profile app up -d backend
#
#   Prod (backend + frontend en una sola imagen):
#     docker compose --profile prod build backend-prod
#     docker compose --profile prod up -d
#

# ── Stage: base (backend stand-alone, target dev) ─────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Sistema: build tools + libs nativas que necesitan PyMuPDF, Pillow, OpenCV (Surya).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY backend ./backend

ENV HOME=/root \
    HF_HOME=/root/.cache/huggingface

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]


# ── Stage: frontend-build (sólo usado por prod) ───────────────────────────
FROM node:24-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ── Stage: prod (base + SPA baked-in) ─────────────────────────────────────
FROM base AS prod
COPY --from=frontend-build /app/dist /app/static
ENV STATIC_DIR=/app/static
