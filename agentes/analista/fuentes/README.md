# Fuentes del Agente Analista

Archivos JSON que consultan las herramientas MCP. Todo el contenido es ficticio o simulado.

| Archivo | Herramienta | Campos |
|---|---|---|
| `glosario.json` | `consultar_glosario` | `termino`, `definicion`, `fuente`, `terminos` |
| `estandares.json` | `consultar_estandares` | `id`, `titulo`, `regla`, `referencia`, `terminos` |
| `checklist_vacios.json` | `aplicar_checklist_vacios` | `id` (GUID), `categoria`, `descripcion`, `terminos` |
| `hu_similares.json` | `buscar_hu_similares` | `id`, `titulo`, `resumen`, `aclaraciones`, `terminos` |

- `terminos` son las palabras clave con las que se encuentra la entrada.
- Los estándares reemplazan a los antiguos skills: cada regla conserva su ID (`FORM-03`, `BOTO-07`, `MODU-07`, `SIM-SEG-01`...), que debe ser único.
- Las reglas simuladas empiezan con `[SIMULADO, confirmar con Negocio]` y las de contexto con `[CONTEXTO simulado, no es regla de negocio confirmada]`.
- Al editar un archivo hay que reiniciar FastAPI (el MCP lee los archivos al arrancar).
