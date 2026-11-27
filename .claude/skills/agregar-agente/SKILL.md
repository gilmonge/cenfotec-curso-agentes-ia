---
name: agregar-agente
description: Úsala cuando haya que agregar un agente nuevo al equipo, o darle herramientas MCP o un paso en el flujo a un agente existente, en este repositorio de historias de usuario.
---

# Agregar un agente

Un agente es una carpeta en `agentes/equipo/<id>/`. El registro la descubre solo. Sigue estos pasos en orden y no edites los archivos genéricos (`agentes/equipo/__init__.py`, `agent_registry.py`, `ejecutor_mcp.py`, `health.py`).

## 1. Carpeta y definición
Crea `agentes/equipo/<id>/` (id en snake_case) con:
- `__init__.py` con una línea de docstring.
- `definicion.py` con `DEFINICION = DefinicionAgente(...)`. Copia la forma de `agentes/equipo/redactor_revisor/definicion.py`:
  - `id` igual al nombre de la carpeta; `constante` en MAYÚSCULAS (será `AgentId.<CONSTANTE>`); `nombre` visible; `orden` único (en decenas, según el lugar en el flujo).
  - `herramienta`: solo herramientas que existan en `_TOOL_NAMESPACE` (`agent_registry.py`), y en `fuente` el namespace de cada una con los tipos de fuente permitidos.
  - `propiedad`: las cuatro propiedades de agente (autonomía, razonamiento, herramientas, memoria).
  - `puede_consultar_asesor=True` solo si debe pedir criterio al Asesor Técnico.
- `prompt.md` con `**Versión editorial:** 1.0.0` y las secciones Misión, Entrada, Salida estructurada y Límites (mira los prompts existentes).
- `servidor_mcp.py`: copia exacta del de `agentes/equipo/analista/servidor_mcp.py`. No se edita.

## 2. Implementación
`<id>_service.py` con una clase `<Nombre>Service(AgenteOpenCodeService[<ModeloSalida>])`:
- `agente = AgentId.<CONSTANTE>`, `titulo_sesion = "..."`, y un error de salida que herede de `SalidaAgenteInvalidaError`.
- En `__init__`, pasa `client_factory or OpenCodeClient` a `super().__init__` (así las pruebas pueden reemplazarlo).
- Un método público (por ejemplo `evaluar`) que arma la tarea y el contexto y llama a `self._ejecutar_turno(tarea=..., contexto=..., consulta_base=..., armar_mensaje=..., interpretar=...)`.
- `interpretar` valida la salida con su modelo Pydantic y lanza el error de salida si no cumple: la base pide una corrección automáticamente.
- Ejemplo completo: `agentes/equipo/redactor_revisor/redactor_revisor_service.py`.

El modelo de salida va en `agentes/analista/core/workflow_models.py`, con `extra="forbid"` y límites de longitud.

## 3. OpenCode
Agrega en `opencode.jsonc` la entrada `"<id>"` con `"mode"` igual a `modo_opencode`, `"system": "{file:./agentes/equipo/<id>/prompt.md}"` y el permiso deny-all.

## 4. Flujo
El flujo es una tabla de pasos al final de `build_workflow_graph` en `agentes/analista/core/workflow_graph.py` (`lista_paso`). No uses `add_node`/`add_edge` directamente.
- Escribe una función `call_<id>` (con parámetro inyectable para pruebas, como `draft`/`review`) y un nodo que valide la salida con su modelo y devuelva los cambios de estado.
- Agrega su `Paso("<id>", <id>_node, "<siguiente>", "descripción")` y cambia el `siguiente` del paso anterior para que llegue al nuevo. Si el siguiente depende del estado, usa `Ruta(decidir, {clave: paso})`.
- `construir_flujo` valida la tabla: si un destino no existe o un paso queda sin llegada, falla con un mensaje claro.
- Agrega a `WorkflowState`/`WorkflowSnapshot` los campos nuevos y a `_public_snapshot` los que puede ver la interfaz.

Si el agente necesita una decisión humana: el nodo usa `interrupt({...,"kind": "<tipo>"})`, se agrega el tipo a `WorkflowInterrupt.kind` y a la tabla de modelos de respuesta en `agentes/analista/api/routes/workflows.py`, y en el frontend una entrada en `src/flujo/interrupciones.jsx`.

## 5. Ayuda y pruebas
- Agrega el agente a `AGENTES` en `src/data/ayudaDocumentacion.js` con `nombre: '<nombre visible>'` igual al de la definición.
- Pruebas del servicio con un OpenCode simulado (mira `agentes/analista/tests/unit/test_redactor_revisor.py`) y del nodo del grafo.
- Ejecuta `.venv/bin/python -m pytest -q agentes`: `test_estructura_proyecto.py` dirá qué falta.
