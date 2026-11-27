import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { PendientesComponent } from '../PendientesComponent';
import { pendientesApi } from '../../../services/pendientesApi';

const RESPUESTA = {
  por_decidir: [{ tipo: 'por_aprobar', workflow_id: 'wf-1', titulo: 'Validar fecha de nacimiento', creado_por: 'Luis' }],
  avisos: [{ id: 'av-1', tipo: 'devuelta', titulo: 'Teléfono opcional', detalle: 'Falta un criterio', autor: 'Ana', workflow_id: 'wf-2' }],
  total: 2,
};

describe('Pendientes', () => {
  it('muestra lo que espera la decisión y los avisos, y abre la historia para decidir', async () => {
    vi.mocked(pendientesApi.listar).mockResolvedValue(RESPUESTA);
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/pendientes']}>
        <Routes>
          <Route path="/pendientes" element={<PendientesComponent />} />
          <Route path="/historias/nueva" element={<p>Asistente abierto</p>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('Validar fecha de nacimiento')).toBeInTheDocument();
    expect(screen.getByText(/Su historia fue devuelta para ajustes: Teléfono opcional/)).toBeInTheDocument();
    expect(screen.getByText('Motivo: Falta un criterio')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Marcar como leído' }));
    await waitFor(() => expect(pendientesApi.marcarLeido).toHaveBeenCalledWith('av-1'));

    await user.click(screen.getByRole('button', { name: 'Revisar y decidir' }));
    expect(await screen.findByText('Asistente abierto')).toBeInTheDocument();
    vi.mocked(pendientesApi.listar).mockReset();
  });
});
