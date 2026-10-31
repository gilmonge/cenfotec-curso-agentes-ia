#!/bin/bash
# Arranque dentro del contenedor: OpenCode (solo interno) + backend FastAPI (público).
# Los secretos llegan por variables de entorno; no se imprimen.
set -eu

DATOS="${DATA_DIR:-/var/data}"
mkdir -p "$DATOS/opencode"
export XDG_DATA_HOME="$DATOS/opencode"
export ANALISTA_REPO_DB="${ANALISTA_REPO_DB:-$DATOS/repositorio.db}"
export OPENCODE_SERVER_URL="${OPENCODE_SERVER_URL:-http://127.0.0.1:4096}"

: "${OPENCODE_SERVER_PASSWORD:?Falta OPENCODE_SERVER_PASSWORD}"

# Credencial del proveedor del modelo (OpenCode Go). Se escribe en el formato de auth.json.
if [ -n "${OPENCODE_API_KEY:-}" ]; then
  umask 077
  mkdir -p "$XDG_DATA_HOME/opencode"
  python - <<'PY'
import json, os
ruta = os.path.join(os.environ["XDG_DATA_HOME"], "opencode", "auth.json")
clave = os.environ["OPENCODE_API_KEY"].strip()
datos = {proveedor: {"type": "api", "key": clave} for proveedor in ("opencode", "opencode-go")}
with open(ruta, "w", encoding="utf-8") as archivo:
    json.dump(datos, archivo)
PY
else
  echo "Aviso: OPENCODE_API_KEY no está definida; el agente no podrá usar el modelo." >&2
fi

# OpenCode debe arrancar desde la raíz del proyecto para cargar opencode.jsonc y el prompt.
cd /app
"${OPENCODE_BIN:-opencode}" serve --hostname 127.0.0.1 --port 4096 &
PID_OPENCODE=$!

python -m uvicorn agentes.analista.api.main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 &
PID_API=$!

terminar() { kill "$PID_OPENCODE" "$PID_API" 2>/dev/null || true; }
trap terminar TERM INT

# Si cualquiera de los dos procesos se cae, el contenedor termina y el hosting lo reinicia.
wait -n "$PID_OPENCODE" "$PID_API"
CODIGO=$?
terminar
exit "$CODIGO"
