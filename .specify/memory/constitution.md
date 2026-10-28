<!--
Sync Impact Report
==================
Versión: 0.0.0 (scaffold sin completar) → 1.0.0
Tipo de bump: ratificación inaugural (MAJOR inicial sobre un documento sin reglas de equipo).
Motivo: el archivo previo era la plantilla genérica de Spec Kit con marcadores sin resolver;
no contenía principios, secciones ni reglas de equipo que preservar.

Principios modificados:
- Ninguno. No existían principios previos; no se eliminó ninguna regla de equipo.

Principios añadidos:
- I. Disciplina de Ramas y Pull Request Revisado
- II. Cambios Gobernados por Spec Kit
- III. Stack Frontend Bloqueado: React + JavaScript + SCSS
- IV. Agentes Python en ./agentes/<nombre>
- V. Cero Secretos en Repositorio, Navegador y Trazas
- VI. Fidelidad del Rol Analista: PEAS y Semiautonomía Humana
- VII. Integraciones Honestas: OpenCode, LangChain, MCP y Langfuse
- VIII. Seguridad Read-Only y Mínimo Privilegio
- IX. No Regresión de Pantallas y Simulaciones
- X. Verificación Focalizada y Obligatoria
- XI. Arranque Documentado en Windows PowerShell

Secciones añadidas:
- Restricciones Técnicas y de Seguridad
- Flujo de Trabajo y Puertas de Calidad
- Governance

Secciones eliminadas:
- Ninguna.

Seguimientos pendientes:
- TODO(SOURCE_DOC): el documento "Definición Agentes Proyecto Popular Seguros..."
  (22 de octubre de 2026) no está presente en el repositorio. La constitución se derivó de
  specs/001-chat-flotante-analista/spec.md (que lo cita y resume), del prompt del Analista y
  de requerimientos_prototipo_historias_usuario.md. Verificar y ajustar cuando se aporte el
  documento fuente; cualquier ajuste requiere PR y bump de versión.
- El `.gitignore` actual ignora todo `.opencode/`, por lo que los comandos de Spec Kit no se
  versionan. Resolver en un cambio separado, sin tocar `main` directamente.
- La fecha de ratificación se fija en la fecha de esta adopción (2026-10-26) porque no existía
  una constitución ratificada previamente.
-->

# StoryCraft AI — Popular Seguros Constitution

Constitución del proyecto académico **StoryCraft AI** para **Popular Seguros**. Aplica al
frontend React existente, a los servicios de agentes en Python y a toda la documentación,
pruebas y configuración del repositorio. Las reglas son obligatorias y verificables.

## Core Principles

### I. Disciplina de Ramas y Pull Request Revisado

`main` es una rama protegida y de solo integración. Ningún integrante DEBE hacer commit, push,
force-push ni merge directo sobre `main`. Todo cambio DEBE realizarse en una rama de feature
creada desde `main` actualizado, con nombre descriptivo (`feat/<slug>`, `fix/<slug>`,
`docs/<slug>`, `test/<slug>`) y DEBE integrarse mediante Pull Request revisado por al menos otra
persona del equipo. El merge lo ejecuta una persona tras la aprobación; los merges automáticos
están prohibidos. La rama de trabajo vigente para el chat del Analista es
`feat/chat-agente-analista`.

**Racional:** mantener `main` siempre demostrable y evitar que una regresión llegue a la
presentación del curso sin revisión.

**Verificación:** `git log main` no contiene commits de trabajo directo; existe PR asociado a la
rama; la PR declara revisor y aprobación humana.

### II. Cambios Gobernados por Spec Kit

Todo cambio funcional, técnico o de documentación relevante DEBE pasar por el flujo Spec Kit:
constitución, `/speckit.specify`, `/speckit.clarify` cuando aplique, `/speckit.plan`,
`/speckit.tasks`, `/speckit.analyze` y `/speckit.implement`. No se escribe código de una
capacidad nueva antes de que existan especificación, plan y tareas coherentes. Las correcciones
menores DEBEN referenciar una especificación existente o abrir una mínima. Los artefactos viven
versionados en `specs/NNN-<nombre>/` y las desviaciones deliberadas respecto de los
requerimientos originales DEBEN quedar justificadas en la especificación. Esta constitución se
modifica solo mediante el procedimiento de Governance y su propio PR.

**Racional:** trazabilidad entre necesidad, decisión técnica, tarea y evidencia de validación.

**Verificación:** la PR enlaza spec, plan y tareas; `/speckit.analyze` no reporta
inconsistencias críticas abiertas; no hay implementación huérfana de especificación.

### III. Stack Frontend Bloqueado: React + JavaScript + SCSS

El frontend DEBE usar React 18, JavaScript con JSX, SCSS y las herramientas ya presentes
(Vite 5, React Router 6, componentes de `src/components/ui`). Está prohibido introducir
TypeScript (`*.ts`, `*.tsx`, `tsconfig*.json`), Bootstrap, Material UI, Tailwind, Chakra, Ant
Design, Redux, MobX, Zustand u otro gestor de estado o framework UI. Se permite reutilizar
`lucide-react` para iconografía y `react-markdown` + `remark-gfm` para Markdown seguro, sin
`rehype-raw`. `localStorage` se permite solo para persistencia simulada del prototipo. Toda
dependencia nueva DEBE justificarse en el plan, fijarse en el lockfile y ser aprobada por el
equipo; se prefiere la plataforma y los componentes existentes.

**Racional:** preservar la coherencia visual y la mantenibilidad del prototipo académico, y
evitar una migración de stack no solicitada.

**Verificación:** `npm run build` compila sin archivos TypeScript; `package.json` no incorpora
frameworks UI ni state managers prohibidos; los estilos nuevos usan SCSS y las variables
existentes.

### IV. Agentes Python en ./agentes/<nombre>

Cada agente se implementa como servicio Python independiente y encapsulado en
`./agentes/<nombre>/`, con al menos `api/`, `core/`, `mcp/`, `fuentes/`, `prompts/`, `tests/`,
`requirements.txt`, `.env.example` y `README.md`. El Analista reside en `./agentes/analista/`.
El prompt de sistema DEBE vivir en `prompts/sistema.md`, cargarse desde archivo y registrar su
versión o hash; su contenido no se hardcodea en Python. El navegador nunca importa ni ejecuta
código Python: se comunica solo mediante la API HTTP documentada del agente.

**Racional:** límites de responsabilidad claros, prompts auditables y despliegue local simple.

**Verificación:** la estructura existe; el prompt se carga externamente; el frontend solo llama
rutas `/api/<agente>/...`; ningún módulo React importa archivos de `agentes/`.

### V. Cero Secretos en Repositorio, Navegador y Trazas

Está prohibido versionar secretos, contraseñas, tokens, claves de API o credenciales, incluso en
el historial de Git. Tampoco DEBEN aparecer en el bundle de Vite, en `import.meta.env`, en
`localStorage`/`sessionStorage`, en URLs, en respuestas de API, en logs ni en trazas. El archivo
`.env` real DEBE permanecer ignorado y fuera de commits; `.env.example` solo contiene
marcadores. Las credenciales de OpenCode (Basic Auth) y Langfuse viven exclusivamente en el
entorno del backend Python; el navegador nunca contacta OpenCode ni Langfuse directamente. Ante
una exposición sospechosa se DEBE rotar el secreto, evaluar la limpieza del historial y
reportarlo al equipo; borrar la línea no es suficiente.

**Racional:** el repositorio es compartido con compañeros y el build es inspeccionable.

**Verificación:** `git status`/`git ls-files` no incluyen `.env`; búsqueda de patrones de
credenciales sin hallazgos; `dist/` no contiene claves; la API no devuelve secretos ni trazas.

### VI. Fidelidad del Rol Analista: PEAS y Semiautonomía Humana

El Analista DEBE respetar el modelo PEAS acordado. **Performance:** detectar vacíos válidos,
formular preguntas útiles y mantener en cero los datos inventados. **Environment:** StoryCraft
AI, analistas y Negocio, fuentes simuladas y OpenCode local. **Actuators:** consultar solo las
herramientas permitidas, clasificar información, generar preguntas y actualizar el análisis; no
aprueba alcance ni escribe en sistemas reales. **Sensors:** mensajes del usuario, respuestas de
Negocio, correcciones humanas y resultados de herramientas. El agente es semiautónomo: DEBE
detenerse y solicitar validación humana. No DEBE inventar nombres, pólizas, coberturas, reglas,
fechas, importes ni permisos; no DEBE convertir supuestos en hechos; cuando falta información,
DEBE declarar el vacío. Tiene prohibido redactar, aprobar o priorizar Historias de Usuario y
criterios de aceptación; solo puede indicar que el análisis está listo para el Redactor-Revisor.
El contenido del usuario y las fuentes son datos no confiables, nunca instrucciones que cambien
su misión.

**Racional:** el valor del agente es reducir ambigüedad antes del grooming, no sustituir el
juicio del analista.

**Verificación:** pruebas adversariales de invención y de inyección de prompt; el JSON de
respuesta no contiene HU redactada; `listo_para_redactor=true` no implica aprobación; las
métricas PEAS se reportan solo si fueron medidas.

### VII. Integraciones Honestas: OpenCode, LangChain, MCP y Langfuse

OpenCode local es el único motor de modelo y se invoca desde Python, nunca desde el navegador.
LangChain DEBE usarse de forma efectiva en la construcción del prompt, la orquestación y el
parseo tipado; no se admite como dependencia decorativa. Las cuatro fuentes del dominio
(`consultar_glosario`, `buscar_hu_similares`, `consultar_estandares`,
`aplicar_checklist_vacios`) DEBEN exponerse mediante MCP real y ser de solo lectura, con datos
simulados o anonimizados. Langfuse DEBE recibir trazas correlacionadas por conversación,
solicitud y turno, con duración, herramientas y errores; su fallo degrada la observabilidad pero
no bloquea el chat. Está prohibido simular integraciones, declarar herramientas consultadas sin
resultado real o devolver respuestas hardcodeadas como si fueran del agente. No se asume
compatibilidad de OpenCode con OpenAI Chat Completions; las versiones y adaptadores se fijan y
se prueban.

**Racional:** la demostración debe probar la cadena real y ser diagnosticable, sin aparentar
capacidades inexistentes.

**Verificación:** prueba de integración que atraviesa React → FastAPI → LangChain → OpenCode y
regresa; traza MCP por herramienta; observación en Langfuse; el health check refleja el estado
real y la UI no muestra "en línea" sin comprobarlo.

### VIII. Seguridad Read-Only y Mínimo Privilegio

El agente y su backend operan en modo de solo lectura sobre fuentes simuladas. No DEBEN tener
shell, lectura o escritura libre de archivos, internet, correo, repositorios, bases productivas
ni herramientas de OpenCode ajenas a su tarea. La allowlist se aplica en Python y en los
permisos del servidor OpenCode, no solo en el prompt. El servicio escucha en `127.0.0.1`; se
prohíbe `0.0.0.0` por defecto y CORS `*`. Se DEBEN validar entradas y tamaños, aplicar timeouts,
permitir una sola solicitud en vuelo por conversación, soportar aborto y reset, y devolver
errores controlados sin stack traces, rutas internas ni credenciales. El Markdown se renderiza
sin HTML crudo y con enlaces saneados. Los retrasos o datos simulados DEBEN identificarse como
tales y nunca presentarse como procesamiento real.

**Racional:** reducir superficie de ataque en una demo local y evitar daños o filtraciones.

**Verificación:** pruebas de allowlist, timeout, 409 por concurrencia, reset durante generación,
render XSS y ausencia de rutas de escritura o shell.

### IX. No Regresión de Pantallas y Simulaciones

Las rutas existentes (`/`, `/historias`, `/historias/nueva`, `/historias/:id`,
`/historias/:id/editar`, `/ayuda`), el Dashboard, el listado, el Stepper, el Accordion, los datos
mock, las claves de `localStorage` y el estilo visual DEBEN seguir funcionando. La capacidad real
de IA es aditiva: no reemplaza la generación simulada del Stepper ni elimina pantallas sin una
especificación nueva que lo autorice. Todo cambio intencional de comportamiento, ruta o esquema
de persistencia DEBE incluir evidencia antes/después, ruta de migración o reinicio seguro y
aprobación en la PR. No se DEBE romper la navegación ni el responsive en escritorio, tableta o
móvil.

**Racional:** el prototipo ya es demostrable y la nueva fase no puede costar lo ya logrado.

**Verificación:** build y recorrido manual de todas las rutas; pruebas del Stepper y del chat en
paralelo; revisión de que las claves de `localStorage` se conservan o migran.

### X. Verificación Focalizada y Obligatoria

Toda capacidad nueva DEBE incluir pruebas automatizadas focalizadas, no exhaustivas, en cinco
frentes: (1) API y validación de contratos y errores; (2) reset durante una generación activa y
descarte de respuestas tardías; (3) concurrencia y rechazo de envíos duplicados; (4) render
seguro de Markdown y resistencia a XSS; (5) flujo del agente, allowlist de herramientas,
ausencia de invención y salida estructurada válida. Cuando se integren OpenCode, MCP o Langfuse
se DEBE añadir una prueba manual end-to-end controlada. Ninguna PR se fusiona con pruebas rojas;
una prueba inestable se corrige o se aísla con incidencia registrada, nunca se ignora. Esta
regla sustituye de forma deliberada la prohibición de pruebas automatizadas del prototipo
original para esta fase; el resto del alcance original sigue vigente. Las métricas o tiempos de
respuesta solo se reportan si fueron medidos.

**Racional:** los fallos más costosos del chat son concurrencia, reset y render inseguro, no la
cobertura global.

**Verificación:** `pytest` del backend y pruebas de frontend del chat en verde; evidencia de la
prueba manual; PR con resultados adjuntos.

### XI. Arranque Documentado en Windows PowerShell

Todo cambio que afecte la ejecución DEBE actualizar la documentación con comandos reproducibles
para **Windows PowerShell**: requisitos previos y versión de Python, creación del entorno
virtual, instalación de dependencias, copia de `.env.example` a `.env`, arranque de OpenCode,
FastAPI y Vite, ejecución de pruebas, health checks, apagado y solución de problemas. Los
comandos DEBEN funcionar desde la raíz del repositorio, indicar puertos y rutas reales y no
incluir secretos. La documentación se actualiza en la misma PR que el cambio de comportamiento.
No se aceptan instrucciones ambiguas ni dependientes de una máquina específica.

**Racional:** el equipo y el profesor deben poder levantar frontend, API, OpenCode y MCP sin
improvisar.

**Verificación:** un integrante distinto al autor sigue la guía en PowerShell y logra el flujo;
los health checks responden; no hay secretos en los ejemplos.

## Restricciones Técnicas y de Seguridad

- **Naturaleza del proyecto:** prototipo académico y demostración local para Popular Seguros; no
  es una solución productiva y no DEBE presentarse como tal.
- **Datos:** solo ficticios o anonimizados. Se prohíbe usar datos reales de asegurados, pólizas o
  siniestros, y registrar datos personales en logs o trazas.
- **Stack verificado:** Vite 5, React 18, React Router 6, JavaScript y SCSS. El backend propuesto
  usa FastAPI con Pydantic, httpx, LangChain, MCP y Langfuse; Python `>=3.11` es una propuesta
  sujeta a verificación local y debe documentarse la versión realmente usada.
- **Frontera de confianza:** el navegador solo habla con `/api/analista/...` por loopback o proxy
  de Vite. Las credenciales y el contacto con OpenCode y Langfuse son exclusivos del backend.
- **Contrato de respuesta:** el backend valida un esquema tipado que incluye
  `respuesta_markdown`, las cuatro clasificaciones (conocida, faltante, supuesta, ambigua),
  preguntas y fuentes consultadas. Si la validación falla se devuelve un error controlado; nunca
  se renderiza JSON crudo como mensaje de chat.
- **Alcance excluido:** integraciones productivas con Azure DevOps, iTop, correo, repositorios
  reales, internet o bases de datos; autenticación productiva; multiusuario; adjuntos; voz;
  streaming token a token; sistema multiagente; persistencia histórica permanente.
- **Fuera de alcance del rol:** implementar el Redactor-Revisor, Asesor Técnico o Gestor de
  Cambios, y automatizar la generación o aprobación de HU en el Stepper.

## Flujo de Trabajo y Puertas de Calidad

1. Actualizar `main` local, crear la rama de feature y confirmar que HEAD está en ella.
2. Ejecutar Spec Kit y dejar especificación, plan y tareas coherentes antes de programar.
3. Implementar por incrementos pequeños, con pruebas focalizadas y sin tocar `main`.
4. Abrir PR hacia `main` con alcance, evidencia, riesgos y pasos de verificación.
5. Obtener revisión humana y fusionar solo tras aprobación explícita.

**Puertas obligatorias antes del merge:**

- **G1 — Consistencia Spec Kit:** artefactos presentes, sin contradicciones críticas abiertas.
- **G2 — Build:** `npm run build` exitoso y sin archivos TypeScript.
- **G3 — Pruebas:** pruebas focalizadas de API, reset, concurrencia, render seguro y agente en
  verde, más la prueba manual de integración cuando corresponda.
- **G4 — Secretos y datos:** `.env` fuera de Git, sin credenciales en `dist/` ni en logs, sin
  datos personales en trazas.
- **G5 — No regresión:** rutas, pantallas, Stepper y simulaciones verificadas.
- **G6 — Documentación:** arranque en Windows PowerShell y health checks actualizados.
- **G7 — Revisión:** PR revisada por otra persona, sin merge automático ni escritura directa a
  `main`.

**Definition of Done:** comportamiento especificado y demostrable, pruebas y build en verde,
documentación actualizada, evidencia adjunta en la PR y aprobación humana registrada. Las
excepciones a G1–G6 se documentan y acotan en la PR con aprobación del equipo; no existen
excepciones para secretos ni para escritura directa a `main`.

## Governance

Esta constitución prevalece sobre prácticas, costumbres y decisiones ad hoc del equipo. Si un
documento, plan o tarea la contradice, prevalece la constitución hasta que sea enmendada.

**Procedimiento de enmienda:** toda modificación se propone en una rama `docs/constitution-<slug>`
creada desde `main`, mediante PR que incluya motivación, impacto en principios y artefactos,
plan de migración cuando aplique y la versión resultante. Requiere revisión y aprobación del
equipo; nunca se aplica directamente sobre `main`. El informe de impacto de sincronización es
material temporal de revisión y DEBE retirarse antes de fusionar la PR.

**Política de versiones (SemVer):**

- **MAJOR:** eliminación o redefinición incompatible de principios o reglas de Governance.
- **MINOR:** nuevo principio o sección, o expansión material de la guía existente.
- **PATCH:** aclaraciones, correcciones de redacción o refinamientos no semánticos.

La versión y las fechas se registran en la línea final. Las fechas usan formato ISO
`YYYY-MM-DD`.

**Revisión de cumplimiento:** cada PR y cada `/speckit.analyze` DEBEN verificar los principios
aplicables y declarar el resultado. Una violación bloquea el merge hasta corregirse o hasta una
enmienda aprobada. El equipo revisa la constitución al cierre de cada fase del curso y cuando
cambie el alcance. La complejidad añadida DEBE justificarse frente a la alternativa más simple.

**Artefactos de referencia:** `.specify/memory/constitution.md`, `specs/`,
`agentes/<nombre>/prompts/sistema.md`, `requerimientos_prototipo_historias_usuario.md` y los
README de arranque.

**Version**: 1.0.0 | **Ratified**: 2026-10-26 | **Last Amended**: 2026-10-26
