# Quickstart local — Feature 003 experimental

**Estado:** los workflows LangGraph, su API FastAPI y la interfaz React se ejecutan experimentalmente en `feat/sistema-multiagente-rag`. T001/T002 siguen pendientes de ratificación formal. Esta guía no cambia `main` ni despliega a Render.

## Requisitos

- Windows 10/11 y PowerShell 5.1 o 7.
- Node.js 22 o superior.
- Python 3.12 en `agentes\analista\.venv`.
- OpenCode Server local en `127.0.0.1:4096` para la ejecución real de agentes. Pruebas automáticas usan dobles.

## Instalar y arrancar

Desde la raíz del repositorio:

```powershell
npm ci
py -3.12 -m venv .\agentes\analista\.venv
& .\agentes\analista\.venv\Scripts\python.exe -m pip install -r .\agentes\analista\requirements.lock
if (-not (Test-Path .\.env)) { Copy-Item .\agentes\analista\.env.example .\.env }
```

Completa las variables locales de `.env`; no guardes credenciales en el frontend ni en esta guía. Inicia OpenCode, FastAPI y React:

```powershell
npm run iniciar
```

Abre `http://localhost:3000`. FastAPI debe usar un worker. Para revisar el estado, consulta `http://127.0.0.1:8000/api/analista/health` con las credenciales de desarrollo existentes. Para detener:

```powershell
npm run detener
```

## Flujo UI

- Crear HU inicia `pre_grooming`; revisa el análisis del Analista y responde todas las preguntas pendientes.
- El workflow muestra la HU del Redactor-Revisor y la evaluación del Asesor. La evidencia técnica de la demo procede de archivos ficticios y estándares de ejemplo.
- La decisión PO requiere confirmación explícita; solo el backend persiste la HU aprobada.
- Solicitar cambio en una HU aprobada inicia `post_grooming` con la HU real del Repositorio. El Gestor puede recomendar `aclaracion` o `cambio_alcance`; aceptar, rechazar y devolver requiere confirmación.
- Las lecciones propuestas no se aprueban automáticamente. La persona puede decidir cada una expresamente.
- Si el endpoint no responde al crear una HU, queda disponible el flujo manual existente. Solicitud de cambio ofrece modo manual explícito con selección de clasificación.

Los IDs de workflow permanecen solo en memoria de React y no se escriben en `localStorage`. El backend usa checkpoints en memoria: un reinicio pierde el checkpoint. Un 404 al consultar o reanudar pide iniciar un workflow nuevo; no se simula la recuperación. La autenticación Basic compartida no comprueba la identidad individual del PO.

## API y pruebas

La API experimental expone:

- `POST /api/workflows`
- `GET /api/workflows/{workflow_id}`
- `POST /api/workflows/{workflow_id}/resume`

Consulta `contracts/workflow-api.md` para esquemas exactos de respuesta y `interrupt_id`. Los tests frontend simulan los tres endpoints; pytest usa dobles y no llama modelos, MCP, TiDB o Pinecone.

```powershell
npm test
npm run build
& .\agentes\analista\.venv\Scripts\python.exe -m pytest .\agentes\analista\tests -q
```

RAG/Pinecone no está integrado. No configures claves Pinecone ni `INGESTA_AL_ARRANCAR`; las rutas disponibles no realizan recuperación vectorial. Para comandos PowerShell completos, salud, troubleshooting y apagado consulta `../../docs/GUIA-PRUEBAS-ARRANQUE-POWERSHELL.md`.
