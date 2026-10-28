# Evidencia de Markdown seguro

Fecha: 2026-10-27

Vitest ejecutó diez cargas de prueba sintéticas sobre `AnalystMarkdown`:

1. Etiqueta `<script>`.
2. Imagen HTML con `onerror`.
3. SVG con `onload`.
4. Iframe con URL `javascript:`.
5. Enlace `javascript:`.
6. Enlace `data:`.
7. Enlace `blob:`.
8. Enlace `file:`.
9. Protocolo `JaVaScRiPt:` con mayúsculas mezcladas.
10. Imagen remota Markdown.

**Resultado:** 10/10 quedaron inertes: no se renderizaron scripts, iframes, SVG, imágenes, atributos de evento ni enlaces con protocolos activos. GFM y enlaces HTTP/HTTPS se conservan; los enlaces externos usan `noopener noreferrer`. Prueba automatizada: `src/components/analyst-chat/__tests__/AnalystChat.test.jsx`. No se afirma una evaluación manual en navegador ni una prueba de penetración general.
