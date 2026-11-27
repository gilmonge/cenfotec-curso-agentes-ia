# Despliegue en Render

La aplicación completa (interfaz, backend del Agente Analista y OpenCode Server) se publica como **un solo servicio con un solo URL**. Cada cambio que se une a `main` se despliega solo. Para trabajar los cambios sigues usando tu entorno local.

El Blueprint mantiene un único Web Service Docker. La imagen incluye React compilado, FastAPI y OpenCode; FastAPI mantiene un worker, usa el `DATABASE_URL` de TiDB y conserva la autenticación Basic existente. `/healthz` es el health check ligero de Render y queda exento de autenticación. Esta configuración no crea servicios ni modifica credenciales.

**Alcance verificado:** el servicio despliega los cuatro agentes (Analista, Asesor Técnico, Redactor-Revisor y Gestor de Cambios) orquestados con LangGraph, con pausas para las decisiones humanas guardadas en la base de datos, conocimiento en Pinecone (con copia local de respaldo) y un servidor MCP de solo lectura por agente. El health detallado `/api/analista/health` verifica OpenCode, el prompt y que cada servidor MCP exponga exactamente las herramientas de su agente.

## Flujo de trabajo

1. Trabajas en local: `npm run iniciar` (igual que hoy, con tu `.env`).
2. Subes una rama y abres un PR en GitHub.
3. Al unir el PR a `main`, Render construye la imagen y publica la nueva versión sin intervención.
4. El equipo entra por el URL de Render con el usuario y la clave compartidos.

## Primera vez

1. En Render: **New → Blueprint** y selecciona el repositorio `Yuvania/historias-de-usuario-cenfotec-proyecto`. Render lee `render.yaml`.
2. Completa los valores que se piden (no se guardan en el repositorio):

| Variable | Qué es |
|---|---|
| `OPENCODE_API_KEY` | Clave del plan OpenCode Go (la misma que usas en local, pero crea una **nueva** para el servidor). |
| `ACCESO_USUARIO` / `ACCESO_CLAVE` | Usuario y contraseña del **administrador inicial**. Con ellas se activa el inicio de sesión por usuario: en una base nueva se crean los roles iniciales y este administrador, que luego crea a los demás usuarios en Mantenimiento. Usa una clave larga. |
| `TEAMS_WEBHOOK_URL` (opcional) | URL del flujo de Teams que recibe el aviso «Historia lista para su aprobación». Sin ella no se envía nada a Teams (los Pendientes de la aplicación funcionan igual). Ver «Aviso por Teams al Product Owner». |
| `APP_URL` (opcional) | Dirección pública de la aplicación para el enlace del aviso. En Render se usa `RENDER_EXTERNAL_URL` si falta. |
| `SESION_SECRETO` (opcional) | Secreto para firmar las sesiones. Si falta se deriva de `ACCESO_CLAVE`; si se cambia, todos deben volver a ingresar. |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Opcionales. Déjalas vacías si no usas Langfuse en el servidor. |

3. Ya vienen definidas en `render.yaml`: `ANALISTA_PUBLICO=1` (obliga a tener usuario y clave; si faltan, el servicio no inicia), `OPENCODE_PROVIDER_ID`, `OPENCODE_MODEL_ID` y `OPENCODE_SERVER_PASSWORD` (la genera Render).
4. Espera el primer despliegue (varios minutos) y abre el URL `https://<nombre>.onrender.com`. El navegador pedirá el usuario y la clave.
5. Verifica el agente con `https://<nombre>.onrender.com/api/analista/health` (con las mismas credenciales) y crea una historia de prueba.

## Variables de entorno

Se cambian en el panel de Render (**Environment**); al guardar, Render reinicia el servicio.

| Variable | Obligatoria | Uso |
|---|---|---|
| `ANALISTA_PUBLICO` | Sí en Render | Con `1` exige usuario y clave de acceso. |
| `ACCESO_USUARIO`, `ACCESO_CLAVE` | Sí en Render | Administrador inicial y activación de la seguridad por usuario. |
| `OPENCODE_SERVER_PASSWORD` | Sí | Clave interna entre el backend y OpenCode (la genera Render). |
| `OPENCODE_API_KEY` | Sí | Credencial del modelo. |
| `OPENCODE_PROVIDER_ID`, `OPENCODE_MODEL_ID` | Sí | Modelo a usar (`opencode-go` / `glm-5.3-flash`). |
| `DATABASE_URL` | Sí en Render | Cadena de conexión de la base MySQL compatible (TiDB Cloud Starter). Sin ella se usa un SQLite local que **se pierde** en cada despliegue. |
| `DATABASE_SSL` | No | Con `0` desactiva TLS hacia la base (solo para una base local); por defecto está activo. |
| `ANALISTA_REPO_DB` | No | Ruta del SQLite local cuando no hay `DATABASE_URL` (desarrollo). |
| `LANGFUSE_*` | No | Observabilidad. |
| `VITE_ANIO`, `VITE_VERSION` | No | Año y versión del pie de página: «HISTORIAS DE USUARIO ® Derechos Reservados *año* - V.*versión*». Son de **compilación**: al cambiarlos Render vuelve a construir la imagen. Por defecto: año actual y `1.0.0`. |
| `VITE_PREFIJO_HU` | No | Prefijo del número de la HU. Es de **compilación**: si lo cambias, hay que volver a desplegar. |
| `PINECONE_API_KEY` | No | Clave de Pinecone para el RAG. Sin ella (o si Pinecone falla) las herramientas usan la copia local y lo indican con `status=degraded`. Los demás `PINECONE_*` vienen en `render.yaml`. |
| `ASESOR_REPOSITORIO_URL` | No | Repositorio de código que revisa el Asesor Técnico (https, público, **sin credenciales en la URL**). Vacío: usa `ejemplos/polizas_demo`. |
| `ASESOR_REPOSITORIO_RAMA` | No | Rama de ese repositorio (por defecto `main`). |
| `ANALISTA_MCP_TRANSPORTE` | No | `memoria` (recomendado en Render: mismo protocolo MCP, mismo proceso, sin arrancar un proceso por consulta) o `stdio` (cada servidor MCP en su propio proceso; predeterminado en local). |
| `ANALISTA_TURN_TIMEOUT_SECONDS` | No | Tiempo máximo por agente, en segundos (90 por defecto; 180 en `render.yaml`; máximo 300). |
| `PINECONE_SINCRONIZACION_AUTOMATICA` | No | `1` (por defecto): carga automática del conocimiento en Pinecone. `0`: solo carga manual. |
| `ANALISTA_UMBRAL_SIMILITUD_VACIO` | No | Similitud (0 a 1, `0.9` por defecto) a partir de la cual un vacío se considera el mismo tema que una pregunta ya respondida: no se le vuelve a preguntar a Negocio y pasa como supuesto a validar por el PO. |

## Aviso por Teams al Product Owner

Está preparado pero apagado: sin `TEAMS_WEBHOOK_URL` no se envía nada. Para activarlo más adelante:

Cuando una historia queda lista para aprobar, la aplicación envía una tarjeta a Teams con el título, quién la creó y el enlace para decidir.

1. En Teams, abra la app **Workflows** y cree un flujo con la plantilla «Post to a chat when a webhook request is received» (o a un canal).
2. Elija el chat con el Product Owner (o el canal del equipo) y guarde. Copie la URL que muestra el flujo.
3. En Render, agregue la variable `TEAMS_WEBHOOK_URL` con esa URL. No se versiona: contiene la firma del flujo.

Los flujos de Teams no muestran botones en la tarjeta, por eso el enlace también va como texto.

## Base de datos gratuita (TiDB Cloud Starter)

Las historias, el Repositorio de HU y las lecciones aprendidas se guardan en una base MySQL compatible, así que **no se pierden** al reiniciar o redesplegar en Render y se comparten entre dispositivos.

1. Crea una cuenta en TiDB Cloud y un **Starter cluster** gratuito (elige una región cercana a la del servicio en Render).
2. En el cluster pulsa **Connect**, elige el conector **PyMySQL** y genera la contraseña. Copia los datos de conexión (host, puerto, usuario, contraseña y base).
3. Arma la URL así: `mysql+pymysql://USUARIO:CLAVE@HOST:4000/BASE` (si la clave tiene caracteres especiales como `@`, `/` o `:`, codifícalos, por ejemplo `@` → `%40`).
4. En Render, **Environment → Add Environment Variable**: `DATABASE_URL` con esa URL. Guarda; Render reinicia el servicio.
5. Verifica con `/api/analista/health` y crea una historia. Al entrar desde otro navegador o dispositivo debe aparecer la misma.

Notas:

- Las tablas se crean solas al iniciar; no hay que ejecutar scripts.
- **Identificadores:** cada registro tiene un `id` GUID aleatorio (llave primaria y relaciones entre tablas) y, aparte, un `codigo` legible para las personas: `HU-CODIGO-001` en las historias y `LEC-001` en las lecciones. El GUID nunca se usa como código.
- **Esquema anterior:** si el servicio detecta tablas de una versión incompatible (por ejemplo, IDs numéricos), se detiene y lo indica en los logs. No borres tablas ni ejecutes migraciones destructivas. Detén el despliegue, conserva una copia de seguridad y prepara una migración no destructiva revisada antes de cambiar el esquema. Esta revisión no incluye una migración automática de esquemas antiguos.
- La conexión usa TLS y se recicla cada pocos minutos porque TiDB Cloud cierra las conexiones inactivas.
- El plan Starter tiene una cuota mensual gratuita; si se agota, la base deja de aceptar conexiones hasta el mes siguiente o hasta subir de plan.
- **Nunca** pegues la cadena de conexión en el chat, en el código ni en un commit: solo en el panel de Render. Si se expone, restablece la contraseña en TiDB Cloud.
- La base es la única fuente de verdad: lo que un navegador tenga guardado de versiones anteriores se reemplaza por lo que haya en la base.

## Plan gratuito (prueba) y paso a datos permanentes

Por defecto el Blueprint usa el plan `free`, sin tarjeta de crédito, para comprobar que todo arranca. Límites:

- **Sin disco persistente:** los archivos locales se borran en cada despliegue o reinicio; por eso los datos van a la base de datos externa (`DATABASE_URL`).
- **Se duerme sin uso:** tras unos 15 minutos sin visitas el servicio se detiene y la primera visita siguiente tarda aproximadamente un minuto en responder.
- **Memoria limitada (512 MB):** el servicio ejecuta el backend y OpenCode juntos. Si Render lo reinicia por falta de memoria (aparece en los logs), hay que pasar al plan `starter`.

Para usarlo en serio: en `render.yaml` cambie `plan: free` por `plan: starter`, descomente el bloque `disk` y una el cambio a `main`. Render pedirá tarjeta y desde entonces los archivos locales también se conservan entre despliegues.

## Importante

- **Seguridad:** quien entre al URL consume la cuota de tu plan de OpenCode. Por eso el acceso con clave es obligatorio y no se debe compartir el URL con la clave fuera del equipo. No uses datos personales reales en las historias.
- **Un solo servidor:** el servicio está pensado para una sola instancia (las conversaciones del agente y los flujos activos viven en memoria; los flujos se guardan en la base de datos cada vez que esperan a una persona, así que un reinicio no los pierde). No lo escales a varias instancias.
- **Credenciales del modelo:** el contenedor escribe `OPENCODE_API_KEY` en el archivo de credenciales de OpenCode al arrancar. Si el endpoint `/api/analista/health` indica que el modelo no está disponible, revisa que la clave sea válida y el plan esté activo.
- **Rotación:** cambia `OPENCODE_API_KEY` desde el panel cuando alguien deje el equipo, y desactiva su usuario en Mantenimiento.
- **Datos compartidos:** las historias y el Repositorio de HU viven en la base de datos. El navegador solo conserva una copia local (caché) que se actualiza al abrir la aplicación y al volver a ella; sin conexión se puede leer, pero los cambios se envían cuando el servicio responde.

## Ingesta, salud y memoria

- **Carga automática de Pinecone** (con `PINECONE_API_KEY`): al arrancar, en segundo plano, el backend descarga el repositorio del Asesor, crea el índice si falta y carga solo las fuentes que cambiaron o que están vacías (guarda una huella por fuente en la tabla `sincronizacion_conocimiento`). Al aprobar, editar o eliminar una HU, o al aprobar una lección, recarga la fuente `repositorio`. Mientras dura la carga inicial, las búsquedas usan la copia local (`status=degraded`, `KNOWLEDGE_SYNC_IN_PROGRESS`). En los logs aparece `Conocimiento (Pinecone): {...}` con el resultado por fuente.
- Si la carga falla, el servicio sigue con la copia local y se reintenta en el siguiente arranque. Se puede desactivar con `PINECONE_SINCRONIZACION_AUTOMATICA=0` y cargar a mano con `python -m agentes.conocimiento.ingesta --fuente todas --crear-indice`.
- `/healthz` responde con una comprobación local mínima para el health check de Render. `/api/analista/health` hace diagnósticos adicionales contra OpenCode y el registro MCP del Analista; puede tardar más y requiere autenticación.
- El entrypoint inicia OpenCode y Uvicorn con `--workers 1`, requisito para conservar las conversaciones en memoria. Mantén una sola instancia.
- Con `ANALISTA_MCP_TRANSPORTE=stdio`, cada consulta de un agente abre su servidor MCP como proceso aparte (unos 90 MB y, con 0,1 CPU, unos 10 s de arranque). Por eso en Render se usa `memoria`.
- El plan Free actual asigna 512 MB por instancia ([planes de cómputo de Render](https://render.com/docs/compute-plans)); OpenCode y FastAPI comparten esa memoria. Esta revisión local no puede consultar las métricas del servicio Render: monitoréalas en el panel de Render durante cualquier prueba. Si hay reinicios por memoria, detén la prueba y evalúa el plan existente antes de volver a intentarlo. No añadas workers ni servicios.

Para las pruebas de PowerShell y los límites de validación actuales, consulta [la guía de arranque y pruebas](docs/GUIA-PRUEBAS-ARRANQUE-POWERSHELL.md).
