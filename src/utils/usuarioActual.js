// Nombre de la persona que usa la aplicación. No hay inicio de sesión por persona (el acceso al
// servicio es una clave compartida), así que cada quien escribe su nombre una vez y se recuerda
// en su navegador. Se usa para registrar quién creó y quién modificó cada historia.

export const NOMBRE_USUARIO_KEY = 'historias_usuario_nombre';
export const EVENTO_USUARIO = 'historias-usuario:usuario-cambiado';
export const SIN_IDENTIFICAR = 'Sin identificar';
const LARGO_MAXIMO = 60;

export function normalizarNombre(nombre) {
  return String(nombre ?? '').replace(/\s+/g, ' ').trim().slice(0, LARGO_MAXIMO);
}

export function leerNombreUsuario() {
  try {
    return normalizarNombre(localStorage.getItem(NOMBRE_USUARIO_KEY));
  } catch (error) {
    console.error('No se pudo leer el nombre del usuario:', error);
    return '';
  }
}

export function guardarNombreUsuario(nombre) {
  const limpio = normalizarNombre(nombre);
  try {
    if (limpio) localStorage.setItem(NOMBRE_USUARIO_KEY, limpio);
    else localStorage.removeItem(NOMBRE_USUARIO_KEY);
  } catch (error) {
    console.error('No se pudo guardar el nombre del usuario:', error);
  }
  window.dispatchEvent(new Event(EVENTO_USUARIO));
  return limpio;
}

export function autorDe(historia, campo = 'updatedBy') {
  return normalizarNombre(historia?.[campo]) || normalizarNombre(historia?.createdBy) || SIN_IDENTIFICAR;
}
