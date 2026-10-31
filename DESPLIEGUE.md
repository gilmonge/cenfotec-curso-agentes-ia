# Despliegue en Render

La aplicación completa (interfaz, backend del Agente Analista y OpenCode Server) se publica como **un solo servicio con un solo URL**. Cada cambio que se une a `main` se despliega solo. Para trabajar los cambios sigues usando tu entorno local.

## Flujo de trabajo

1. Trabajas en local: `npm run iniciar` (igual que hoy, con tu `.env`).
2. Subes una rama y abres un PR en GitHub.
3. Al unir el PR a `main`, Render construye la imagen y publica la nueva versión sin intervención.
4. El equipo entra por el URL de Render con el usuario y la clave compartidos.

## Primera vez

1. En Render: **New → Blueprint** y selecciona el repositorio `Yuvania/historias-de-usuario-cenfotec-proyecto`. Render lee `render.yaml`.
2. Completa los valores que se piden (no se guardan en el repositorio):

| Variable | Qué es |
|---|---|
| `OPENCODE_API_KEY` | Clave del plan OpenCode Go (la misma que usas en local, pero crea una **nueva** para el servidor). |
| `ACCESO_USUARIO` / `ACCESO_CLAVE` | Usuario y clave compartidos con el equipo para entrar al URL. Usa una clave larga. |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Opcionales. Déjalas vacías si no usas Langfuse en el servidor. |

3. Ya vienen definidas en `render.yaml`: `ANALISTA_PUBLICO=1` (obliga a tener usuario y clave; si faltan, el servicio no inicia), `OPENCODE_PROVIDER_ID`, `OPENCODE_MODEL_ID` y `OPENCODE_SERVER_PASSWORD` (la genera Render).
4. Espera el primer despliegue (varios minutos) y abre el URL `https://<nombre>.onrender.com`. El navegador pedirá el usuario y la clave.
5. Verifica el agente con `https://<nombre>.onrender.com/api/analista/health` (con las mismas credenciales) y crea una historia de prueba.

## Variables de entorno

Se cambian en el panel de Render (**Environment**); al guardar, Render reinicia el servicio.

| Variable | Obligatoria | Uso |
|---|---|---|
| `ANALISTA_PUBLICO` | Sí en Render | Con `1` exige usuario y clave de acceso. |
| `ACCESO_USUARIO`, `ACCESO_CLAVE` | Sí en Render | Acceso al URL. |
| `OPENCODE_SERVER_PASSWORD` | Sí | Clave interna entre el backend y OpenCode (la genera Render). |
| `OPENCODE_API_KEY` | Sí | Credencial del modelo. |
| `OPENCODE_PROVIDER_ID`, `OPENCODE_MODEL_ID` | Sí | Modelo a usar (`opencode-go` / `glm-5.3-flash`). |
| `DATABASE_URL` | Sí en Render | Cadena de conexión de la base MySQL compatible (TiDB Cloud Starter). Sin ella se usa un SQLite local que **se pierde** en cada despliegue. |
| `DATABASE_SSL` | No | Con `0` desactiva TLS hacia la base (solo para una base local); por defecto está activo. |
| `ANALISTA_REPO_DB` | No | Ruta del SQLite local cuando no hay `DATABASE_URL` (desarrollo). |
| `LANGFUSE_*` | No | Observabilidad. |
| `VITE_ANIO`, `VITE_VERSION` | No | Año y versión del pie de página: «HISTORIAS DE USUARIO ® Derechos Reservados *año* - V.*versión*». Son de **compilación**: al cambiarlos Render vuelve a construir la imagen. Por defecto: año actual y `1.0.0`. |
| `VITE_PREFIJO_HU` | No | Prefijo del número de la HU. Es de **compilación**: si lo cambias, hay que volver a desplegar. |

## Base de datos gratuita (TiDB Cloud Starter)

Las historias, el Repositorio de HU y las lecciones aprendidas se guardan en una base MySQL compatible, así que **no se pierden** al reiniciar o redesplegar en Render y se comparten entre dispositivos.

1. Crea una cuenta en TiDB Cloud y un **Starter cluster** gratuito (elige una región cercana a la del servicio en Render).
2. En el cluster pulsa **Connect**, elige el conector **PyMySQL** y genera la contraseña. Copia los datos de conexión (host, puerto, usuario, contraseña y base).
3. Arma la URL así: `mysql+pymysql://USUARIO:CLAVE@HOST:4000/BASE` (si la clave tiene caracteres especiales como `@`, `/` o `:`, codifícalos, por ejemplo `@` → `%40`).
4. En Render, **Environment → Add Environment Variable**: `DATABASE_URL` con esa URL. Guarda; Render reinicia el servicio.
5. Verifica con `/api/analista/health` y crea una historia. Al entrar desde otro navegador o dispositivo debe aparecer la misma.

Notas:

- Las tablas se crean solas al iniciar; no hay que ejecutar scripts.
- **Identificadores:** cada registro tiene un `id` GUID aleatorio (llave primaria y relaciones entre tablas) y, aparte, un `codigo` legible para las personas: `HU-CODIGO-001` en las historias y `LEC-001` en las lecciones. El GUID nunca se usa como código.
- **Empezar de cero:** la base inicia vacía y la aplicación no trae historias de ejemplo. Si la base tiene tablas de una versión anterior (ids numéricos), el servicio no arranca y lo indica en los logs; en el SQL Editor de TiDB ejecuta y vuelve a desplegar:
  ```sql
  DROP TABLE IF EXISTS leccion, solicitud_cambio, hu_aprobada, historia;
  ```
- La conexión usa TLS y se recicla cada pocos minutos porque TiDB Cloud cierra las conexiones inactivas.
- El plan Starter tiene una cuota mensual gratuita; si se agota, la base deja de aceptar conexiones hasta el mes siguiente o hasta subir de plan.
- **Nunca** pegues la cadena de conexión en el chat, en el código ni en un commit: solo en el panel de Render. Si se expone, restablece la contraseña en TiDB Cloud.
- La base es la única fuente de verdad: lo que un navegador tenga guardado de versiones anteriores se reemplaza por lo que haya en la base.

## Plan gratuito (prueba) y paso a datos permanentes

Por defecto el Blueprint usa el plan `free`, sin tarjeta de crédito, para comprobar que todo arranca. Límites:

- **Sin disco persistente:** los archivos locales se borran en cada despliegue o reinicio; por eso los datos van a la base de datos externa (`DATABASE_URL`).
- **Se duerme sin uso:** tras unos 15 minutos sin visitas el servicio se detiene y la primera visita siguiente tarda aproximadamente un minuto en responder.
- **Memoria limitada (512 MB):** el servicio ejecuta el backend y OpenCode juntos. Si Render lo reinicia por falta de memoria (aparece en los logs), hay que pasar al plan `starter`.

Para usarlo en serio: en `render.yaml` cambie `plan: free` por `plan: starter`, descomente el bloque `disk` y una el cambio a `main`. Render pedirá tarjeta y desde entonces los archivos locales también se conservan entre despliegues.

## Importante

- **Seguridad:** quien entre al URL consume la cuota de tu plan de OpenCode. Por eso el acceso con clave es obligatorio y no se debe compartir el URL con la clave fuera del equipo. No uses datos personales reales en las historias.
- **Un solo servidor:** el servicio está pensado para una sola instancia (las conversaciones del agente viven en memoria). No lo escales a varias instancias.
- **Credenciales del modelo:** el contenedor escribe `OPENCODE_API_KEY` en el archivo de credenciales de OpenCode al arrancar. Si el endpoint `/api/analista/health` indica que el modelo no está disponible, revisa que la clave sea válida y el plan esté activo.
- **Rotación:** cambia `OPENCODE_API_KEY` y `ACCESO_CLAVE` desde el panel cuando alguien deje el equipo.
- **Datos compartidos:** las historias y el Repositorio de HU viven en la base de datos. El navegador solo conserva una copia local (caché) que se actualiza al abrir la aplicación y al volver a ella; sin conexión se puede leer, pero los cambios se envían cuando el servicio responde.
