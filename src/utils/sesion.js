// Token de la sesión por usuario. Se guarda en este navegador y viaja en cada llamada a la API.
export const TOKEN_SESION_KEY = 'historias_sesion_token';
export const EVENTO_SESION_VENCIDA = 'historias-usuario:sesion-vencida';

export function leerToken() {
  try {
    return localStorage.getItem(TOKEN_SESION_KEY) || '';
  } catch (error) {
    console.error('No se pudo leer la sesión:', error);
    return '';
  }
}

export function guardarToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_SESION_KEY, token);
    else localStorage.removeItem(TOKEN_SESION_KEY);
  } catch (error) {
    console.error('No se pudo guardar la sesión:', error);
  }
}

export function encabezadoSesion() {
  const token = leerToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// La API respondió 401: la sesión venció o el usuario se desactivó. La interfaz vuelve a pedir el ingreso.
export function avisarSesionVencida(status) {
  if (status === 401 && leerToken()) window.dispatchEvent(new Event(EVENTO_SESION_VENCIDA));
}
