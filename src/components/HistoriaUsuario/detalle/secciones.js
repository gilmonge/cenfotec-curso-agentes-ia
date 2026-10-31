import { leerBitacora } from '../../../utils/bitacora';

// Qué secciones tiene el detalle de una HU y cuáles se muestran para una HU concreta.
// Es lógica pura (sin React) para poder probar las reglas de visibilidad por separado.
export const SECCION_INICIAL = 'historia';

const tienePlantilla = (story) => Boolean(story.system || story.codigoHu || story.area || story.benefits?.length > 0);

const DEFINICION = [
  { id: 'historia', titulo: 'Historia', visible: () => true },
  {
    id: 'criterios',
    titulo: 'Criterios de aceptación',
    visible: () => true,
    contador: (story) => story.acceptanceCriteria?.length ?? 0,
  },
  {
    id: 'preguntas',
    titulo: 'Preguntas pendientes',
    visible: (story) => (story.pendingQuestions?.length ?? 0) > 0,
    contador: (story) => story.pendingQuestions?.length ?? 0,
  },
  { id: 'observaciones', titulo: 'Observaciones y aclaraciones', visible: (story) => leerBitacora(story).length > 0 },
  {
    id: 'revisiones',
    titulo: 'Historial',
    visible: (story) => (story.revisiones?.length ?? 0) + (story.ediciones?.length ?? 0) > 0,
    contador: (story) => (story.revisiones?.length ?? 0) + (story.ediciones?.length ?? 0),
  },
  { id: 'analisis', titulo: 'Análisis del requerimiento', visible: (story) => Boolean(story.analysis) },
  { id: 'plantilla', titulo: 'Datos de la plantilla', visible: tienePlantilla },
];

export function construirSecciones(story) {
  return DEFINICION.filter((seccion) => seccion.visible(story)).map(({ id, titulo, contador }) => ({
    id,
    titulo,
    contador: contador ? contador(story) : null,
  }));
}

// Si la sección pedida no existe para esta HU, se vuelve a la primera.
export const seccionActiva = (secciones, pedida) => (
  secciones.find((seccion) => seccion.id === pedida)?.id ?? secciones[0].id
);
