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
#   CORREGIDO 2026-09-10 (bloque D · D3). Aquí ponía que FULKRO_BACKEND_URL
#   también era runtime, "porque next.config.mjs lo lee de process.env en el
#   arranque del server". Es FALSO y estaba rompiendo el demo entero:
#
#     $ docker exec fulkro-demo-frontend-1 sh -lc 'echo $FULKRO_BACKEND_URL'
#     http://backend:8000                      <- la variable SÍ estaba bien
#     $ docker exec fulkro-demo-frontend-1 node -e \
#         "console.log(require('/app/.next/routes-manifest.json').rewrites)"
#     [{ source: '/api/:path*',
#        destination: 'http://localhost:8000/api/:path*' }]   <- horneado
#     $ docker logs fulkro-demo-frontend-1 | tail
#     Failed to proxy http://localhost:8000/api/v1/auth/login ECONNREFUSED
#
#   `next build` SERIALIZA el destino de los rewrites en
#   .next/routes-manifest.json, y `next start` usa el manifiesto, no vuelve a
#   evaluar la función. Consecuencia: en el demo NO se podía ni entrar por la
#   web (el POST de /login devolvía 500), aunque la API respondiera perfecta
#   en su puerto. Por eso ahora es un ARG de construcción, con verificación
#   inmediata al terminar el build (más abajo).
#
#   FULKRO_AUTH_PUBLIC_KEY sí sigue siendo runtime de verdad: middleware.ts la
#   lee de process.env en cada petición.
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

# Destino del proxy /api/* → backend. Es BUILD-TIME (ver la nota de arriba).
# El default es el nombre del servicio en compose, para que un `docker build`
# a secas produzca ya una imagen que funciona dentro de la red de compose.
# Se sobrescribe con `--build-arg FULKRO_BACKEND_URL=...` o con `build.args`.
ARG FULKRO_BACKEND_URL=http://backend:8000
ENV FULKRO_BACKEND_URL=${FULKRO_BACKEND_URL}

# next build genera .next/ (server + static). No usamos `output: standalone`
# para no alterar next.config.mjs existente; corremos `next start` clásico.
RUN npm run build

# Guardia: si el destino horneado apunta a localhost, la imagen no sirve dentro
# de un contenedor (localhost seria el propio Next.js) y el fallo se manifiesta
# como un 500 opaco en el primer POST. Que reviente aqui y no en produccion.
RUN node scripts/verificar-proxy-api.js

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
