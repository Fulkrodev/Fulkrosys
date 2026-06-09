# FULKRO — Frontend Next.js 14 · PRODUCCIÓN (Hetzner deploy)
# Multi-stage: deps → build → runtime (next start).
#
# IMPORTANTE (seguridad · honest note):
#   FULKRO_AUTH_PUBLIC_KEY es SERVER-SIDE ONLY (lo lee middleware.ts vía
#   jose.importSPKI con EdDSA · NO lleva prefijo NEXT_PUBLIC_). Por eso NO
#   se inyecta como build-arg sino como variable de entorno en RUNTIME
#   (docker-compose env_file: .env.prod). Inyectarla como build-arg la
#   hornearía en el bundle estático y rompería el modelo de confianza
#   (la clave pública NO debe filtrarse al browser aunque sea "pública":
#   el contrato es que la verificación de JWT ocurre server-side).
#
#   Igual para FULKRO_BACKEND_URL (rewrites proxy /api/* → backend): es
#   runtime (next.config.mjs lo lee de process.env en arranque del server).
#
# Build:
#   docker build -f frontend/Dockerfile -t fulkro/frontend:latest ./frontend
# Run (vía compose):
#   docker compose -f docker-compose.prod.yml up -d frontend

# ─────── Stage 1: deps (cache de node_modules) ───────
FROM node:20-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# ─────── Stage 2: build ───────
FROM node:20-bookworm-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# next build genera .next/ (server + static). No usamos `output: standalone`
# para no alterar next.config.mjs existente; corremos `next start` clásico.
RUN npm run build

# ─────── Stage 3: runtime ───────
FROM node:20-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
# curl para healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root
RUN groupadd --system --gid 1001 nodejs \
    && useradd --system --uid 1001 --gid nodejs nextjs

# Artefactos mínimos para `next start`
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/package-lock.json ./package-lock.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.mjs ./next.config.mjs

USER nextjs
EXPOSE 3000

# Healthcheck: la home / debe responder 200/3xx una vez next start está listo.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:3000/ || exit 1

CMD ["npm", "run", "start"]
