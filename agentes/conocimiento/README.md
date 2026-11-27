# Paquete de conocimiento

La recuperación y la ingesta de la feature 003 son experimentales en la rama `feat/sistema-multiagente-rag`. Este documento describe la configuración del backend; no significa que se haya ejecutado una ingesta remota.

## Índice y namespaces

La configuración vigente define el índice Pinecone denso convencional `historias-usuario`, serverless en AWS `us-east-1`, con dimensión `1024`, métrica `cosine` y embeddings generados por `PineconeEmbeddings(model="multilingual-e5-large")`. `PineconeVectorStore` realiza consultas y upserts. No se usa document index ni embedding integrado.

Los únicos namespaces permitidos son:

- `glosario`
- `estandares`
- `checklist`
- `hu_aprobadas`
- `lecciones`
- `codigo`

El backend valida namespace, rol, tipo de fuente y referencias. Las herramientas de recuperación son read-only; la escritura de vectores solo ocurre en la CLI explícita de ingesta.

## Preparación e ingesta

Desde la raíz del repositorio, prepara y valida todas las fuentes localmente, sin llamadas remotas:

```powershell
python -m agentes.conocimiento.ingesta --fuente todas --dry-run
```

Activa el entorno `.venv` del proyecto antes de usar `python`, o reemplázalo por `& .\agentes\analista\.venv\Scripts\python.exe`. El modo dry-run no construye el cliente Pinecone ni hace upserts. Como `--fuente todas` también lee RepositorioHU, si `DATABASE_URL` está definida puede consultar TiDB; para garantizar que no haya llamadas de red, quita esa variable y usa el SQLite local. Si la base SQLite no existe, la lectura puede crear un archivo vacío; si falta una fuente o su esquema local, el CLI devuelve `partial_failure` con el código de error sanitizado.

Cuando se decida ejecutar la ingesta real, usa:

```powershell
python -m agentes.conocimiento.ingesta --fuente todas
```

Si el índice no existe, agrega `--crear-indice` para crearlo si falta y validarlo si ya existe:

```powershell
python -m agentes.conocimiento.ingesta --fuente todas --crear-indice
```

La opción `--crear-indice` solo es pertinente para ingesta real y requiere que la clave esté disponible en el entorno. La ingesta real y la creación de un índice no se ejecutaron como parte de T051/T052.

## Procedencia y fallback

Cada fuente informa su `backend` real. `status=degraded` indica que Pinecone falló o no se configuró y que se aplicó el fallback local. `backend=local` significa que el resultado vino de las fuentes locales; `backend=none` significa que no hubo resultados locales disponibles. Esos estados no representan una búsqueda de Pinecone. `backend=pinecone` solo se informa para resultados devueltos por el cliente Pinecone.

## Secretos

`PINECONE_API_KEY` se lee desde el entorno del backend. Configúrala fuera del repositorio; no incluyas claves reales ni valores secretos en `.env.example`, documentación, fuentes ficticias o logs. En Render, `PINECONE_API_KEY` usa `sync: false` y se completa en el panel privado del servicio. Nunca expongas esa variable al frontend.
