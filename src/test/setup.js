import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Las pruebas corren sin seguridad (como el desarrollo local): la sesión responde que no está activa.
// Una prueba de seguridad puede reemplazar estas funciones con vi.mocked(sesionApi.leer).mockResolvedValue(...).
vi.mock('../services/seguridadApi.js', () => ({
  sesionApi: {
    leer: vi.fn(async () => ({ seguridad: false, usuario: null })),
    iniciar: vi.fn(),
    listarAprobador: vi.fn(async () => []),
  },
  mantenimientoApi: {
    listarAccion: vi.fn(async () => []),
    listarUsuario: vi.fn(async () => []),
    crearUsuario: vi.fn(),
    actualizarUsuario: vi.fn(),
    listarRol: vi.fn(async () => []),
    crearRol: vi.fn(),
    actualizarRol: vi.fn(),
    eliminarRol: vi.fn(),
  },
}));

// Pendientes: sin nada por decidir, salvo que una prueba diga otra cosa.
vi.mock('../services/pendientesApi.js', () => ({
  pendientesApi: {
    listar: vi.fn(async () => ({ por_decidir: [], avisos: [], total: 0 })),
    marcarLeido: vi.fn(async () => null),
  },
}));

afterEach(() => {
  cleanup();
});
