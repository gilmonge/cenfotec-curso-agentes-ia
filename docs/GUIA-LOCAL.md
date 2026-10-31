
# Guía de ejecución local — Historias de Usuario / Agente Analista

  

**Proyecto:**  `cenfotec-curso-agentes-ia`

**Entorno:** Windows + PowerShell

**Arquitectura:** React/Vite → FastAPI (Python) → LangChain/MCP → OpenCode Server v2 → proveedor/modelo configurado en OpenCode.

  

> **Importante:** La aplicación utiliza **OpenCode Server** como única interfaz de generación de IA. **No es necesario iniciar Ollama** ni un servidor MCP por separado: según el quickstart del proyecto, MCP se inicia por turno desde el backend. El servidor puede estar correctamente conectado y, aun así, no generar respuestas si OpenCode devuelve `429 provider.quota`.

> Para publicar la aplicación con un URL y variables de entorno en un hosting, consulte [DESPLIEGUE.md](DESPLIEGUE.md).

## Inicio rápido (un solo comando)

Después de la instalación inicial (secciones siguientes: entorno de Python, OpenCode 2.1.2, `.env` en la raíz y `opencode auth login`), el entorno completo se levanta con:

```powershell
npm run iniciar          # o: .\scripts\entorno\iniciar-entorno.ps1
```

Abre una ventana por servicio (OpenCode, backend FastAPI y frontend Vite), espera a que cada puerto responda y muestra el estado del agente. Opciones:

- `.\scripts\entorno\iniciar-entorno.ps1 -Reiniciar`: cierra lo que esté usando los puertos 4096, 8000 y 3000 y vuelve a iniciar todo (úselo después de cambiar el `.env`).
- `npm run detener` o `.\scripts\entorno\detener-entorno.ps1`: cierra los tres servicios.

Si PowerShell bloquea el script, `npm run iniciar` ya lo ejecuta con `-ExecutionPolicy Bypass`.

  

## 1. Requisitos previos

  

- Node.js y npm instalados.

- Python **3.12** instalado (en este equipo también hay Python 3.14; utilizar expresamente 3.12).

- OpenCode **2.1.2** instalado de forma temporal para este proyecto, con un proveedor/modelo autorizado. No hace falta reemplazar la versión global de OpenCode.

- Trabajar desde la **raíz del repositorio**  `cenfotec-curso-agentes-ia`.

- Mantener un archivo **`.env` en la raíz** (ignorado por Git), con la configuración que necesita el backend.

  

Comprobar instalaciones:

  

```powershell
node --version
npm --version
py -3.12 --version
# La versión temporal de OpenCode se comprueba en la preparación inicial.
```

  

### Preparación inicial (solo la primera vez o si faltan dependencias)

  

**Frontend** (desde la raíz):

  

```powershell
# Si existe package-lock.json:
npm ci

# Si no existe package-lock.json, usar en su lugar:
# npm install
```

  

**Backend Python** (desde la raíz):

  

```powershell

# Crear únicamente si no existe ya el entorno virtual:
py -3.12 -m venv agentes\analista\.venv

# Instalar o actualizar las dependencias declaradas por el proyecto:
& .\agentes\analista\.venv\Scripts\python.exe -m pip install -r .\agentes\analista\requirements.txt
```

  

Para repetir exactamente las versiones fijadas en el lockfile:

  

```powershell
& .\agentes\analista\.venv\Scripts\python.exe -m pip install -r .\agentes\analista\requirements.lock
```

  

Si la ubicación del archivo de dependencias cambia, consultar `specs/002-chat-agente-analista/quickstart.md` y utilizar el archivo declarado allí. No modificar la instalación global de Python para este proyecto.

  
  

**OpenCode Server 2.1.2** (preparación una sola vez, desde la raíz):

  

```powershell
$opencodeProbe = Join-Path $env:TEMP 'opencode-2.1.2-isolated'
npm install --prefix $opencodeProbe --no-audit --no-fund @opencode/cli@2.1.2
& (Join-Path $opencodeProbe 'node_modules/@opencode/cli/bin/opencode.exe') --version
```

  

La versión mostrada debe ser `2.1.2`. Esta instalación es **independiente de la instalación global**; el comando habitual `opencode --version` puede mostrar otra versión. Si el directorio temporal se elimina, repite este paso antes de iniciar el servidor.

  

### Configuración `.env` (verificar antes de cada arranque)

  

Si el archivo no existe, copiar la plantilla y editarlo:

  

```powershell
if (-not (Test-Path .\.env)) { Copy-Item .\agentes\analista\.env.example .\.env }
notepad .\.env
```

  

Verificar que se hayan definido correctamente, como mínimo:

  

```dotenv
OPENCODE_SERVER_URL=http://127.0.0.1:4096
OPENCODE_SERVER_USERNAME=opencode
OPENCODE_SERVER_PASSWORD=<CONTRASEÑA_LOCAL_DEL_SERVIDOR>
OPENCODE_PROVIDER_ID=opencode
OPENCODE_MODEL_ID=nemotron-3.5-lightning-free
ANALISTA_HOST=127.0.0.1
ANALISTA_PORT=8000
ANALISTA_REQUEST_TIMEOUT_SECONDS=90
ANALISTA_MAX_TOOL_CALLS=4
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=<LANGFUSE_PUBLIC_KEY>
LANGFUSE_SECRET_KEY=<LANGFUSE_SECRET_KEY>
```

  

- Reemplazar `<CONTRASEÑA_LOCAL_DEL_SERVIDOR>` por una contraseña Basic Auth local que usarán tanto el script `scripts\entorno\iniciar-servidor-opencode.ps1` como FastAPI. El script la lee directamente de `.env` y no te la solicita en cada inicio. **Nunca** compartirla, subirla a Git ni copiarla en el frontend.

- `OPENCODE_PROVIDER_ID` vacío usa `opencode`. Con `OPENCODE_MODEL_ID` vacío se usa el default de ese provider solo si tiene costo cero verificable. Configurar provider y modelo juntos autoriza ese par aunque el precio sea positivo o no esté publicado; OpenCode debe anunciarlo y tenerlo habilitado. Ejemplo: `OPENCODE_PROVIDER_ID=opencode-go` y `OPENCODE_MODEL_ID=glm-5.3-flash`. `/api/analista/health` expone la configuración, la selección y el motivo concreto de rechazo. La lista no garantiza cuota disponible.

- Langfuse es opcional para levantar el chat; sin claves/servicio, el health puede indicar `degraded`.

- Reiniciar **FastAPI** después de modificar `.env`; si cambia `OPENCODE_SERVER_PASSWORD`, reiniciar también OpenCode con `.\scripts\entorno\iniciar-servidor-opencode.ps1`.

  

## 2. Inicio habitual — abrir tres terminales PowerShell

  

Iniciar **en este orden**, desde la raíz del proyecto.

  

### Terminal 1 — OpenCode Server 2.1.2 (puerto 4096)

Ejecuta **un único comando** desde la raíz del repositorio. El script `scripts\entorno\iniciar-servidor-opencode.ps1` lee el `.env` de la raíz del repositorio. El script lee `OPENCODE_SERVER_PASSWORD` del `.env` local, utiliza la instalación temporal de OpenCode 2.1.2 y no solicita que escribas la contraseña manualmente.

```powershell
.\scripts\entorno\iniciar-servidor-opencode.ps1
```

- Antes de iniciarlo, comprueba que la versión temporal haya sido instalada según la preparación inicial y que el puerto `4096` no esté ocupado. El script también valida estas condiciones.
- Debe aparecer algo similar a `server listening on http://127.0.0.1:4096`. **Mantén abierta esta terminal**; usa `Ctrl+C` para detener OpenCode.
- El usuario Basic Auth es `opencode`. El valor de `OPENCODE_SERVER_PASSWORD` del `.env` se utiliza para arrancar el servidor y también para que FastAPI se autentique. **No compartas ni publiques ese valor**.
- Si modificas la contraseña en `.env`, detén y vuelve a iniciar OpenCode con el script, y reinicia FastAPI. No inicies dos servidores en el mismo puerto.
- **No utilices `opencode serve` directamente** para este proyecto: podría ejecutar tu instalación global en lugar de la versión temporal 2.1.2.

### Terminal 2 — Backend FastAPI / Agente Analista (puerto 8000)

  

```powershell
& .\agentes\analista\.venv\Scripts\python.exe -m uvicorn agentes.analista.api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

  

- Esperar `Application startup complete` / `Uvicorn running on http://127.0.0.1:8000`.

-  **Mantener `--workers 1`**, porque las conversaciones se almacenan en memoria.

-  **No añadir `--reload`** durante las pruebas de conversaciones: al reiniciar se pierde ese estado.

- Conservar abierta esta terminal.

  

### Terminal 3 — Frontend React / Vite

  

Durante el desarrollo:
  

```powershell
npm run dev
```

  

Abre `http://localhost:3000`. Para compilar y previsualizar la versión de producción, detén el modo dev y ejecuta:

  

```powershell
npm run build
npm run preview
```

  

Abre la dirección **Local** mostrada por Vite; `preview` usa normalmente `http://localhost:4173/`. Usa solo uno de los modos a la vez. Tras modificar archivos, reconstruye con `npm run build` antes de abrir de nuevo `preview`.

  

## 3. Verificación rápida

  

Utilizar **otra terminal PowerShell** para las comprobaciones, sin detener las tres anteriores.

  

### Estado de FastAPI

  

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/analista/health' | ConvertTo-Json -Depth 8
```

  

La ruta correcta es **`/api/analista/health`**. `http://127.0.0.1:8000/health` puede responder `404` y eso, por sí solo, **no es una falla del agente**. `ready`, `degraded` y `unavailable` describen las dependencias del backend; HTTP 200 confirma que FastAPI respondió, pero no demuestra que el modelo pueda generar.

  

La interfaz presenta por separado **Backend conectado**, **OpenCode Server conectado** y **Generación del modelo sin verificar**. Solo una respuesta real confirma la capacidad de generar. Si health no responde, el backend está desconectado; `checks.opencode.status: unavailable` indica OpenCode desconectado. Los errores de envío identifican el modelo no disponible, la cuota agotada (`429`) o el timeout de 90 segundos.

  

### Comprobar los puertos

  

```powershell
Get-NetTCPConnection -LocalPort 4096,8000,4173 -State Listen -ErrorAction SilentlyContinue |
Select-Object LocalAddress,LocalPort,OwningProcess
```

  

Si se usa `npm run dev`, comprobar también el puerto indicado por Vite (habitualmente `3000` en este proyecto).

  

### Probar desde el navegador

  

1. Abrir la URL local que imprime Vite.

2. Abrir el panel **Agente Analista** y comprobar por separado backend y OpenCode.

3. Si indica **Backend desconectado**, revisar FastAPI y seleccionar **Reintentar conexión**.

4. Si indica **OpenCode Server desconectado**, revisar su terminal y el puerto 4096.

5.  **Generación del modelo sin verificar** es el estado inicial: health no ejecuta generación ni demuestra cuota. Una respuesta válida la confirma; los errores muestran modelo no disponible, cuota agotada o timeout.

  

## 4. Errores conocidos y solución

  

| Síntoma | Qué revisar |
|---|---|
| `ECONNREFUSED 127.0.0.1:8000` en Vite / **Backend desconectado** | FastAPI no se inició o se cerró; ejecutar el comando de la **Terminal 2**. |
| `404 /health` | Usar `/api/analista/health`, no `/health`. |
| `500 /api/analista/health` tras cambiar a 2.1.2 | Verificar que las validaciones del backend acepten 2.1.2 además de 2.0.27; no confundir el error con falta de cuota del modelo. |
| `401` al consultar OpenCode | `OPENCODE_SERVER_USERNAME` / `OPENCODE_SERVER_PASSWORD` no coinciden con el servidor activo; corregir `.env` local y reiniciar FastAPI. |
| **OpenCode Server desconectado** / `OPENCODE_UNAVAILABLE` | OpenCode Server no está disponible; revisa el listener 4096 y su terminal. No inicies una segunda instancia. |
| **Modelo no disponible** / `MODEL_UNAVAILABLE` | Revisa `OPENCODE_PROVIDER_ID` y `OPENCODE_MODEL_ID`, y consulta `checks.opencode.rejection_reason` en `/api/analista/health`; el modelo debe aparecer habilitado en OpenCode. |
| **Cuota agotada (429)** / `OPENCODE_RATE_LIMITED` | OpenCode rechazó la generación por cuota. Si OpenCode `2.1.2` devuelve `retryAfterMs`, el chat muestra la cuenta regresiva real; si no, informa que el tiempo es desconocido. El mensaje se conserva para reintentar manualmente. |
| **Timeout de 90 segundos** / `TURN_TIMEOUT` | La generación superó el deadline; revisa el proveedor. El mensaje se conserva para reintentar. |
| El panel muestra generación sin verificar | Health no ejecuta el modelo. Solo una respuesta real confirma capacidad de generación. |
| Cambios del frontend no se ven en `preview` | Detener preview, ejecutar `npm run build` y reiniciar `npm run preview`. |

  

### Habilitar el contador de recuperación

  

El contador automático puede recibir el tiempo de recuperación cuando **OpenCode 2.1.2** incluya `retryAfterMs` en el error. Para utilizar esa versión, sigue la instalación temporal de la sección 1 y arranca el servidor mediante `.\scripts\entorno\iniciar-servidor-opencode.ps1`, como se indica en la **Terminal 1** de la sección 2. No es necesario reemplazar la instalación global. Reinicia FastAPI tras cambiar la versión activa del servidor; conserva Basic Auth local y el provider/model configurado. La interfaz no realiza reintentos automáticos.

  

El tiempo aparece solo cuando el servicio incluye `retryAfterMs`; una cuota o un modelo cuyo error no contenga esa pista seguirá mostrando “tiempo desconocido”. No se asume un periodo de 24 horas.

  

### Inspección de modelos (solo si es necesario)

  

```powershell
opencode auth list
opencode models
```

  

Estos comandos sirven para inspeccionar autenticación y modelos listados, pero no demuestran que exista cuota funcional. No utilizar modelos de pago sin autorización expresa.

  

## 5. Detener los servicios

  

En cada una de las terminales de OpenCode, FastAPI y Vite, presionar **Ctrl+C**.

  

- Al detener FastAPI se pierden las conversaciones guardadas en memoria.

- Mantener los servicios enlazados a `127.0.0.1`; no publicar puertos a la red durante estas pruebas.

- No borrar el `.env` ni compartir capturas con contraseñas o tokens.

  

## 6. Resumen de comandos de todos los días

  

```powershell
# TERMINAL 1: OpenCode Server 2.1.2 (lee la contraseña del .env)
.\scripts\entorno\iniciar-servidor-opencode.ps1

# TERMINAL 2: Backend Python / FastAPI
& .\agentes\analista\.venv\Scripts\python.exe -m uvicorn agentes.analista.api.main:app --host 127.0.0.1 --port 8000 --workers 1

# TERMINAL 3: Frontend (si ya existe build actualizado)
npm run preview
# Desarrollo local (en lugar de preview):
# npm run dev
# Ejecutar después de modificar el frontend antes de preview:
# npm run build

# CUARTA TERMINAL OPCIONAL: salud del backend
# Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/analista/health' | ConvertTo-Json -Depth 8
```

  

**Referencia del propio proyecto:**  `specs/002-chat-agente-analista/quickstart.md`, que contiene las instrucciones y las comprobaciones más extensas. Si cambian los puertos, dependencias, contratos o scripts, actualizar esta guía de manera coordinada con el quickstart.


## Repositorio de HU y lecciones (memoria de largo plazo)

El backend guarda los datos en una base MySQL compatible (TiDB Cloud Starter en Render) indicada con `DATABASE_URL`; sin esa variable crea al iniciar un SQLite local en `agentes/analista/data/repositorio.db` (ignorado por Git; se puede cambiar con `ANALISTA_REPO_DB`). Guarda las historias de trabajo del equipo y, aparte, solo lo que una persona aprobó: HU aprobadas por el Product Owner (anonimizadas) y lecciones aprendidas aprobadas tras cambios posteriores al grooming. El agente solo lee lo aprobado, mediante `buscar_hu_similares` y `aplicar_checklist_vacios`. Para empezar de cero en local, detenga el backend y borre ese archivo. La configuración de la base en Render está en `DESPLIEGUE.md`.
