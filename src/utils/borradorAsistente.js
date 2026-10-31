// Borrador automático del asistente "Nueva Historia": guarda el avance en este navegador para
// no perderlo si se cae la conexión, se recarga la página o se cierra la pestaña.
// No reemplaza a la base de datos: es solo el avance de una historia que aún no se ha guardado.
const CLAVE_BORRADOR = 'historias_borrador_nueva';
const VERSION_BORRADOR = 1;

export const leerBorrador = () => {
  try {
    const texto = localStorage.getItem(CLAVE_BORRADOR);
    if (!texto) return null;
    const dato = JSON.parse(texto);
    return dato?.version === VERSION_BORRADOR && dato.estado ? dato.estado : null;
  } catch (error) {
    console.error('No se pudo leer el borrador del asistente:', error);
    return null;
  }
};

export const guardarBorrador = (estado) => {
  try {
    localStorage.setItem(CLAVE_BORRADOR, JSON.stringify({ version: VERSION_BORRADOR, guardadoEn: new Date().toISOString(), estado }));
  } catch (error) {
    console.error('No se pudo guardar el borrador del asistente:', error);
  }
};

export const borrarBorrador = () => {
  try {
    localStorage.removeItem(CLAVE_BORRADOR);
  } catch (error) {
    console.error('No se pudo borrar el borrador del asistente:', error);
  }
};

// Un borrador vale la pena guardarlo solo si la persona ya escribió algo.
export const borradorTieneContenido = (estado) =>
  Boolean(String(estado?.requirementName ?? '').trim() || String(estado?.description ?? '').trim());
