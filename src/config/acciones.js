// Códigos de las acciones, iguales a los del catálogo del backend (agentes/seguridad/catalogo.py).
// El nombre que lee la persona lo trae el backend; aquí solo se usa el código para mostrar u ocultar
// pantallas y botones. Una prueba de estructura revisa que esta lista y la del backend sean la misma.
export const ACCION = Object.freeze({
  HISTORIA_VER: 'historia.ver',
  HISTORIA_CREAR: 'historia.crear',
  HISTORIA_RESPONDER_NEGOCIO: 'historia.responder_negocio',
  HISTORIA_EDITAR: 'historia.editar',
  HISTORIA_APROBAR: 'historia.aprobar',
  HISTORIA_DEVOLVER: 'historia.devolver',
  HISTORIA_RECHAZAR: 'historia.rechazar',
  HISTORIA_ELIMINAR: 'historia.eliminar',
  HISTORIA_DESCARTAR_EN_PROCESO: 'historia.descartar_en_proceso',
  CAMBIO_SOLICITAR: 'cambio.solicitar',
  CAMBIO_DECIDIR: 'cambio.decidir',
  LECCION_VER: 'leccion.ver',
  LECCION_DECIDIR: 'leccion.decidir',
  MANTENIMIENTO_VER: 'mantenimiento.ver',
  USUARIO_ADMINISTRAR: 'usuario.administrar',
  ROL_ADMINISTRAR: 'rol.administrar',
});
