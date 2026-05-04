# syntax=docker/dockerfile:1.7
#
# Multi-stage build:
#   - build: produce el bundle de producción en /app/dist
#   - dev:   dev server con hot-reload (target por defecto en compose)
#   - prod:  sirve /app/dist con `serve` de Vercel (sin nginx)
#
# Comandos:
#   Dev (default):
#     docker compose --profile app build frontend
#     docker compose --profile app up -d frontend
#
#   Prod (manual, no usa compose):
#     docker build -t rag-da-frontend:prod --target prod ./frontend
#     docker run --rm -p 5173:5173 rag-da-frontend:prod

# ── Stage 1: builder ──────────────────────────────────────────────────────
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ── Stage 2: dev server (hot reload) ──────────────────────────────────────
FROM node:24-alpine AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# ── Stage 3: prod static server (sin nginx) ───────────────────────────────
FROM node:24-alpine AS prod
WORKDIR /app
RUN npm install -g serve@14 && npm cache clean --force
COPY --from=build /app/dist ./dist
EXPOSE 5173
# `serve -s` activa fallback a index.html (SPA-safe).
# `-l 5173` mantiene el mismo puerto que el dev server.
CMD ["serve", "-s", "dist", "-l", "5173"]
