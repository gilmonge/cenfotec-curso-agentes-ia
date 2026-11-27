# Asistente multiagente para historias de usuario

Aplicación web que asiste en la creación y el mantenimiento de historias de usuario (HU) mediante un sistema de **cuatro agentes de inteligencia artificial**. Los agentes detectan vacíos en el requerimiento, identifican el impacto del cambio en otras partes del sistema, redactan la historia con sus criterios de aceptación y analizan las solicitudes de cambio posteriores al grooming. Las decisiones finales siempre las toma una persona: la HU solo se aprueba con la confirmación explícita del Product Owner.

Proyecto desarrollado para el curso de Inteligencia Artificial de Cenfotec. El diseño de la interfaz y de los flujos se elaboró con Antigravity.

## Contenido

- [Funcionalidades](#funcionalidades)
- [Flujo de creación de una historia](#flujo-de-creación-de-una-historia)
- [Arquitectura multiagente](#arquitectura-multiagente)
- [Diseño e identidad visual](#diseño-e-identidad-visual)
- [Tecnologías](#tecnologías)
- [Ejecución local](#ejecución-local)
- [Pruebas](#pruebas)
- [Despliegue](#despliegue)
- [Seguridad y datos](#seguridad-y-datos)
- [Documentación adicional](#documentación-adicional)
- [Equipo](#equipo)

## Funcionalidades

- **Asistente de cinco pasos** para crear una HU, desde el requerimiento de Negocio hasta la aprobación del Product Owner; el Analista y el Asesor Técnico arman juntos una sola ronda de preguntas.
- **Análisis de impacto:** antes de redactar la historia, el Asesor Técnico revisa el código del sistema y explica, en lenguaje de negocio, qué otras funciones afecta el cambio y qué reglas falta decidir.
- **Avance persistente:** cada flujo se guarda al esperar una respuesta. Una HU se puede dejar a medias y retomarse otro día desde la sección *En proceso*; un paso que falla se puede reintentar sin perder lo anterior.
- **Gestión de cambios:** las solicitudes de cambio sobre una HU aprobada se clasifican como aclaración o cambio de alcance, con propuesta de lecciones aprendidas.
- **Acciones sobre una HU:** consulta, edición, solicitud de cambio, descarga en Word o PDF con plantilla configurable y eliminación.
- **Roles, acciones y Mantenimiento:** inicio de sesión por usuario; cada rol tiene sus acciones (por ejemplo, solo el Product Owner aprueba) y se administran en la pestaña Mantenimiento.
- **Pendientes y avisos:** el Product Owner ve lo que espera su aprobación; quien creó la historia ve si fue aprobada, devuelta con su motivo o rechazada. El aviso por Teams está preparado pero apagado hasta configurarlo (ver DESPLIEGUE.md).
- **Ayuda integrada** con el flujo, los agentes, las tecnologías y los temas pendientes de definición.

## Flujo de creación de una historia

| Paso | Responsable | Descripción |
|---|---|---|
| 1. Requerimiento | Analista humano | Registro de la minuta, el correo o el incidente recibido de Negocio |
| 2. Análisis | Agente Analista y Asesor Técnico (en equipo) | El Analista clasifica la información en conocida, faltante, supuesta y ambigua; lo que solo se sabe revisando el sistema lo pasa al Asesor, que revisa el código enseguida |
| 3. Preguntas a Negocio | Negocio | Una sola ronda con las preguntas del Analista y las decisiones del Asesor, junto con el impacto en otros módulos explicado sin detalle técnico; se repite solo si quedan vacíos |
| 4. Historia | Agente Redactor-Revisor | Redacción *Como / Quiero / Para* con criterios *Dado que / Cuando / Entonces* (cada impacto queda como criterio) y revisión en hasta dos rondas |
| 5. Aprobación | Product Owner | Aprobación, devolución a un agente con motivo o rechazo |

Al aprobarse, la HU se almacena en el Repositorio de HU y se incorpora a la base de conocimiento que consultan los agentes.

## Arquitectura multiagente

La aplicación se ejecuta como un solo servicio: una interfaz en React servida por un backend en FastAPI, que orquesta a los agentes con LangGraph. Cada agente utiliza el modelo de lenguaje a través de OpenCode Server y accede a sus fuentes mediante un servidor MCP propio, respaldado por una base de conocimiento en Pinecone (RAG).

### Estructura del proyecto

El proyecto está organizado por capas y con registros declarativos, para que los cambios frecuentes se hagan en un solo lugar. El detalle está en [docs/arquitectura.md](docs/arquitectura.md).

- **Equipo de agentes (`agentes/equipo/<agente>/`):** cada agente es una carpeta con su definición (`definicion.py`), sus instrucciones (`prompt.md`), su servidor MCP y su implementación (`<agente>_service.py`). El registro las descubre automáticamente y de ahí salen sus permisos, herramientas y servidor.
- **Clase base (`agentes/equipo/agente_opencode_service.py`):** el ciclo común con OpenCode y MCP, incluida la corrección de salidas inválidas, se escribe una sola vez (patrón *Template Method*).
- **Registro de pantallas (`src/config/rutas.jsx`):** de una sola lista salen las rutas y el menú.
- **Registro de intervenciones humanas (`src/flujo/interrupciones.jsx`):** asocia cada pausa del flujo con su formulario.
- **Pruebas de estructura:** `agentes/analista/tests/unit/test_estructura_proyecto.py` verifica que cada agente tenga todas sus piezas y que la configuración coincida con el registro.
- **Guías para herramientas de IA:** las skills `estructura-proyecto`, `agregar-agente` y `agregar-ruta` (en `.agents/skills` y `.claude/skills`) explican cómo hacer cambios sin romper la estructura.

### Ciclo de trabajo de cada agente

Todos los agentes siguen el ciclo **percibir → pensar → actuar** (`agentes/analista/core/ciclo_agente.py`):

1. **Planificación:** el modelo recibe la tarea y las herramientas de su rol, y decide qué consultar y con qué términos.
2. **Ejecución por MCP:** el backend valida el plan contra los permisos del rol y lo ejecuta en el servidor MCP del agente.
3. **Respuesta:** el agente responde con la evidencia recuperada. Si el plan no es válido, el backend consulta todas las fuentes del rol y deja constancia.

### Agentes

| Agente | Autonomía | Razonamiento | Herramientas (servidor MCP propio) | Memoria |
|---|---|---|---|---|
| Analista de Requerimientos | Elige fuentes y consultas; se detiene al entregar preguntas | Clasifica la información en conocida, faltante, supuesta y ambigua | Glosario, HU similares, estándares y checklist de vacíos | Historial de la sesión y Repositorio de HU |
| Asesor Técnico | Decide qué datos buscar y qué archivos abrir, en hasta tres rondas | Identifica todos los lugares que afecta un cambio y separa el impacto de negocio de la evidencia técnica | Referencias en el código, búsqueda semántica, lectura de archivos, estándares y HU similares | Análisis validado y Repositorio de HU |
| Redactor-Revisor | Redacta, revisa y corrige, en hasta dos rondas | Evalúa la HU contra estándares y checklist, y cubre cada impacto con criterios | Estándares, checklist y HU similares | Análisis aclarado, impacto y ronda previa |
| Gestor de Cambios | Elige fuentes y puede consultar al Asesor Técnico | Compara con la HU aprobada, clasifica el cambio y determina la causa raíz | HU aprobadas, lecciones aprendidas y checklist | HU aprobadas e historial de causas raíz |

### Principios de diseño

- **Mínimo privilegio:** cada agente dispone de un servidor MCP (en su carpeta, con las herramientas de `agentes/analista/mcp/`) que expone únicamente las herramientas de su definición; al conectarse se verifica que el conjunto coincida exactamente. La recuperación también se filtra por rol.
- **Revisión de código en solo lectura:** el Asesor Técnico analiza un repositorio independiente, indicado en `ASESOR_REPOSITORIO_URL` (por defecto, [codigo-ejemplo-polizas](https://github.com/Yuvania/codigo-ejemplo-polizas)). Al arrancar se descarga una copia superficial, se conservan solo archivos `.py` y `.md`, se elimina el historial y no se ejecuta nada. Si no está disponible, se usa la copia incluida en `ejemplos/polizas_demo`.
- **Lenguaje de negocio para las personas usuarias:** la interfaz no muestra archivos, líneas ni código; la evidencia técnica se conserva para Desarrollo.
- **Control humano:** ningún agente aprueba historias. Negocio responde, la persona que redacta la HU toma las decisiones de impacto y el Product Owner aprueba.
- **Trazabilidad:** la sección *Cómo trabajó el agente* muestra qué decidió consultar cada agente y por qué; Langfuse registra cada paso.

### Persistencia de los flujos

Cada vez que un flujo espera a una persona, o falla, su último punto de control se guarda en la tabla `workflow_guardado`. Si el servicio se reinicia, el flujo se recupera al consultarlo y la conversación del Analista se restaura con el último análisis guardado.

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/api/workflows` | Iniciar un flujo antes o después del grooming |
| `GET` | `/api/workflows` | Listar las HU en proceso |
| `GET` | `/api/workflows/{workflow_id}` | Consultar el estado de un flujo |
| `POST` | `/api/workflows/{workflow_id}/resume` | Responder la decisión que el flujo espera |
| `PUT` | `/api/workflows/{workflow_id}/borrador` | Guardar respuestas sin enviarlas |
| `POST` | `/api/workflows/{workflow_id}/reintentar` | Reintentar el paso que falló |
| `DELETE` | `/api/workflows/{workflow_id}` | Descartar un flujo |

## Diseño e identidad visual

La interfaz usa la marca **«Ciruela corporativa»**: sobria, de empresa y con identidad propia. La guía completa, con el porqué de cada regla, está en [docs/marca.md](docs/marca.md). Ninguna tarea cambia la marca: una pantalla nueva usa lo que ya existe.

**Colores** (solo como variables en `src/styles/_theme.scss`, con su par para modo oscuro):

| Color | Claro | Para qué se usa |
|---|---|---|
| Ciruela `--color-nav-bg` | `#1E1530` | Navegación: barra lateral, barra superior en móvil y botón de ayuda. |
| Morado `--color-primary` | `#6F3FA0` | La acción principal (una por pantalla), lo activo y el foco. |
| Naranja `--color-brand` | `#F36C21` | Solo el logotipo y lo que espera una decisión. Nunca texto ni botones. |
| Fondo `--color-bg` | `#F6F7F9` | Fondo de página. |
| Superficie `--color-surface` | `#FFFFFF` | Tarjetas, tablas y formularios, con borde de 1 px `#E5E7EB`. |
| Texto | `#111827` / `#4B5563` / `#6B7280` | Principal, secundario y tenue. |
| Estados | verde `#1F6B33`, ámbar `#9A4A0B`, rojo `#B42318` | Aprobada, espera a Negocio, rechazada: siempre con texto, no solo color. |

**Tipografía:** Inter (400, 500 y 600) para toda la interfaz e IBM Plex Mono para códigos como `HU-POL-014`. Título de página de 26 px en peso 600, texto de 14 a 16 px, etiquetas de 13 px. Sin serifas ni negritas de 700. Mayúscula solo al inicio de la oración.

**Fondos y formas:** página gris muy claro, contenido en superficies blancas con bordes finos, sin sombras ni degradados. Radios de 6 px en controles, 8 px en tarjetas y 12 px en ventanas modales.

**Web, tablet y móvil** (en `src/styles/_layout.scss`, sin trabajo extra en cada pantalla):

- **Web:** barra lateral ciruela de 232 px con el menú, la persona y el cambio de tema.
- **Tablet:** la barra queda en íconos de 72 px, con nombre accesible y texto emergente.
- **Móvil:** barra superior con la marca y la sesión, y el menú en una barra inferior fija con etiquetas cortas. Una columna y botones de 44 px.

**Modo claro y oscuro:** la persona lo elige en la barra; todos los colores tienen su par oscuro con contraste AA.

Para herramientas de IA, la skill `marca-diseno` (en `.agents/skills` y `.claude/skills`) resume estas reglas, y las pruebas de estructura fallan si aparece un color fuera de `_theme.scss` o una fuente distinta.

## Tecnologías

| Capa | Tecnologías |
|---|---|
| Interfaz | React 18, Vite 5, React Router 6, Sass, lucide-react, react-markdown |
| Documentos | docx (Word), jsPDF y jspdf-autotable (PDF) |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic, SQLAlchemy y PyMySQL |
| Orquestación | LangGraph, con interrupciones para decisiones humanas y puntos de control persistentes |
| Modelo de lenguaje | OpenCode Server 2.1.2 (proveedor OpenCode Go, modelo `glm-5.3-flash`) y LangChain |
| Herramientas | FastMCP y el adaptador MCP de LangChain, con un servidor por agente |
| Conocimiento (RAG) | Pinecone con `multilingual-e5-large` en seis espacios de nombres, carga automática y copia local de respaldo |
| Datos | TiDB Cloud (compatible con MySQL); SQLite en local y en pruebas |
| Observabilidad | Langfuse y registros del servidor |
| Pruebas | Vitest, Testing Library, Playwright, pytest y pytest-asyncio |
| Integración y despliegue | GitHub Actions, Docker y Render |

## Ejecución local

**Requisitos:** Node.js 22, Python 3.12 y una clave de OpenCode con un modelo autorizado.

1. **Instalar las dependencias:**
   ```powershell
   npm ci
   py -3.12 -m venv agentes\analista\.venv
   .\agentes\analista\.venv\Scripts\python.exe -m pip install -r agentes\analista\requirements.txt
   ```
2. **Configurar el entorno** a partir de la plantilla (el archivo `.env` no se versiona):
   ```powershell
   Copy-Item agentes\analista\.env.example .env
   ```
3. **Iniciar OpenCode, el backend y la interfaz:**
   ```powershell
   npm run iniciar
   ```
   La aplicación queda disponible en `http://localhost:3000`. Para detener el entorno: `npm run detener`.
4. **Verificar el estado del servicio:** `http://127.0.0.1:8000/api/analista/health` debe responder `status: ready`.

Para trabajar solo con la interfaz, sin agentes (las historias se guardan en el navegador): `npm ci` y `npm run dev`.

## Pruebas

```powershell
npm test                 # pruebas de la interfaz (Vitest)
npm run test:e2e         # pruebas de navegador (Playwright)
npm run build            # compilación de producción
.\agentes\analista\.venv\Scripts\python.exe -m pytest agentes\analista -q   # pruebas del backend
```

GitHub Actions ejecuta todas las pruebas en cada cambio que llega a `main` y en cada pull request.

## Despliegue

La aplicación completa (interfaz, backend y OpenCode) se publica como un único servicio Docker en Render, con despliegue automático desde la rama `main` (`render.yaml`). Las historias, el Repositorio de HU, las lecciones y los flujos en proceso se almacenan en TiDB Cloud, por lo que se conservan entre despliegues.

- Verificación ligera: `<URL del servicio>/healthz` (sin autenticación).
- Diagnóstico completo: `<URL del servicio>/api/analista/health` (con credenciales; comprueba OpenCode y los cuatro servidores MCP).
- Variables de entorno y configuración: [DESPLIEGUE.md](DESPLIEGUE.md).

## Seguridad y datos

- Los secretos se configuran únicamente en el panel de Render o en el `.env` local; nunca se versionan ni se envían al navegador.
- Las fuentes de conocimiento y el código de ejemplo son ficticios o anonimizados. La interfaz solicita anonimizar los datos personales antes de ingresarlos.
- Los agentes tratan las minutas, el código y los resultados de las herramientas como contenido no confiable y no siguen instrucciones contenidas en ellos.

## Documentación adicional

- [Arquitectura y cómo hacer cambios](docs/arquitectura.md)
- [Marca e identidad visual](docs/marca.md)
- [Guía de ejecución local](docs/GUIA-LOCAL.md)
- [Guía de pruebas y arranque en PowerShell](docs/GUIA-PRUEBAS-ARRANQUE-POWERSHELL.md)
- [Evaluación del Asesor Técnico](docs/evaluacion-asesor-tecnico.md)
- [Base de conocimiento e ingesta en Pinecone](agentes/conocimiento/README.md)
- [Despliegue y variables de entorno](DESPLIEGUE.md)

## Equipo

Allam Fernandez · Gilberth Monge · Yuvania Castillo
