import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { CrearHistoriaUsuarioComponent } from '../CrearHistoriaUsuarioComponent';

const abrir = () => render(<MemoryRouter><CrearHistoriaUsuarioComponent /></MemoryRouter>);

describe('Nueva historia: borrador automático', () => {
  beforeEach(() => localStorage.clear());

  it('recupera lo escrito al volver a abrir el asistente y permite descartarlo', async () => {
    const user = userEvent.setup();
    const primera = abrir();
    await user.type(screen.getByLabelText(/Nombre del requerimiento/), 'Consulta de reclamos');
    await user.type(screen.getByLabelText(/^Descripción o información/), 'Texto de prueba');
    primera.unmount();

    abrir();
    expect(screen.getByText('Se recuperó su borrador')).toBeInTheDocument();
    expect(screen.getByLabelText(/Nombre del requerimiento/)).toHaveValue('Consulta de reclamos');
    expect(screen.getByLabelText(/^Descripción o información/)).toHaveValue('Texto de prueba');

    await user.click(screen.getByRole('button', { name: /Descartar borrador/ }));
    expect(screen.queryByText('Se recuperó su borrador')).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Nombre del requerimiento/)).toHaveValue('');
    expect(localStorage.getItem('historias_borrador_nueva')).toBeNull();
  });

  it('no muestra el aviso cuando no hay borrador', () => {
    abrir();
    expect(screen.queryByText('Se recuperó su borrador')).not.toBeInTheDocument();
  });
});
