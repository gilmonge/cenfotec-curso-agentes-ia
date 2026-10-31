import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UltimasHistoriasComponent, ultimasHistorias } from '../UltimasHistoriasComponent';

const hu = (id, fecha, extra = {}) => ({ id, title: `Título ${id}`, status: 'aprobada', createdAt: fecha, updatedAt: fecha, createdBy: 'Yuvania', ...extra });

describe('últimas historias del panel', () => {
  it('ordena de la más reciente a la más antigua y limita a 5', () => {
    const lista = ['2026-10-01', '2026-10-05', '2026-10-03', '2026-10-07', '2026-10-02', '2026-10-06'].map((fecha, i) => hu(`H${i}`, fecha));
    expect(ultimasHistorias(lista).map((story) => story.updatedAt)).toEqual([
      '2026-10-07', '2026-10-06', '2026-10-05', '2026-10-03', '2026-10-02',
    ]);
  });

  it('muestra estado, revisión y abre la historia elegida', async () => {
    const user = userEvent.setup();
    const onVer = vi.fn();
    render(<UltimasHistoriasComponent stories={[hu('HU-1', '2026-10-31', { revision: 2 })]} onVer={onVer} onVerTodas={vi.fn()} />);
    expect(screen.getByText(/Título HU-1/)).toBeInTheDocument();
    expect(screen.getByText(/Rev\. 2/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Ver' }));
    expect(onVer).toHaveBeenCalledWith('HU-1');
  });

  it('sin historias invita a crear la primera', () => {
    render(<UltimasHistoriasComponent stories={[]} onVer={vi.fn()} onVerTodas={vi.fn()} />);
    expect(screen.getByText(/Todavía no hay historias/)).toBeInTheDocument();
  });
});
