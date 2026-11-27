# Marca «Ciruela corporativa»

Guía de identidad visual de la aplicación. Es la fuente de verdad del diseño: cualquier persona o herramienta de IA que toque la interfaz la sigue. **Cambiar la marca es una decisión del equipo, no de una tarea**; una funcionalidad nueva usa lo que ya está aquí.

Bocetos de referencia (web, tablet, móvil y modo oscuro): lienzo «Bocetos de la marca Ciruela corporativa».

## Propósito

Una herramienta de trabajo que se pueda vender a empresas: seria, ordenada y confiable, con identidad propia. Cada regla tiene un porqué:

| Principio | Qué significa en la pantalla |
|---|---|
| El contenido manda | La navegación (ciruela) retrocede; el contenido va sobre superficies claras. |
| El color comunica | El color marca acciones, estados y lo que espera una decisión; nunca decora. |
| Una acción principal por pantalla | Solo un botón morado relleno por vista; el resto son secundarios. |
| Estructura que se siente, no se ve | Bordes finos de 1 px, sin sombras en tarjetas ni degradados. |
| Accesible por defecto | Contraste AA (4,5:1) en todo el texto, foco visible, objetivos táctiles de 44 px. |

## Colores

Los colores **solo** se definen en `src/styles/_theme.scss`, como variables CSS para modo claro y oscuro. Los componentes usan las variables (`var(--color-…)` o `$color-…` de `_variables.scss`); nunca escriben un hexadecimal. Una prueba de estructura lo verifica.

| Rol | Variable | Claro | Oscuro | Uso |
|---|---|---|---|---|
| Fondo de página | `--color-bg` | `#F6F7F9` | `#0F0D14` | Detrás de todo el contenido. |
| Superficie | `--color-surface` | `#FFFFFF` | `#17141E` | Tarjetas, tablas, formularios. |
| Superficie alterna | `--color-surface-alt` | `#FAFAFB` | `#1B1722` | Encabezados de tabla, zonas secundarias. |
| Texto principal | `--color-text-primary` | `#111827` | `#ECEAF0` | Títulos y texto. |
| Texto secundario | `--color-text-secondary` | `#4B5563` | `#B9B3C4` | Descripciones. |
| Texto tenue | `--color-text-muted` | `#6B7280` | `#9A94A6` | Fechas, ayudas, metadatos. |
| Borde | `--color-border` | `#E5E7EB` | `#2A2533` | Divisores y contornos de 1 px. |
| Borde de campo | `--color-border-dark` | `#9CA3AF` | `#5A5366` | Contorno de campos (3:1). |
| **Morado (primario)** | `--color-primary` | `#6F3FA0` | `#7C4DB3` | Acción principal, elemento activo, foco. |
| Texto morado | `--color-primary-text` | `#6F3FA0` | `#C4A6EA` | Enlaces y texto de acento. |
| **Ciruela (navegación)** | `--color-nav-bg` | `#1E1530` | `#0B0910` | Barra lateral, barra superior móvil, botón de ayuda. |
| **Naranja (marca)** | `--color-brand` | `#F36C21` | `#F36C21` | Logotipo e indicador de lo que espera una decisión. |
| Éxito | `--color-success-*` | `#1F6B33` | `#9FD9A6` | Aprobada, atendido. |
| Advertencia | `--color-warning-*` | `#9A4A0B` | `#F6C177` | Espera a Negocio, dependencias. |
| Peligro | `--color-danger-*` | `#B42318` | `#FF8A82` | Rechazada, eliminar, errores. |

Reglas:
- El **naranja nunca es texto** sobre fondo claro (contraste 3:1) ni fondo de botones; solo el logotipo, el punto de «espera su decisión» y la marca del elemento activo del menú.
- El **morado** relleno es solo para la acción principal. Los demás botones son secundarios (superficie con borde).
- Los **estados** se muestran con su color de significado en una insignia (fondo claro + texto oscuro del mismo tono), nunca solo con color: siempre llevan texto.
- Blanco (`#FFFFFF`) y casi negro (`#1A1A1A`) solo como texto sobre un relleno de color.

## Tipografía

Dos familias, cargadas desde Google Fonts en `index.html` y definidas en `_variables.scss`:

- **Inter** (400, 500 y 600) para toda la interfaz. Es la base de la tipografía de sistemas empresariales como el de Atlassian: neutra, legible y profesional.
- **IBM Plex Mono** (400 y 500) para códigos y valores técnicos: `HU-POL-014`, `LEC-003`, fechas en tablas.

No se usan serifas ni pesos 700 u 800: la jerarquía sale del tamaño y del peso 600.

| Nivel | Tamaño | Peso | Uso |
|---|---|---|---|
| Título de página | 26 px (1,625 rem) | 600, tracking −0,02 em | Un `h1` por pantalla. |
| Título de sección | 17–18 px | 600 | Encabezados de tarjeta y de paso. |
| Subtítulo | 15 px | 600 | Encabezados de bloque. |
| Texto | 14–16 px | 400 | Contenido y campos (16 px en móvil para evitar el zoom de iOS). |
| Etiqueta | 13 px | 500 | Etiquetas de campos, pestañas. |
| Metadato | 12 px | 400–500 | Fechas, insignias, ayudas. |
| Código | 12–13 px | 400 | IBM Plex Mono. |

Mayúsculas solo al inicio de la oración («Nueva historia», no «Nueva Historia»).

## Fondos, espaciado y formas

- Página en `--color-bg`; contenido en tarjetas de `--color-surface` con borde de 1 px.
- Radios: 6 px en controles (botones, campos, insignias de 4 px), 8 px en tarjetas, 12 px en ventanas modales.
- Espaciado en múltiplos de 4: 8, 12, 16, 24 y 32 px. Margen de página de 40 px en web, 24 en tablet y 16 en móvil.
- Sombras solo en elementos flotantes (modales, menús, botón de ayuda).
- Íconos de `lucide-react`, de 16 a 20 px, con trazo; acompañan al texto, no lo reemplazan (salvo en tablet y móvil, donde tienen nombre accesible).

## Componentes

| Componente | Regla |
|---|---|
| Botón principal | `btn btn--primary`: morado relleno, texto blanco, 40 px de alto (44 en táctil). Uno por pantalla. |
| Botón secundario | `btn btn--secondary`: superficie con borde. |
| Botón de peligro | `btn btn--danger`: solo para eliminar o rechazar, siempre con confirmación (`useConfirmacion`). |
| Campos | `input`, `select`, `textarea` de 40 px, borde `--color-border-dark`, etiqueta de 13 px arriba. |
| Insignias de estado | `badge badge--<estado>`: radio 4, 12 px, peso 500. |
| Tablas | Encabezado en `--color-surface-alt` con texto tenue de 12 px; filas con divisor de 1 px; números tabulares. |
| Avisos | `AlertaComponent` con el color del significado. |
| Modales | `ConfirmacionComponent` (nunca `window.confirm`). |

## Web, tablet y móvil

La estructura está en `src/styles/_layout.scss` (`.barra-lateral`) y se adapta sola; las pantallas no hacen nada especial.

| Tamaño | Navegación | Contenido |
|---|---|---|
| **Web** (más de 1024 px) | Barra lateral ciruela de 232 px con logotipo, menú con texto y, abajo, la persona y el cambio de tema. | Hasta 1200 px de ancho, margen de 40 px. |
| **Tablet** (641–1024 px) | Barra de 72 px solo con íconos; cada enlace conserva su nombre accesible y su texto emergente. | Margen de 24 px; las grillas pasan a dos columnas. |
| **Móvil** (hasta 640 px) | Barra superior ciruela con el logotipo y la sesión; el menú pasa a una barra inferior fija con íconos y una etiqueta corta (`menu.corta` en `rutas.jsx`). | Una columna, margen de 16 px; los botones de ayuda flotan sobre la barra inferior. |

Una opción de menú nueva necesita `etiqueta` y `corta` (máximo 9 letras) en `src/config/rutas.jsx`.

## Modo claro y oscuro

El tema lo elige la persona (botón de luna o sol en la barra) y se guarda en el navegador. Todos los colores tienen su par oscuro en `_theme.scss`; en oscuro, el morado y los estados se aclaran para mantener el contraste AA. No hay estilos propios del modo oscuro en los componentes.

## Tono de los textos

Lenguaje de negocio, directo y en segunda persona formal («Revise», «Su decisión»). Verbos en los botones («Nueva historia», «Enviar respuestas», «Confirmar decisión»). Sin detalle técnico para la persona usuaria.

## Cómo hacer un cambio sin romper la marca

- **Pantalla nueva:** use los componentes de `src/components/Comun/` y las clases existentes. No agregue colores ni fuentes.
- **Necesito un color nuevo:** no se agrega en el componente. Si de verdad hace falta (por ejemplo, un estado nuevo), se agrega como variable en `_theme.scss`, con su par oscuro y su contraste verificado, y se documenta en esta guía.
- **Ajuste de estilo de un componente común:** va en `src/styles/_marca.scss` (se carga después del resto).
- Antes de terminar: `npx vitest run`, `npx vite build` y `pytest` (incluye las pruebas de estructura que vigilan la marca).
