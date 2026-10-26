export const skillsData = [
  {
    id: 'error-handling-resilience-review',
    name: 'error-handling-resilience-review',
    title: 'Error Handling & Resilience Review',
    category: 'Resiliencia y Manejo de Errores',
    categoryTag: 'resilience',
    path: '.agents/skills/error-handling-resilience-review/SKILL.md',
    description:
      'Revisa código React + JavaScript del proyecto para evaluar manejo de excepciones, retries, timeouts, circuit breakers, fallback, rate limiting y degradación controlada. Usar al revisar páginas, componentes con lógica, acceso a localStorage, procesos simulados de IA y navegación por rutas con id.',
    purpose:
      'Asegurar que la aplicación nunca quede en pantalla en blanco ni en un estado roto: que los errores se capturen donde corresponde, que el usuario siempre vea un mensaje claro y una forma de continuar, y que un problema en una parte no tumbe toda la aplicación.',
    whenToUse: [
      'Al revisar un PR o cambio que agrega o modifica páginas, componentes con lógica o utilidades.',
      'Al revisar la lectura y escritura en localStorage.',
      'Al revisar los procesos simulados ("Analizando requerimiento...", "Generando Historia de Usuario...").',
      'Al revisar rutas con parámetros (/historias/:id, /historias/:id/editar).',
      'Cuando se reporta una pantalla en blanco, un botón que no responde o datos que se pierden.'
    ],
    whenNotToUse: [
      'Logs, correlation IDs, métricas o health checks → usar observability-review.',
      'Validaciones de formulario por reglas de negocio, salvo cómo se muestran sus errores.',
      'Revisión de estilos, diseño o responsive.',
      'Cumplimiento funcional contra el documento de requerimientos.'
    ],
    checklistSections: [
      {
        title: 'Manejo de excepciones',
        items: [
          'Existe un ErrorBoundary que envuelve las rutas y muestra una pantalla de recuperación con opción de volver al Dashboard.',
          'Existe una ruta "*" con página de "no encontrado".',
          'JSON.parse siempre dentro de try/catch.',
          'localStorage.setItem dentro de try/catch (puede fallar por cuota o por modo privado).',
          'No hay catch vacíos.',
          'Los errores se registran mediante el logger del proyecto.',
          'Mensajes de error claros y en español, mostrados con Alert.'
        ]
      },
      {
        title: 'Datos nulos y defensivos',
        items: [
          'Los componentes toleran props vacías con valores por defecto (como hace AnalysisCard con analysis || {}).',
          'Las páginas con :id manejan historia inexistente con EmptyState y botón para volver.',
          'Listas vacías muestran EmptyState, no una grilla vacía.',
          'Acceso a propiedades anidadas con encadenamiento opcional (story?.criteria?.length).'
        ]
      },
      {
        title: 'Retries',
        items: [
          'Si el análisis o la generación fallan, se ofrece un botón "Reintentar".',
          'Hay un máximo de reintentos (ej. 3) antes de sugerir revisar la información.',
          'Guardar es idempotente: no duplica la historia si se presiona dos veces o se reintenta.',
          'Preparación para IA real: la función de simulación tiene la misma forma que tendría la llamada real (devuelve una Promise).'
        ]
      },
      {
        title: 'Timeouts y cancelación',
        items: [
          'Los setTimeout de las simulaciones se limpian al desmontar el componente.',
          'Salir del Stepper durante un proceso no produce actualizaciones de estado sobre un componente desmontado.',
          'Preparación para IA real: existe un tiempo máximo de espera y el usuario ve un mensaje si se excede.'
        ]
      },
      {
        title: 'Circuit breaker (preparación)',
        items: [
          'Info: si en el futuro se integra una API de IA, se deja documentado que tras varios fallos seguidos se deshabilite temporalmente la acción y se informe al usuario.'
        ]
      },
      {
        title: 'Fallback y degradación controlada',
        items: [
          'Si localStorage no está disponible, la app funciona en memoria y muestra un aviso ("Los cambios no se conservarán al recargar").',
          'Si los datos guardados están corruptos, se usan los mocks y se avisa, sin perder silenciosamente la información.',
          'Si falla una sección del Accordion de edición, las demás siguen funcionando.',
          'La falla de algo secundario (ej. contador del Dashboard) no bloquea la navegación.'
        ]
      },
      {
        title: 'Rate limiting (del lado del cliente)',
        items: [
          'Botones de proceso deshabilitados mientras corren ("Analizar requerimiento", "Generar Historia de Usuario", "Guardar Historia").',
          'No se pueden disparar dos procesos iguales en paralelo.',
          'Info: si hubiera API, manejar respuestas 429 mostrando un mensaje de espera.'
        ]
      }
    ],
    references: [
      'React Docs — Error Boundaries, useEffect cleanup, manejo de estados de carga y error.',
      'React Router v6 — rutas comodín (*), errorElement, useParams.',
      'MDN — try...catch, AbortController, Promise, Web Storage API (QuotaExceededError).',
      'Azure Architecture Center — patrones Retry, Circuit Breaker y Throttling (referencia para la fase con IA real).',
      'Nielsen Norman Group — Error Message Guidelines.',
      'Michael Nygard — Release It! (stability patterns).'
    ]
  },
  {
    id: 'observability-review',
    name: 'observability-review',
    title: 'Observability Review',
    category: 'Observabilidad y Diagnóstico',
    categoryTag: 'observability',
    path: '.agents/skills/observability-review/SKILL.md',
    description:
      'Revisa código React + JavaScript del proyecto para verificar logs estructurados, métricas, trazas de operaciones, correlation IDs, health checks y capacidad de diagnóstico en el navegador. Usar al revisar componentes, páginas, utilidades o flujos simulados (análisis y generación con IA, guardado en localStorage).',
    purpose:
      'Asegurar que cuando algo falla o se comporta raro en la aplicación, cualquier persona del equipo pueda entender qué pasó revisando la consola del navegador, sin tener que depurar línea por línea.',
    whenToUse: [
      'Al revisar un PR o cambio que agrega o modifica páginas, componentes con lógica, utilidades de utils/ o acceso a localStorage.',
      'Al revisar los flujos simulados: "Analizando requerimiento...", "Generando Historia de Usuario...", "Guardar Historia".',
      'Cuando alguien reporta un comportamiento que no se pudo reproducir o explicar.',
      'Cuando se pide revisar "logs", "consola", "trazabilidad", "diagnóstico" o "telemetría".'
    ],
    whenNotToUse: [
      'Manejo de errores, reintentos, timeouts o fallback → usar error-handling-resilience-review.',
      'Componentes puramente visuales sin lógica (ej. Badge, Card, PageTitle).',
      'Revisión de estilos SCSS, diseño o responsive.',
      'Cumplimiento funcional contra el documento de requerimientos.'
    ],
    checklistSections: [
      {
        title: 'Logs estructurados',
        items: [
          'Existe src/utils/logger.js con niveles debug, info, warn, error.',
          'No hay console.* directos en componentes ni páginas.',
          'Cada log tiene nombre de evento y objeto de contexto.',
          'Niveles bien usados: error para fallos, warn para situaciones recuperables, info para hitos del flujo, debug para detalle.',
          'Los errores se registran con el objeto Error completo (mensaje y stack), no solo error.message.',
          'debug deshabilitado fuera de desarrollo.',
          'Sin textos completos del usuario ni datos sensibles en los logs.'
        ]
      },
      {
        title: 'Correlation IDs',
        items: [
          'Existe un generador de IDs (crypto.randomUUID() con fallback).',
          'Cada flujo de creación o edición inicia un operationId y lo propaga a todos sus logs.',
          'El operationId se conserva entre pasos del Stepper (estado del flujo, no una variable local de cada paso).',
          'Si en el futuro hay llamadas HTTP, el ID se envía en un header (X-Correlation-Id).'
        ]
      },
      {
        title: 'Trazas de operaciones',
        items: [
          'Las operaciones simuladas registran inicio y fin (analysis.started / analysis.completed).',
          'Se registra el paso actual del Stepper al avanzar o retroceder.',
          'Se registran las acciones clave del usuario: guardar, editar, abrir historia.'
        ]
      },
      {
        title: 'Métricas',
        items: [
          'Duración de análisis y generación medida con performance.now().',
          'Conteos útiles: historias cargadas, preguntas pendientes vs respondidas, criterios generados.',
          'Las métricas se registran como logs estructurados con campo numérico (durationMs, count).'
        ]
      },
      {
        title: 'Health checks',
        items: [
          'Al iniciar la app se verifica que localStorage esté disponible.',
          'Se valida que los datos guardados tengan la estructura esperada (versión de esquema o campos mínimos).',
          'El resultado del chequeo queda registrado (app.health con estado ok o degraded).',
          'Existe una forma simple de ver el estado (log en consola o sección en la pantalla de Ayuda en modo desarrollo).'
        ]
      },
      {
        title: 'Diagnosticabilidad',
        items: [
          'Un ErrorBoundary registra errores de renderizado con el componente y la ruta.',
          'Rutas con id inexistente registran un warn con el id solicitado.',
          'Un error en localStorage indica qué clave falló y por qué.',
          'Con solo la consola se puede reconstruir qué hizo el usuario antes del fallo.'
        ]
      }
    ],
    references: [
      'OpenTelemetry — conceptos de Logs, Metrics, Traces y propagación de contexto (W3C Trace Context).',
      'MDN — Console API, performance.now(), crypto.randomUUID(), Web Storage API.',
      'React Docs — Error Boundaries (componentDidCatch).',
      'Vite — Variables de entorno (import.meta.env.DEV).',
      'OWASP Logging Cheat Sheet — qué registrar y qué no.',
      'Google SRE Book — Monitoring Distributed Systems (señales de latencia, tráfico, errores y saturación).'
    ]
  }
];
