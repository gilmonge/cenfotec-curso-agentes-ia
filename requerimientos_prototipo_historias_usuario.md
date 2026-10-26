# Prototipo — Asistente IA para Historias de Usuario

## 1. Objetivo

Construir una **prueba de concepto web** para representar el flujo de creación, análisis, generación y revisión de Historias de Usuario.

El objetivo es demostrar la experiencia visual del sistema, no desarrollar una solución productiva.

---

## 2. Alcance

El prototipo debe permitir visualizar y navegar por:

- Dashboard.
- Listado de Historias de Usuario.
- Creación de una nueva Historia de Usuario.
- Flujo paso a paso para creación.
- Análisis simulado del requerimiento.
- Preguntas de aclaración.
- Generación simulada de Historia de Usuario.
- Revisión final.
- Edición mediante secciones colapsables.

No se requiere backend, base de datos ni integraciones reales.

---

## 3. Requerimientos técnicos

- Proyecto web.
- React.
- JavaScript.
- No usar TypeScript.
- SCSS para estilos.
- React Router para navegación.
- Se permite `localStorage` para simular persistencia.
- No usar Redux ni gestores de estado complejos.
- No usar frameworks UI externos.
- No usar Bootstrap.
- No usar Material UI.
- No usar Tailwind CSS.
- No implementar pruebas automatizadas.

---

## 4. Diseño

El diseño debe ser:

- Responsive.
- Limpio.
- Minimalista.
- Corporativo.
- Con paleta de colores neutra.
- Con fondo claro.
- Con tarjetas blancas.
- Con bordes sutiles.
- Con buena separación visual entre secciones.
- Consistente entre todas las pantallas.

Usar componentes reutilizables.

### Responsive

Considerar:

- Desktop.
- Tablet.
- Mobile.

En dispositivos móviles, las columnas deben reorganizarse en una sola columna.

---

## 5. Navegación principal

La aplicación tendrá las siguientes opciones:

- Dashboard.
- Historias de Usuario.
- Nueva Historia.
- Ayuda.

---

## 6. Dashboard

Debe mostrar:

### Tarjeta 1 — Historias de Usuario

Mostrar:

- Cantidad total de historias.
- Botón o enlace para ver historias.

Ejemplo:

**12 Historias creadas**

### Tarjeta 2 — Nueva Historia de Usuario

Mostrar:

- Texto breve indicando que se puede crear una nueva historia.
- Botón para iniciar el proceso.

No incluir gráficos ni métricas complejas.

---

## 7. Pantalla de Historias de Usuario

Mostrar una lista sencilla de historias simuladas.

Cada historia debe incluir:

- Título.
- Tipo.
- Fecha.
- Estado.

Estados posibles:

- Borrador.
- En análisis.
- Pendiente de información.
- Generada.
- Revisada.

Acciones:

- Ver.
- Editar.

Los datos pueden venir de un archivo mock o de `localStorage`.

---

## 8. Creación de Historia de Usuario

La creación debe utilizar un flujo tipo **Stepper**.

Pasos:

1. Requerimiento.
2. Análisis.
3. Preguntas.
4. Historia de Usuario.
5. Revisión.

---

## 9. Paso 1 — Requerimiento

Campos:

- Nombre del requerimiento.
- Tipo de información.
- Descripción o información de negocio.

Tipos de información:

- Descripción libre.
- Minuta.
- Notas de conversación.
- Otro.

Incluir un botón:

**Analizar requerimiento**

No se requiere análisis real. El botón puede avanzar al siguiente paso mostrando información simulada.

---

## 10. Paso 2 — Análisis

Mostrar información simulada dividida en:

### Datos conocidos

Ejemplo:

- Existe una póliza activa.
- La solicitud corresponde a una modificación.

### Información faltante

Ejemplo:

- No se especifica la fecha de vigencia.
- No se indica quién puede realizar el cambio.

### Supuestos

Ejemplo:

- Se asume que la modificación se realiza sobre una póliza activa.

### Ambigüedades

Ejemplo:

- No está definido si el cambio aplica sobre pólizas ya emitidas.

Mostrar pequeños indicadores con cantidades.

Ejemplo:

- 4 conocidos.
- 2 faltantes.
- 1 supuesto.
- 1 ambigüedad.

---

## 11. Paso 3 — Preguntas de aclaración

Mostrar preguntas simuladas para Negocio.

Cada pregunta debe incluir:

- Categoría.
- Pregunta.
- Campo de respuesta.
- Estado.

Categorías:

- Reglas de negocio.
- Datos requeridos.
- Validaciones.
- Excepciones.
- Comportamiento esperado.

Estados:

- Pendiente.
- Respondida.

Incluir botón:

**Generar Historia de Usuario**

---

## 12. Paso 4 — Historia de Usuario

Mostrar una Historia de Usuario generada de forma simulada.

Formato:

### Como

Usuario del sistema.

### Quiero

Modificar una cobertura asociada a una póliza.

### Para

Mantener actualizada la información contractual.

---

## 13. Criterios de aceptación

Mostrar criterios simulados.

Ejemplo:

1. El sistema debe validar que la póliza exista.
2. El sistema debe verificar que la cobertura pueda modificarse.
3. El cambio debe conservar el historial de modificaciones.

Opcionalmente mostrar un selector visual:

- Lista.
- Dado / Cuando / Entonces.

No es necesario realizar una conversión real.

---

## 14. Preguntas pendientes

Si existen puntos sin resolver, mostrarlos en una sección independiente.

Ejemplo:

- ¿Cuándo entra en vigencia la modificación?
- ¿Debe notificarse al asegurado?

---

## 15. Paso 5 — Revisión

Mostrar un resumen final con:

- Historia propuesta.
- Criterios de aceptación.
- Preguntas pendientes.
- Observaciones.

Ejemplo de resumen:

- Historia completa.
- Criterios generados.
- 2 puntos pendientes.

Botón:

**Guardar Historia**

El guardado puede simularse con `localStorage`.

---

## 16. Editar Historia de Usuario

La edición no debe utilizar Stepper.

Utilizar un componente tipo **Accordion / Collapse**.

Secciones:

- Requerimiento inicial.
- Análisis.
- Preguntas para Negocio.
- Historia de Usuario.
- Criterios de aceptación.
- Observaciones.

Cada sección debe poder abrirse y cerrarse independientemente.

---

## 17. Componentes reutilizables

Crear componentes básicos como:

- Button.
- Card.
- Input.
- Textarea.
- Select.
- Badge.
- Alert.
- Header.
- PageTitle.
- Stepper.
- Accordion.
- StatusBadge.
- MetricCard.
- UserStoryCard.
- QuestionCard.
- AnalysisCard.
- EmptyState.

---

## 18. Datos simulados

Crear datos mock para al menos 4 historias de usuario.

Ejemplo:

```js
{
  id: 1,
  title: "Modificación de cobertura",
  status: "reviewed",
  type: "Cambio",
  createdAt: "2026-09-23"
}
```

Los datos pueden almacenarse temporalmente en:

```text
localStorage
```

---

## 19. Inteligencia Artificial

Para esta prueba de concepto **no se requiere una integración real con IA**.

Simular comportamientos como:

- Analizando requerimiento...
- Análisis completado.
- Generando Historia de Usuario...
- Historia generada.

Puede utilizarse un pequeño retraso visual para simular procesamiento.

No utilizar API keys ni servicios externos en esta primera versión.

---

## 20. Estructura sugerida

```text
src/
├── assets/
├── components/
├── data/
├── layouts/
├── pages/
├── styles/
├── utils/
├── App.jsx
└── main.jsx
```

---

## 21. Rutas sugeridas

```text
/
/historias
/historias/nueva
/historias/:id
/historias/:id/editar
/ayuda
```

---

## 22. Flujo principal

```text
Dashboard
   ↓
Nueva Historia
   ↓
Requerimiento
   ↓
Análisis
   ↓
Preguntas
   ↓
Historia de Usuario
   ↓
Revisión
   ↓
Historias
```

Para edición:

```text
Historias
   ↓
Editar
   ↓
Accordion con secciones
```

---

## 23. Fuera de alcance

No implementar:

- Login.
- Registro.
- Roles.
- Administración de usuarios.
- Backend.
- API REST propia.
- Base de datos.
- Integración con Jira.
- Integración con Azure DevOps.
- Integración con iTop.
- Correos.
- Repositorios.
- Subida real de archivos.
- Exportación PDF.
- Historial de versiones.
- Auditoría.
- Notificaciones.
- Inteligencia Artificial real.
- Pruebas automatizadas.

---

## 24. Criterio de finalización

El prototipo se considera terminado cuando:

- Se ejecuta localmente.
- Está desarrollado con React y JavaScript.
- Utiliza SCSS.
- Es responsive.
- Tiene Dashboard.
- Tiene listado de Historias.
- Tiene flujo de creación con Stepper.
- Tiene pantalla de análisis.
- Tiene preguntas de aclaración.
- Tiene Historia de Usuario simulada.
- Tiene criterios de aceptación.
- Tiene revisión final.
- Tiene edición mediante Accordion.
- Usa datos mock o `localStorage`.
- Mantiene una interfaz visual consistente.
- No depende de backend ni servicios externos.

---

## 25. Prioridad

La prioridad es desarrollar rápidamente una interfaz navegable y visualmente consistente.

No profundizar en arquitectura, validaciones, seguridad, integraciones ni funcionalidades productivas.

La prueba de concepto debe enfocarse únicamente en demostrar el flujo principal de uso.
