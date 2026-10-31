# Imagen única: interfaz React compilada + backend FastAPI + OpenCode Server 2.1.2.
# Se publica como un solo servicio con un solo URL (ver DESPLIEGUE.md).

# 1) Compila la interfaz
FROM node:22-slim AS interfaz
WORKDIR /compilacion
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
# Valores de compilación (Render los entrega como argumentos si están definidos en Environment).
ARG VITE_PREFIJO_HU
ARG VITE_ANIO
ARG VITE_VERSION
COPY index.html vite.config.js ./
COPY src ./src
RUN npm run build

# 2) Instala OpenCode en la versión validada por el backend
FROM node:22-slim AS opencode
RUN npm install --prefix /opt/opencode --no-audit --no-fund @opencode/cli@2.1.2

# 3) Imagen final
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 MALLOC_ARENA_MAX=2
RUN useradd --create-home --uid 1000 app && mkdir -p /var/data && chown app:app /var/data
WORKDIR /app

COPY agentes/analista/requirements.txt agentes/analista/requirements.txt
RUN pip install -r agentes/analista/requirements.txt

COPY --from=opencode /usr/local/bin/node /usr/local/bin/node
COPY --from=opencode /opt/opencode /opt/opencode
COPY --from=interfaz /compilacion/dist ./dist
COPY agentes ./agentes
COPY .agents ./.agents
COPY opencode.jsonc ./opencode.jsonc
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && chown -R app:app /app

USER app
ENV DATA_DIR=/var/data OPENCODE_BIN=/opt/opencode/node_modules/.bin/opencode
EXPOSE 10000
CMD ["/usr/local/bin/docker-entrypoint.sh"]
