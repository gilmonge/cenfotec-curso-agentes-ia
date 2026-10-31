import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AccionesHistoriaComponent } from '../AccionesHistoriaComponent';
import { descargarPdf } from '../../../utils/exportarPdf';
import { descargarWord } from '../../../utils/exportarWord';

vi.mock('../../../utils/exportarPdf', () => ({ descargarPdf: vi.fn().mockResolvedValue(undefined) }));
vi.mock('../../../utils/exportarWord', () => ({ descargarWord: vi.fn().mockResolvedValue(undefined) }));

const manejadores = () => ({ onVer: vi.fn(), onEditar: vi.fn(), onSolicitarCambio: vi.fn(), onEliminar: vi.fn() });

describe('acciones de una HU (íconos)', () => {
  afterEach(() => { cleanup(); vi.clearAllMocks(); });

  it('cada ícono tiene nombre accesible y descripción emergente', () => {
    render(<AccionesHistoriaComponent story={{ id: 'a', status: 'aprobada', number: 'HU-1' }} {...manejadores()} />);
    ['Ver', 'Editar', 'Solicitar cambio', 'Descargar'].forEach((nombre) => {
      expect(screen.getByRole('button', { name: nombre })).toHaveAttribute('data-tooltip', nombre);
    });
    expect(screen.getByRole('button', { name: /Eliminar historia/ })).toBeInTheDocument();
  });

  it('antes de aprobarse no ofrece Solicitar cambio pero sí Editar', () => {
    render(<AccionesHistoriaComponent story={{ id: 'a', status: 'revisada' }} {...manejadores()} />);
    expect(screen.queryByRole('button', { name: 'Solicitar cambio' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Editar' })).toBeInTheDocument();
  });

  it('avisa qué acción se eligió', async () => {
    const user = userEvent.setup();
    const acciones = manejadores();
    const story = { id: 'a', status: 'aprobada' };
    render(<AccionesHistoriaComponent story={story} {...acciones} />);
    await user.click(screen.getByRole('button', { name: 'Editar' }));
    await user.click(screen.getByRole('button', { name: 'Solicitar cambio' }));
    expect(acciones.onEditar).toHaveBeenCalledWith(story);
    expect(acciones.onSolicitarCambio).toHaveBeenCalledWith(story);
  });

  it('Descargar muestra Word y PDF y descarga el formato elegido', async () => {
    const user = userEvent.setup();
    const story = { id: 'a', status: 'revisada' };
    render(<AccionesHistoriaComponent story={story} {...manejadores()} />);
    expect(screen.queryByRole('menuitem')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Descargar' }));
    expect(screen.getAllByRole('menuitem').map((item) => item.textContent.trim())).toEqual(['Word', 'PDF']);
    await user.click(screen.getByRole('menuitem', { name: /PDF/ }));
    await waitFor(() => expect(descargarPdf).toHaveBeenCalledWith(story));
    expect(descargarWord).not.toHaveBeenCalled();
    expect(screen.queryByRole('menuitem')).not.toBeInTheDocument();
  });

  it('el menú se cierra con Escape', async () => {
    const user = userEvent.setup();
    render(<AccionesHistoriaComponent story={{ id: 'a', status: 'revisada' }} {...manejadores()} />);
    await user.click(screen.getByRole('button', { name: 'Descargar' }));
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('menuitem')).not.toBeInTheDocument();
  });
});
