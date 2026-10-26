---
name: error-handling-resilience-review
description: Revisa código React + JavaScript del proyecto para evaluar manejo de excepciones, retries, timeouts, circuit breakers, fallback, rate limiting y degradación controlada. Usar al revisar páginas, componentes con lógica, acceso a localStorage, procesos simulados de IA y navegación por rutas con id.
---

# Error Handling & Resilience Review

## Purpose
Asegurar que la aplicación **nunca quede en pantalla en blanco ni en un estado roto**: que los errores se capturen donde corresponde, que el usuario siempre vea un mensaje claro y una forma de continuar, y que un problema en una parte (datos corruptos, un componente que falla, un proceso que no termina) no tumbe toda la aplicación.

Aunque hoy el análisis y la generación con IA son simulados, la skill también verifica que el código esté preparado para cuando se reemplacen por llamadas reales (timeouts, reintentos, cancelación).

## When to Use
- Al revisar un PR o cambio que agrega o modifica páginas, componentes con lógica o utilidades.
- Al revisar la lectura y escritura en `localStorage`.
- Al revisar los procesos simulados ("Analizando requerimiento...", "Generando Historia de Usuario...").
- Al revisar rutas con parámetros (`/historias/:id`, `/historias/:id/editar`).
- Cuando se reporta una pantalla en blanco, un botón que no responde o datos que se pierden.

## When NOT to Use
- Logs, correlation IDs, métricas o health checks → usar `observability-review`.
- Validaciones de formulario por reglas de negocio (el documento del prototipo las excluye), salvo cómo se muestran sus errores.
- Revisión de estilos, diseño o responsive.
- Cumplimiento funcional contra el documento de requerimientos.

## Inputs
- **Obligatorio:** archivos, carpeta o diff a revisar (normalmente dentro de `src/`).
- **Recomendado:** `App.jsx` (rutas), `main.jsx`, `src/utils/` (storage, simulación de IA), páginas del flujo de creación y edición.
- **Opcional:** descripción del error o escenario reportado.

## Analysis Process
1. **Mapear los puntos de falla:** lectura/escritura en `localStorage`, parseo JSON, rutas con id, procesos asíncronos simulados, componentes que reciben datos que pueden venir vacíos.
2. **Revisar la red de seguridad global:** `ErrorBoundary` alrededor de las rutas, ruta comodín `*` para páginas inexistentes.
3. **Revisar el manejo de excepciones:** `try/catch` en los puntos de falla, sin `catch` vacíos, mensajes claros al usuario.
4. **Revisar estados de UI:** cada pantalla con datos tiene estados de carga, vacío y error.
5. **Revisar procesos asíncronos:** timeouts, cancelación al desmontar el componente o salir del paso, prevención de doble clic.
6. **Revisar reintentos:** que el usuario pueda reintentar una operación fallida y que exista un límite.
7. **Revisar fallback y degradación:** qué pasa si `localStorage` no está disponible o los datos están corruptos.
8. **Simular escenarios de fallo:**
   - JSON inválido en `localStorage`.
   - `localStorage` lleno o bloqueado (modo privado).
   - Navegar a `/historias/999` o `/historias/abc/editar`.
   - Hacer doble clic en "Analizar requerimiento" o "Guardar Historia".
   - Salir del Stepper mientras "Generando Historia de Usuario..." está en curso.
   - Historia sin criterios, sin preguntas o sin análisis.
9. **Clasificar los hallazgos** y redactar el reporte.

## Rules
- Citar siempre **archivo y línea** (o componente) de cada hallazgo.
- Toda recomendación incluye **código completo** listo para pegar.
- Un `catch` vacío o que oculta el error sin registrarlo ni avisar es siempre **Alto**.
- El usuario nunca debe ver un stack trace, `undefined`, `NaN` ni una pantalla en blanco.
- Todo mensaje de error al usuario dice qué pasó y qué puede hacer ("No se pudo guardar la historia. Intente nuevamente.").
- Reintentar solo operaciones seguras de repetir; en este proyecto: lecturas, análisis y generación simulados. Guardar debe evitar duplicados (verificar id antes de insertar).
- Todo proceso asíncrono debe poder cancelarse al desmontar el componente (limpiar `setTimeout` o usar `AbortController`).
- Los botones que disparan procesos se deshabilitan mientras están en curso.
- Usar los componentes reutilizables del proyecto (`Alert`, `EmptyState`, `Button`) para mostrar errores; no crear markup nuevo por pantalla.
- Calibrar a prueba de concepto: circuit breaker y rate limiting de servidor no aplican mientras no haya backend. Evaluarlos como **Info** ("preparación para IA real") y no como incumplimiento.
- Coordinar con `observability-review`: aquí se evalúa cómo se recupera la app; que el error quede registrado se menciona pero se detalla en la otra skill.
- Reconocer lo que está bien hecho en "Fortalezas".
- Responder en español.

## Checklist

### Manejo de excepciones
- [ ] Existe un `ErrorBoundary` que envuelve las rutas y muestra una pantalla de recuperación con opción de volver al Dashboard.
- [ ] Existe una ruta `*` con página de "no encontrado".
- [ ] `JSON.parse` siempre dentro de `try/catch`.
- [ ] `localStorage.setItem` dentro de `try/catch` (puede fallar por cuota o por modo privado).
- [ ] No hay `catch` vacíos.
- [ ] Los errores se registran mediante el logger del proyecto.
- [ ] Mensajes de error claros y en español, mostrados con `Alert`.

### Datos nulos y defensivos
- [ ] Los componentes toleran props vacías con valores por defecto (como hace `AnalysisCard` con `analysis || {}`).
- [ ] Las páginas con `:id` manejan historia inexistente con `EmptyState` y botón para volver.
- [ ] Listas vacías muestran `EmptyState`, no una grilla vacía.
- [ ] Acceso a propiedades anidadas con encadenamiento opcional (`story?.criteria?.length`).

### Retries
- [ ] Si el análisis o la generación fallan, se ofrece un botón "Reintentar".
- [ ] Hay un máximo de reintentos (ej. 3) antes de sugerir revisar la información.
- [ ] Guardar es idempotente: no duplica la historia si se presiona dos veces o se reintenta.
- [ ] Preparación para IA real: la función de simulación tiene la misma forma que tendría la llamada real (devuelve una `Promise`), para poder agregar reintentos con backoff sin cambiar las pantallas.

### Timeouts y cancelación
- [ ] Los `setTimeout` de las simulaciones se limpian al desmontar el componente.
- [ ] Salir del Stepper durante un proceso no produce actualizaciones de estado sobre un componente desmontado.
- [ ] Preparación para IA real: existe un tiempo máximo de espera y el usuario ve un mensaje si se excede.

### Circuit breaker (preparación)
- [ ] Info: si en el futuro se integra una API de IA, se deja documentado que tras varios fallos seguidos se deshabilite temporalmente la acción y se informe al usuario.

### Fallback y degradación controlada
- [ ] Si `localStorage` no está disponible, la app funciona en memoria y muestra un aviso ("Los cambios no se conservarán al recargar").
- [ ] Si los datos guardados están corruptos, se usan los mocks y se avisa, sin perder silenciosamente la información.
- [ ] Si falla una sección del Accordion de edición, las demás siguen funcionando.
- [ ] La falla de algo secundario (ej. contador del Dashboard) no bloquea la navegación.

### Rate limiting (del lado del cliente)
- [ ] Botones de proceso deshabilitados mientras corren ("Analizar requerimiento", "Generar Historia de Usuario", "Guardar Historia").
- [ ] No se pueden disparar dos procesos iguales en paralelo.
- [ ] Info: si hubiera API, manejar respuestas 429 mostrando un mensaje de espera.

## Severity / Priority
| Severidad | Criterio | Ejemplo en este proyecto |
|---|---|---|
| **Alto** | Pantalla en blanco, pérdida de datos o error oculto. | Sin `ErrorBoundary`; `catch {}` vacío; `/historias/999` rompe el render; doble clic duplica la historia. |
| **Medio** | La app no se rompe, pero el usuario queda sin salida o sin información. | Proceso simulado sin cancelación; lista vacía sin `EmptyState`; error sin opción de reintentar; botón no deshabilitado durante el proceso. |
| **Bajo** | Mejora de claridad o consistencia. | Mensajes de error poco claros o en inglés; errores mostrados sin usar `Alert`. |
| **Info** | Preparación para IA real o backend, o fortaleza observada. | Timeouts con `AbortController`, backoff exponencial, circuit breaker, manejo de 429. |

No se usa "Crítico" porque el proyecto es una prueba de concepto sin datos reales ni usuarios en producción.

## Output Format
````markdown
# Error Handling & Resilience Review — <componente / flujo / PR>

## Resumen
- Alcance revisado: <archivos>
- Calificación general: <Resiliente | Mejorable | Frágil>
- Hallazgos: Alto X · Medio X · Bajo X · Info X

## Fortalezas
- ...

## Escenarios de fallo probados
| Escenario | Resultado actual | Esperado | Estado |
|---|---|---|---|
| JSON inválido en localStorage | Pantalla en blanco | Mocks + aviso | ❌ |

## Hallazgos
### [SEVERIDAD] RES-001 — <título corto>
- **Ubicación:** `src/ruta/Archivo.jsx:línea`
- **Categoría:** Excepciones | Datos nulos | Retries | Timeouts | Circuit breaker | Fallback | Rate limiting
- **Problema:** <qué pasa>
- **Escenario de fallo:** <cómo se reproduce>
- **Impacto:** <qué ve o pierde el usuario>
- **Recomendación:** <acción concreta>
- **Código sugerido:**
```jsx
  // código completo
```

## Preparación para IA real (Info)
- ...

## No verificable
- <archivos no proporcionados>

## Próximos pasos priorizados
1. ...
````

## Examples

### Entrada
````jsx
// pages/StoryDetail.jsx
const { id } = useParams();
const story = getStories().find((s) => s.id === Number(id));
return <h1>{story.title}</h1>;

// pages/NewStory.jsx
const handleGenerate = () => {
  setLoading(true);
  setTimeout(() => {
    setStory(mockStory);
    setLoading(false);
    setStep(4);
  }, 2000);
};
<Button onClick={handleGenerate}>Generar Historia de Usuario</Button>
````

### Salida (extracto)
````markdown
### [ALTO] RES-001 — Historia inexistente rompe la pantalla
- **Ubicación:** `src/pages/StoryDetail.jsx:3`
- **Escenario de fallo:** navegar a `/historias/999`.
- **Impacto:** `story` es `undefined` y la app queda en blanco.
- **Código sugerido:**
```jsx
  const { id } = useParams();
  const navigate = useNavigate();
  const story = getStories().find((s) => String(s.id) === id);

  if (!story) {
    return (
      <EmptyState
        title="Historia no encontrada"
        description={`No existe una historia con el identificador ${id}.`}
        actionLabel="Volver a Historias"
        onAction={() => navigate('/historias')}
      />
    );
  }

  return <h1>{story.title}</h1>;
```

### [MEDIO] RES-002 — Generación sin cancelación ni bloqueo de doble clic
- **Ubicación:** `src/pages/NewStory.jsx:7-14`
- **Escenario de fallo:** presionar dos veces el botón, o salir de la página antes de 2 segundos.
- **Código sugerido:**
```js
  // src/utils/aiSimulator.js
  export const simulateAiTask = (result, { delayMs = 2000, signal } = {}) =>
    new Promise((resolve, reject) => {
      const timer = setTimeout(() => resolve(result), delayMs);
      signal?.addEventListener('abort', () => {
        clearTimeout(timer);
        reject(new DOMException('Operación cancelada', 'AbortError'));
      });
    });
```
```jsx
  // src/pages/NewStory.jsx
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const handleGenerate = async () => {
    if (loading) return;
    controllerRef.current = new AbortController();
    setLoading(true);
    setError(null);
    try {
      const result = await simulateAiTask(mockStory, { signal: controllerRef.current.signal });
      setStory(result);
      setStep(4);
    } catch (err) {
      if (err.name === 'AbortError') return;
      logger.error('story.generation_failed', { operationId }, err);
      setError('No se pudo generar la Historia de Usuario. Intente nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  {error && <Alert variant="error" action={{ label: 'Reintentar', onClick: handleGenerate }}>{error}</Alert>}
  <Button onClick={handleGenerate} disabled={loading}>
    {loading ? 'Generando Historia de Usuario...' : 'Generar Historia de Usuario'}
  </Button>
```
````

## References
- React Docs — Error Boundaries, `useEffect` cleanup, manejo de estados de carga y error.
- React Router v6 — rutas comodín (`*`), `errorElement`, `useParams`.
- MDN — `try...catch`, `AbortController`, `Promise`, Web Storage API (`QuotaExceededError`).
- Azure Architecture Center — patrones Retry, Circuit Breaker y Throttling (referencia para la fase con IA real).
- Nielsen Norman Group — Error Message Guidelines.
- Michael Nygard — *Release It!* (stability patterns).