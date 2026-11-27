import { request } from './analystApi.js';

// Inicio de sesión por usuario y Mantenimiento (usuarios con sus roles, roles con sus acciones).
export const sesionApi = Object.freeze({
  leer: ({ signal } = {}) => request('/sesion', { signal }),
  iniciar: (usuario, clave) => request('/sesion', { method: 'POST', body: { usuario, clave } }),
  listarAprobador: ({ signal } = {}) => request('/sesion/aprobadores', { signal }),
});

export const mantenimientoApi = Object.freeze({
  listarAccion: ({ signal } = {}) => request('/mantenimiento/acciones', { signal }),
  listarUsuario: (busqueda = '', { signal } = {}) => request(
    `/mantenimiento/usuarios${busqueda ? `?busqueda=${encodeURIComponent(busqueda)}` : ''}`, { signal },
  ),
  crearUsuario: (datos) => request('/mantenimiento/usuarios', { method: 'POST', body: datos }),
  actualizarUsuario: (id, datos) => request(`/mantenimiento/usuarios/${encodeURIComponent(id)}`, { method: 'PUT', body: datos }),
  listarRol: ({ signal } = {}) => request('/mantenimiento/roles', { signal }),
  crearRol: (datos) => request('/mantenimiento/roles', { method: 'POST', body: datos }),
  actualizarRol: (id, datos) => request(`/mantenimiento/roles/${encodeURIComponent(id)}`, { method: 'PUT', body: datos }),
  eliminarRol: (id) => request(`/mantenimiento/roles/${encodeURIComponent(id)}`, { method: 'DELETE' }),
});
