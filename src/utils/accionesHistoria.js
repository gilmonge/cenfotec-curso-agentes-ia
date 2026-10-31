// Qué acciones tiene cada HU según su estado. Un solo lugar para el listado y el detalle.
export const ACCION = Object.freeze({
  VER: 'ver',
  EDITAR: 'editar',
  SOLICITAR_CAMBIO: 'solicitar-cambio',
  DESCARGAR: 'descargar',
  ELIMINAR: 'eliminar',
});

export function accionesDisponibles(story = {}, { omitir = [] } = {}) {
  const acciones = [ACCION.VER, ACCION.EDITAR];
  // Solo una HU aprobada pasa por Solicitar cambio: antes de aprobarse se edita directamente.
  if (story.status === 'aprobada') acciones.push(ACCION.SOLICITAR_CAMBIO);
  acciones.push(ACCION.DESCARGAR, ACCION.ELIMINAR);
  return acciones.filter((accion) => !omitir.includes(accion));
}
