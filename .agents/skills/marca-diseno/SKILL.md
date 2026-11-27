---
name: marca-diseno
description: Úsala antes de cambiar o crear cualquier pantalla, estilo, color, fuente o componente visual del frontend de este repositorio. Define la marca «Ciruela corporativa» y lo que no se puede cambiar.
---

# Marca «Ciruela corporativa»

La guía completa es `docs/marca.md`. Léela antes de tocar la interfaz. Una tarea funcional **no cambia el diseño**: usa lo que ya existe. Cambiar la marca es una decisión del equipo.

## Lo que no se negocia
1. **Colores solo en `src/styles/_theme.scss`**, como variables CSS con su par para modo oscuro. En componentes y estilos se usan `var(--color-…)` o `$color-…`; nunca un hexadecimal (permitidos únicamente `#fff`, `#ffffff` y `#1a1a1a` como texto sobre un relleno). La prueba de estructura lo vigila.
2. **Roles del color:** ciruela (`--color-nav-bg`) para la navegación; morado (`--color-primary`) para la acción principal, lo activo y el foco; naranja (`--color-brand`) solo para el logotipo y lo que espera una decisión, nunca como texto ni fondo de botón; verde, ámbar y rojo solo para estados, siempre con texto.
3. **Una acción principal por pantalla** (`btn btn--primary`). El resto, `btn--secondary` o `btn--danger` con confirmación (`useConfirmacion`).
4. **Tipografía:** Inter para la interfaz e IBM Plex Mono para códigos (`HU-POL-014`). Sin serifas, sin pesos 700/800, sin otras fuentes. Mayúscula solo al inicio de la oración.
5. **Formas:** bordes de 1 px, sin sombras en tarjetas ni degradados. Radios 6 (controles), 8 (tarjetas), 12 (modales); insignias de radio 4.
6. **Responsivo sin código por pantalla:** la estructura (`.barra-lateral` en `src/styles/_layout.scss`) ya resuelve web (barra lateral), tablet (íconos) y móvil (barra superior e inferior). Una opción de menú nueva lleva `etiqueta` y `corta` (máximo 9 letras) en `src/config/rutas.jsx`. Objetivos táctiles de 44 px; campos de 16 px en móvil.
7. **Accesible:** contraste AA (4,5:1), foco visible, `aria-label` en botones de solo ícono, estados nunca solo por color.

## Dónde va cada cosa
- Color o token nuevo: `_theme.scss` (claro y oscuro) + documentarlo en `docs/marca.md`. Solo si el equipo lo pidió.
- Ajuste de un componente común: `src/styles/_marca.scss`.
- Estilos de una pantalla nueva: su `.scss` usando variables; reutiliza `src/components/Comun/`.

## Antes de terminar
- `npx vitest run`, `npx vite build` y `.venv/bin/python -m pytest -q agentes` (incluye las pruebas de la marca).
- Revisa la pantalla en 1280, 834 y 390 px de ancho y en modo oscuro.
