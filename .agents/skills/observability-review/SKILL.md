---
name: observability-review
description: Revisa código React + JavaScript del proyecto para verificar logs estructurados, métricas, trazas de operaciones, correlation IDs, health checks y capacidad de diagnóstico en el navegador. Usar al revisar componentes, páginas, utilidades o flujos simulados (análisis y generación con IA, guardado en localStorage).
---

# Observability Review

## Purpose
Asegurar que cuando algo falla o se comporta raro en la aplicación, **cualquier persona del equipo pueda entender qué pasó revisando la consola del navegador**, sin tener que depurar línea por línea.

En este proyecto no hay backend, así que la observabilidad vive en el frontend: un logger centralizado, un identificador por operación (correlation ID), mediciones de duración de los procesos simulados, verificación del estado de la aplicación al iniciar y errores con contexto suficiente para diagnosticarlos.

## When to Use
- Al revisar un PR o cambio que agrega o modifica páginas, componentes con lógica, utilidades de `utils/` o acceso a `localStorage`.
- Al revisar los flujos simulados: "Analizando requerimiento...", "Generando Historia de Usuario...", "Guardar Historia".
- Cuando alguien reporta un comportamiento que no se pudo reproducir o explicar.
- Cuando se pide revisar "logs", "consola", "trazabilidad", "diagnóstico" o "telemetría".

## When NOT to Use
- Manejo de errores, reintentos, timeouts o fallback → usar `error-handling-resilience-review`.
- Componentes puramente visuales sin lógica (ej. `Badge`, `Card`, `PageTitle`).
- Revisión de estilos SCSS, diseño o responsive.
- Cumplimiento funcional contra el documento de requerimientos.

## Inputs
- **Obligatorio:** archivos, carpeta o diff a revisar (normalmente dentro de `src/`).
- **Recomendado:** `src/utils/` (logger, storage, simulación de IA), `main.jsx`, `App.jsx`.
- **Opcional:** descripción del flujo o del problema reportado.

Si no existe una utilidad de logging en el proyecto, esa ausencia es el primer hallazgo; no inventar que existe.

## Analysis Process
1. **Buscar la infraestructura base:** existencia de `utils/logger.js` (o equivalente), generador de IDs de operación y punto de arranque en `main.jsx`.
2. **Inventariar los `console.*`:** buscar `console.log`, `console.error`, `console.warn` sueltos en componentes y páginas.
3. **Recorrer los flujos clave** y verificar que dejan rastro:
   - Crear historia: Requerimiento → Análisis → Preguntas → Historia → Revisión → Guardar.
   - Editar historia desde el Accordion.
   - Carga del listado y del contador del Dashboard desde `localStorage`.
4. **Verificar correlación:** que todos los logs de un mismo flujo compartan un ID de operación.
5. **Verificar métricas:** duración de análisis y generación simulados, cantidad de historias cargadas y guardadas.
6. **Verificar health check de arranque:** disponibilidad de `localStorage`, integridad de los datos mock y versión de la estructura de datos.
7. **Verificar diagnosticabilidad:** simular 2–3 fallos (JSON corrupto en `localStorage`, id inexistente en `/historias/:id`, error en un componente) y evaluar si la consola explica la causa.
8. **Verificar que no se registren datos sensibles** ni textos completos innecesarios.
9. **Clasificar los hallazgos** y redactar el reporte.

## Rules
- Citar siempre **archivo y línea** (o componente) de cada hallazgo.
- Toda recomendación incluye **código completo** listo para pegar.
- Todo log pasa por el logger centralizado; no se aceptan `console.*` sueltos en componentes o páginas.
- Los logs son estructurados: un mensaje fijo más un objeto de contexto (`logger.info('story.saved', { operationId, storyId })`), no strings concatenados.
- Nombres de evento en formato `dominio.accion` en inglés y en minúscula (`analysis.started`, `story.saved`), para que sean fáciles de filtrar.
- No registrar el texto completo de la descripción del requerimiento ni respuestas de Negocio; registrar longitudes, ids o conteos.
- No registrar datos personales, credenciales ni claves de API (si en el futuro se integra IA real).
- Los logs de nivel `debug` no deben mostrarse en el build de producción (`import.meta.env.DEV`).
- Calibrar a prueba de concepto: no exigir herramientas externas (Sentry, Application Insights, Datadog). Si se recomiendan, marcarlas como **Info** para una fase productiva.
- No duplicar hallazgos de manejo de errores: aquí solo se evalúa si el error **queda registrado con contexto**, no cómo se recupera.
- Reconocer lo que está bien hecho en "Fortalezas".
- Responder en español.

## Checklist

### Logs estructurados
- [ ] Existe `src/utils/logger.js` con niveles `debug`, `info`, `warn`, `error`.
- [ ] No hay `console.*` directos en componentes ni páginas.
- [ ] Cada log tiene nombre de evento y objeto de contexto.
- [ ] Niveles bien usados: `error` para fallos, `warn` para situaciones recuperables, `info` para hitos del flujo, `debug` para detalle.
- [ ] Los errores se registran con el objeto `Error` completo (mensaje y stack), no solo `error.message`.
- [ ] `debug` deshabilitado fuera de desarrollo.
- [ ] Sin textos completos del usuario ni datos sensibles en los logs.

### Correlation IDs
- [ ] Existe un generador de IDs (`crypto.randomUUID()` con fallback).
- [ ] Cada flujo de creación o edición inicia un `operationId` y lo propaga a todos sus logs.
- [ ] El `operationId` se conserva entre pasos del Stepper (estado del flujo, no una variable local de cada paso).
- [ ] Si en el futuro hay llamadas HTTP, el ID se envía en un header (`X-Correlation-Id`).

### Trazas de operaciones
- [ ] Las operaciones simuladas registran inicio y fin (`analysis.started` / `analysis.completed`).
- [ ] Se registra el paso actual del Stepper al avanzar o retroceder.
- [ ] Se registran las acciones clave del usuario: guardar, editar, abrir historia.

### Métricas
- [ ] Duración de análisis y generación medida con `performance.now()`.
- [ ] Conteos útiles: historias cargadas, preguntas pendientes vs respondidas, criterios generados.
- [ ] Las métricas se registran como logs estructurados con campo numérico (`durationMs`, `count`).

### Health checks
- [ ] Al iniciar la app se verifica que `localStorage` esté disponible.
- [ ] Se valida que los datos guardados tengan la estructura esperada (versión de esquema o campos mínimos).
- [ ] El resultado del chequeo queda registrado (`app.health` con estado `ok` o `degraded`).
- [ ] Existe una forma simple de ver el estado (log en consola o sección en la pantalla de Ayuda en modo desarrollo).

### Diagnosticabilidad
- [ ] Un `ErrorBoundary` registra errores de renderizado con el componente y la ruta.
- [ ] Rutas con id inexistente registran un `warn` con el id solicitado.
- [ ] Un error en `localStorage` indica qué clave falló y por qué.
- [ ] Con solo la consola se puede reconstruir qué hizo el usuario antes del fallo.

## Severity / Priority
| Severidad | Criterio | Ejemplo en este proyecto |
|---|---|---|
| **Alto** | Un fallo ocurre sin dejar ningún rastro, o se exponen datos sensibles. | `catch {}` vacío al leer `localStorage`; se loguea una API key. |
| **Medio** | Hay rastro, pero no alcanza para diagnosticar o no se puede correlacionar. | `console.log` sueltos sin contexto; flujo de creación sin `operationId`; error logueado solo con `error.message`. |
| **Bajo** | Mejora de consistencia o de calidad del registro. | Nombres de evento inconsistentes; niveles mal elegidos; `debug` visible en build. |
| **Info** | Sugerencia para fase productiva o fortaleza observada. | Integrar Application Insights o Sentry cuando exista backend. |

No se usa "Crítico" porque el proyecto es una prueba de concepto sin datos reales ni usuarios en producción.

## Output Format
````markdown
# Observability Review — <componente / flujo / PR>

## Resumen
- Alcance revisado: <archivos>
- Calificación general: <Adecuada | Mejorable | Insuficiente>
- Hallazgos: Alto X · Medio X · Bajo X · Info X

## Fortalezas
- ...

## Hallazgos
### [SEVERIDAD] OBS-001 — <título corto>
- **Ubicación:** `src/ruta/Archivo.jsx:línea`
- **Categoría:** Logs | Correlation | Trazas | Métricas | Health check | Diagnóstico
- **Problema:** <qué pasa>
- **Impacto:** <qué no se podría diagnosticar>
- **Recomendación:** <acción concreta>
- **Código sugerido:**
```jsx
  // código completo
```

## No verificable
- <archivos no proporcionados>

## Checklist resumen
| Área | Estado |
|---|---|
| Logs estructurados | ✅ / ⚠️ / ❌ / N/V |
| Correlation IDs | |
| Trazas de operaciones | |
| Métricas | |
| Health checks | |
| Diagnosticabilidad | |

## Próximos pasos priorizados
1. ...
````

## Examples

### Entrada
````jsx
// pages/NewStory.jsx
const handleAnalyze = () => {
  console.log('analizando', form.description);
  setLoading(true);
  setTimeout(() => {
    setAnalysis(mockAnalysis);
    setLoading(false);
    setStep(2);
  }, 1500);
};

// utils/storage.js
export const getStories = () => {
  try {
    return JSON.parse(localStorage.getItem('stories')) || mockStories;
  } catch {
    return mockStories;
  }
};
````

### Salida (extracto)
````markdown
### [ALTO] OBS-001 — Datos corruptos en localStorage se descartan sin registro
- **Ubicación:** `src/utils/storage.js:5`
- **Categoría:** Diagnóstico
- **Problema:** El `catch` vacío devuelve los mocks sin avisar.
- **Impacto:** Las historias guardadas "desaparecen" y nadie puede saber por qué.
- **Código sugerido:**
```js
  import { logger } from './logger';

  const STORAGE_KEY = 'stories';

  export const getStories = () => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return mockStories;
    try {
      return JSON.parse(raw);
    } catch (error) {
      logger.error('storage.read_failed', { key: STORAGE_KEY, length: raw.length }, error);
      return mockStories;
    }
  };
```

### [MEDIO] OBS-002 — Log suelto con texto completo del usuario y sin correlación
- **Ubicación:** `src/pages/NewStory.jsx:2`
- **Categoría:** Logs · Correlation · Métricas
- **Código sugerido:**
```js
  // src/utils/logger.js
  const isDev = import.meta.env.DEV;

  const write = (level, event, context = {}, error) => {
    if (level === 'debug' && !isDev) return;
    const entry = { timestamp: new Date().toISOString(), level, event, ...context };
    if (error) entry.error = { message: error.message, stack: error.stack };
    const method = level === 'debug' ? 'log' : level;
    console[method](`[${level.toUpperCase()}] ${event}`, entry);
  };

  export const logger = {
    debug: (event, context) => write('debug', event, context),
    info: (event, context) => write('info', event, context),
    warn: (event, context) => write('warn', event, context),
    error: (event, context, error) => write('error', event, context, error)
  };

  export const createOperationId = () =>
    (crypto.randomUUID ? crypto.randomUUID() : `op-${Date.now()}-${Math.random().toString(16).slice(2)}`);
```
```jsx
  // src/pages/NewStory.jsx
  const [operationId] = useState(createOperationId);

  const handleAnalyze = () => {
    const start = performance.now();
    logger.info('analysis.started', { operationId, descriptionLength: form.description.length, infoType: form.type });
    setLoading(true);
    setTimeout(() => {
      setAnalysis(mockAnalysis);
      setLoading(false);
      setStep(2);
      logger.info('analysis.completed', {
        operationId,
        durationMs: Math.round(performance.now() - start),
        known: mockAnalysis.knownData.length,
        missing: mockAnalysis.missingData.length
      });
    }, 1500);
  };
```
````

## References
- OpenTelemetry — conceptos de Logs, Metrics, Traces y propagación de contexto (W3C Trace Context).
- MDN — Console API, `performance.now()`, `crypto.randomUUID()`, Web Storage API.
- React Docs — Error Boundaries (`componentDidCatch`).
- Vite — Variables de entorno (`import.meta.env.DEV`).
- OWASP Logging Cheat Sheet — qué registrar y qué no.
- Google SRE Book — Monitoring Distributed Systems (señales de latencia, tráfico, errores y saturación).