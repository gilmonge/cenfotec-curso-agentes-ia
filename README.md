# Historias de Usuario — Agente Analista

Aplicación web para crear historias de usuario (HU) con ayuda de un **Agente Analista de Requerimientos**: analiza el requerimiento, detecta vacíos, genera preguntas para Negocio y, con las respuestas, deja la HU lista para aprobación del Product Owner. Las HU se descargan en Word o PDF con una plantilla de documento configurable.

> Prototipo desarrollado para el curso de IA de Cenfotec. **El diseño del prototipo (interfaz y flujos) se hizo con Antigravity.**

## Qué hace

- **Asistente de 5 pasos:** requerimiento → análisis del agente → preguntas a Negocio → borrador de la HU con criterios (Dado/Cuando/Entonces) → aprobación del Product Owner.
- **Agente Analista:** consulta glosario, HU similares, estándares y checklist de vacíos. No redacta ni aprueba HU. Aprende de las HU aprobadas y de las lecciones que aprueba el Product Owner.
- **Acciones sobre una HU:** ver detalle (solo consulta), editar, solicitar cambio (siempre lleva a un nuevo análisis), descargar (Word/PDF) y eliminar.
- **Ayuda integrada** con el detalle del flujo, el agente, las tecnologías y lo que falta por definir.

## Tecnologías

| Capa | Tecnologías |
|---|---|
| Interfaz | React 18, Vite 5, React Router 6, Sass, lucide-react, react-markdown |
| Documentos | docx (Word), jsPDF + jspdf-autotable (PDF) |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic, SQLAlchemy + PyMySQL |
| Agente de IA | LangChain, FastMCP/MCP (herramientas), OpenCode Server 2.1.2 (modelo `glm-5.3-flash`), Langfuse (trazas) |
| Datos | TiDB Cloud (compatible con MySQL) + copia local en el navegador |
| Pruebas | Vitest + Testing Library, pytest |
| Despliegue | Docker, Render |

## Qué está desplegado

La aplicación completa (interfaz + backend + OpenCode) corre como **un solo servicio Docker en Render**, con un solo URL. Cada cambio que llega a `main` se despliega solo (`render.yaml`). Las historias, el Repositorio de HU y las lecciones se guardan en TiDB Cloud, así que no se pierden al redesplegar.

- Estado del agente: `<URL de Render>/api/analista/health` (debe mostrar `status: ready`).
- Configuración y variables: ver [DESPLIEGUE.md](DESPLIEGUE.md). Los secretos viven solo en el panel de Render, nunca en el repositorio.

## Cómo ejecutarlo en local

**Requisitos:** Node.js 22, Python 3.12 y una cuenta/clave de OpenCode con un modelo autorizado.

1. **Dependencias**
   ```powershell
   npm ci
   py -3.12 -m venv agentes\analista\.venv
   .\agentes\analista\.venv\Scripts\python.exe -m pip install -r agentes\analista\requirements.txt
   ```
2. **Configuración:** copie la plantilla y complete sus valores (no se sube a Git).
   ```powershell
   Copy-Item agentes\analista\.env.example .env
   ```
3. **Iniciar todo** (OpenCode, backend y frontend, cada uno en su ventana):
   ```powershell
   npm run iniciar
   ```
   Abra `http://localhost:3000`. Para detener: `npm run detener`.
4. **Verificar el agente:** `http://127.0.0.1:8000/api/analista/health` debe mostrar `status: ready`.

Solo la interfaz, sin agente (las historias se guardan en el navegador): `npm ci` y `npm run dev`.

**Pruebas**
```powershell
npm test
.\agentes\analista\.venv\Scripts\python.exe -m pytest agentes\analista -q
```

Instrucciones detalladas (OpenCode 2.1.2, arranque manual por terminal, diagnóstico): [docs/GUIA-LOCAL.md](docs/GUIA-LOCAL.md).

## Equipo

Allam Fernandez · Gilberth Monge · Yuvania Castillo
