import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BitacoraComponent } from '../BitacoraComponent';
import { construirSecciones } from '../secciones';

const story = {
  bitacora: [
    { fecha: '2026-11-26', autor: 'Yuvania', tipo: 'decision', texto: '¿La carga usa el mismo formato?\nDecisión: Sí.' },
    { fecha: '2026-11-26', autor: 'Redactor-Revisor', tipo: 'dependencia', texto: 'Servicio al Cliente avisará el cambio.', estado: 'abierto' },
  ],
};

describe('bitácora de la HU en pantalla', () => {
  afterEach(cleanup);

  it('muestra cada entrada aparte con su tipo, y estado solo en lo que pide una acción', () => {
    render(<BitacoraComponent story={story} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText('Decisión')).toBeInTheDocument();
    expect(screen.getByText('Dependencia')).toBeInTheDocument();
    expect(screen.getAllByText('Abierto')).toHaveLength(1);
    // Sin manejador (por ejemplo, en la edición) no se ofrece cambiar el estado.
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('permite marcar como atendida una dependencia', async () => {
    const onCambiarEstado = vi.fn();
    render(<BitacoraComponent story={story} onCambiarEstado={onCambiarEstado} />);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Marcar como atendido' }));
    expect(onCambiarEstado).toHaveBeenCalledWith(1, 'atendido');
  });

  it('el detalle no tiene sección de impacto: el impacto va en los criterios de aceptación', () => {
    const ids = construirSecciones({ ...story, impactoNegocio: [{ area: 'Carga masiva', hoy: 'a', debe: 'b' }] })
      .map((seccion) => seccion.id);
    expect(ids).not.toContain('impacto');
    expect(ids).toContain('observaciones');
  });
});
