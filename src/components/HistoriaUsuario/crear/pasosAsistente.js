// Registro de los pasos del asistente para crear una historia: de aquí salen el indicador de pasos y la
// vista que se muestra. Agregar un paso = crear su componente y agregar una entrada (ver docs/arquitectura.md).
import { PASO } from './constantesAsistente';
import { PasoRequerimientoComponent } from './PasoRequerimientoComponent';
import { PasoAnalisisComponent } from './PasoAnalisisComponent';
import { PasoPreguntasComponent } from './PasoPreguntasComponent';
import { PasoHistoriaComponent } from './PasoHistoriaComponent';
import { PasoAprobacionComponent } from './PasoAprobacionComponent';

export const LISTA_PASO = Object.freeze([
  { id: PASO.REQUERIMIENTO, etiqueta: 'Requerimiento', Componente: PasoRequerimientoComponent },
  { id: PASO.ANALISIS, etiqueta: 'Análisis del agente', Componente: PasoAnalisisComponent },
  { id: PASO.PREGUNTAS, etiqueta: 'Preguntas a Negocio', Componente: PasoPreguntasComponent },
  { id: PASO.HISTORIA, etiqueta: 'Historia (borrador)', Componente: PasoHistoriaComponent },
  { id: PASO.APROBACION, etiqueta: 'Aprobación del PO', Componente: PasoAprobacionComponent },
]);

export const pasoPorId = (id) => LISTA_PASO.find((paso) => paso.id === id) ?? null;
