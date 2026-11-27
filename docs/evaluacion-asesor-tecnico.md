# Evaluación del Asesor Técnico: impacto en otros lugares

La meta principal del Asesor Técnico es encontrar **todos** los lugares del repositorio de código que afecta un cambio, incluso los que la historia de usuario no menciona. Estos escenarios sirven para comprobarlo con el repositorio ficticio [`Yuvania/codigo-ejemplo-polizas`](https://github.com/Yuvania/codigo-ejemplo-polizas) (módulo de clientes).

> Este documento vive en el proyecto principal y **no** en el repositorio de código: el Asesor no puede leer las respuestas esperadas.

## Cómo evaluar

1. Inicia un flujo «antes del grooming» con el requerimiento del escenario y responde las preguntas del Analista hasta llegar al Asesor.
2. Compara los módulos que reporta el Asesor (módulos afectados, dependencias y riesgos) con la columna «Impacto esperado».
3. Registra la **cobertura**: módulos esperados encontrados ÷ módulos esperados. Meta: 100 % en los tres escenarios.
4. Revisa también que cada hallazgo cite un archivo realmente consultado y que no invente módulos.

La prueba automática `test_evaluacion_asesor.py` verifica la parte determinista: que la herramienta MCP `buscar_referencias_codigo` encuentra todos los archivos esperados con los términos indicados. Si esa prueba pasa y el Asesor no reporta un módulo, el problema está en qué buscó el modelo, no en la herramienta.

## Escenario 1. Hacer opcional el teléfono del cliente

**Requerimiento:** «El teléfono del cliente deja de ser obligatorio en la pantalla Datos del cliente.»

**Términos que debería buscar:** `telefono` y su variante de columna `TEL`.

| Módulo | Impacto esperado |
|---|---|
| `clientes/pantalla_cliente.py` | El campo está marcado como obligatorio y la validación exige 8 dígitos. |
| `cargas/carga_cliente.py` | La columna `TEL` es obligatoria y se exige que tenga 8 dígitos: la carga seguiría rechazando filas sin teléfono. |
| `notificaciones/aviso_cliente.py` | Siempre arma el mensaje de texto con el teléfono: con el campo vacío se enviaría a un número inválido. |
| `reportes/exportacion_cliente.py` | Da formato con guion al teléfono: con el campo vacío la exportación mostraría un valor incorrecto. |
| `clientes/modelo_cliente.py` | El teléfono se define como texto requerido. |

## Escenario 2. Cambiar el formato de la fecha de nacimiento a aaaa-mm-dd

**Requerimiento:** «La fecha de nacimiento se debe ingresar y mostrar con el formato aaaa-mm-dd.»

**Términos que debería buscar:** `fecha_nacimiento`, `FORMATO_FECHA` y la columna `FNAC`.

| Módulo | Impacto esperado |
|---|---|
| `clientes/modelo_cliente.py` | Define `FORMATO_FECHA`, que usan la pantalla y la exportación. |
| `clientes/pantalla_cliente.py` | Lee y muestra con `FORMATO_FECHA`, pero la etiqueta tiene el formato escrito a mano «(dd/mm/aaaa)». |
| `reportes/exportacion_cliente.py` | La exportación cambiaría de formato: afecta a quien consume ese archivo. |
| `cargas/carga_cliente.py` | **Trampa:** no usa `FORMATO_FECHA`; tiene su propio formato `%d/%m/%Y`. Si solo se cambia la constante, la carga quedaría con otro formato. |

## Escenario 3. Agregar un correo secundario al cliente

**Requerimiento:** «El cliente puede registrar un correo principal y uno secundario; los avisos se envían a ambos.»

**Términos que debería buscar:** `correo` y su variante de columna `EMAIL`.

| Módulo | Impacto esperado |
|---|---|
| `clientes/modelo_cliente.py` | Hay un solo campo de correo. |
| `clientes/pantalla_cliente.py` | Un solo campo y una sola validación de formato. |
| `notificaciones/aviso_cliente.py` | Arma un único aviso por correo. |
| `reportes/exportacion_cliente.py` | El encabezado tiene una sola columna `CORREO`. |
| `cargas/carga_cliente.py` | La plantilla tiene una sola columna `EMAIL`. |
