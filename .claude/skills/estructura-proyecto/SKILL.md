---
name: estructura-proyecto
description: Úsala antes de cualquier cambio en este repositorio (asistente multiagente de historias de usuario). Explica las capas, los registros declarativos, las convenciones y las pruebas de estructura que no se deben romper.
---

# Estructura del proyecto

Lee `docs/arquitectura.md` antes de cambiar código y `docs/marca.md` (skill `marca-diseno`) antes de tocar la interfaz. Resumen de lo que no se negocia:

## Reglas
1. **No dupliques registros.** Pantallas → `src/config/rutas.jsx`. Pasos del asistente → `src/components/HistoriaUsuario/crear/pasosAsistente.js`. Intervenciones humanas → `src/flujo/interrupciones.jsx`. Agentes → `agentes/equipo/<id>/definicion.py`. Flujo → tabla `lista_paso` en `workflow_graph.py`. No escribas rutas, opciones de menú, listas de agentes ni permisos MCP a mano en otro lugar.
2. **Una carpeta por agente** en `agentes/equipo/`, con `definicion.py`, `prompt.md`, `servidor_mcp.py` y `<id>_service.py`. Para agregar uno usa la skill `agregar-agente`.
3. **Los agentes que usan OpenCode heredan de `AgenteOpenCodeService`** (`agentes/equipo/agente_opencode_service.py`). No copies el ciclo de OpenCode/MCP en otro servicio.
4. **Contratos tipados.** Entradas y salidas de agentes y del grafo son modelos Pydantic en `agentes/analista/core/workflow_models.py`. Una regla de negocio se valida en el modelo o en el nodo, no solo en el prompt.
5. **Ningún agente aprueba.** La aprobación es siempre una decisión humana (Product Owner).
6. **Mínimo privilegio.** Herramientas MCP de solo lectura y solo las que declara la definición del agente.
7. **La HU no muestra detalle técnico** a la persona usuaria (archivos, código, nombres internos).
8. **Toda funcionalidad se protege con una acción.** El catálogo está en `agentes/seguridad/catalogo.py` (código, nombre legible y módulo) y su copia de códigos en `src/config/acciones.js`. Cada ruta de la API declara `requiere_accion(ACCION.X)`, `requiere_sesion` o `ruta_publica` (`agentes/analista/api/sesion.py`); en el frontend, la entrada de `rutas.jsx` lleva `accion` y los botones usan `useSesion().puede(ACCION.X)` o `<Permitido accion>`. La acción nueva aparece sola en Mantenimiento para asignarla a los roles. El permiso se valida en el backend; ocultar el botón no basta.
9. **El diseño es la marca «Ciruela corporativa».** Una tarea funcional no cambia colores, fuentes ni la estructura de navegación: usa las variables de `src/styles/_theme.scss` y los componentes comunes (skill `marca-diseno`).

## Convenciones de código
- Nombres en español y en singular: `listaAgente`, `listaRuta` (no `agentes`, `rutas` para variables).
- Clases de servicio terminan en `Service` (clase y archivo).
- Nunca un `except`/`catch` vacío o solo con comentario: al menos registra un log.
- No registres el contenido generado por el modelo ni datos personales; solo el tipo de error.
- Prompts: cada cambio sube la `**Versión editorial:**`.
- Confirmaciones: nunca `window.confirm`, `alert` ni `prompt`; usa `useConfirmacion()` de `src/components/Comun/ConfirmacionComponent.jsx` (modal accesible de la aplicación).

## Antes de terminar un cambio
- `.venv/bin/python -m pytest -q agentes` (incluye `test_estructura_proyecto.py`, las barandas).
- `npx vitest run` y `npx vite build`.
- Si una prueba de estructura falla, completa lo que falta; no la relajes ni la borres.
- Si agregas o cambias un agente, una pantalla o una tecnología, actualiza la Ayuda (`src/data/ayudaDocumentacion.js`).
