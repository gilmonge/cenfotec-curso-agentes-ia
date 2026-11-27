import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { App } from '../../../App';
import { sesionApi } from '../../../services/seguridadApi';
import { listaOpcionMenu } from '../../../config/rutas';
import { opcionesPermitidas, OPCION_PO } from '../../../flujo/interrupciones';
import { ACCION } from '../../../config/acciones';
import { TOKEN_SESION_KEY } from '../../../utils/sesion';

const PO = {
  id: 'u-po', usuario: 'ana', nombre: 'Ana Mora', activo: true, roles: [{ id: 'r', nombre: 'Product Owner' }],
  acciones: [ACCION.HISTORIA_VER, ACCION.HISTORIA_APROBAR, ACCION.HISTORIA_DEVOLVER],
};

describe('sesión por usuario', () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.pushState({}, '', '/');
  });

  it('con seguridad activa pide ingresar y luego muestra solo el menú permitido', async () => {
    vi.mocked(sesionApi.leer).mockResolvedValueOnce({ seguridad: true, usuario: null });
    vi.mocked(sesionApi.iniciar).mockResolvedValueOnce({ seguridad: true, usuario: PO, token: 'tok' });
    const user = userEvent.setup();
    render(<App />);
    await user.type(await screen.findByLabelText('Usuario'), 'ana');
    await user.type(screen.getByLabelText('Contraseña'), 'clave-segura');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    await waitFor(() => expect(screen.getByRole('button', { name: /Ana Mora. Cerrar sesión/ })).toBeInTheDocument());
    expect(sesionApi.iniciar).toHaveBeenCalledWith('ana', 'clave-segura');
    expect(localStorage.getItem(TOKEN_SESION_KEY)).toBe('tok');
    expect(screen.getByRole('link', { name: /^Historias de usuario$/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Nueva historia/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Mantenimiento/ })).not.toBeInTheDocument();
  });

  it('el menú y las decisiones del PO se filtran por acción', () => {
    const puede = (accion) => (Array.isArray(accion) ? accion : [accion]).some((codigo) => !codigo || PO.acciones.includes(codigo));
    expect(listaOpcionMenu(puede).map((opcion) => opcion.etiqueta)).toEqual(['Inicio', 'Pendientes', 'Historias de usuario', 'Ayuda']);
    expect(opcionesPermitidas(OPCION_PO, puede).map(([valor]) => valor)).toEqual([
      'aprobar', 'devolver_analista', 'devolver_redactor', 'devolver_asesor',
    ]);
  });
});
