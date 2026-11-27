---
name: agregar-ruta
description: Úsala cuando haya que agregar una pantalla, una ruta o una opción de menú al frontend React de este repositorio de historias de usuario.
---

# Agregar una pantalla o una opción de menú

Las rutas y el menú salen de un solo registro: `src/config/rutas.jsx`. No agregues `<Route>` en `App.jsx` ni enlaces en `EnvolturaPaginaComponent.jsx`.

## Pasos
1. Crea el componente en `src/components/<Funcionalidad>/<Nombre>Component.jsx`.
   - Lógica sin React en `src/utils/` (con pruebas), llamadas al backend en `src/services/`, estado reutilizable en `src/hooks/`.
   - Componentes comunes (botones, alertas, tarjetas, áreas de texto) en `src/components/Comun/`: reutilízalos.
2. Agrega una entrada en `listaRuta` de `src/config/rutas.jsx`:
   ```js
   { ruta: 'reportes', componente: ReporteComponent,
     menu: { etiqueta: 'Reportes', titulo: 'Ver reportes', icono: BarChart3, orden: 40 } },
   ```
   - Sin `menu` la pantalla existe pero no aparece en el menú (por ejemplo, un detalle `historias/:id`).
   - `orden` en decenas y único; `exacta: true` si la ruta no debe marcarse activa en sus subrutas.
   - Íconos de `lucide-react`.
   - Si solo deben verla algunos roles, agrega `accion: ACCION.X` (de `src/config/acciones.js`). Si la acción no existe, agrégala en `agentes/seguridad/catalogo.py` (con su nombre legible) y en `src/config/acciones.js`; las rutas de la API que use la pantalla declaran `requiere_accion(ACCION.X)`. No hace falta tocar Mantenimiento.
3. Si la pantalla es nueva para la persona usuaria, descríbela en la Ayuda (`src/data/ayudaDocumentacion.js`).
4. Prueba con Testing Library (mira `src/components/EnvolturaPagina/__tests__/`) y ejecuta `npx vitest run` y `npx vite build`.

## Pasos del asistente para crear una historia
El asistente está en `src/components/HistoriaUsuario/crear/` y separa controlador y vistas:
- La lógica (estado, efectos, llamadas al flujo) va en `useCrearHistoria.js`; lo que una vista necesite se agrega al objeto que devuelve.
- Cada paso es una vista `Paso<Nombre>Component.jsx` que lee el controlador con `useAsistenteHistoria()` y no guarda estado del flujo.
- Para agregar un paso: su valor en `PASO` (`constantesAsistente.js`), su vista y su entrada en `LISTA_PASO` (`pasosAsistente.js`). El indicador de pasos sale de ese registro.
- `CrearHistoriaUsuarioComponent.jsx` solo arma la página (avisos, indicador y paso activo): no agregues lógica ahí.

## Convenciones
- Componentes terminan en `Component`; servicios en `Service`.
- Nombres en español y en singular para variables (`listaHistoria`).
- Sin `catch` vacío: al menos `console.warn` con el motivo.
- Textos para la persona usuaria en lenguaje de negocio, sin detalle técnico.
