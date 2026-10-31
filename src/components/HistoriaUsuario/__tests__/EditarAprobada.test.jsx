import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { EditarHistoriaUsuarioComponent } from '../EditarHistoriaUsuarioComponent';
import { DetalleHistoriaUsuarioComponent } from '../DetalleHistoriaUsuarioComponent';
import { repositorioApi } from '../../../services/repositorioApi';
import { analystApi } from '../../../services/analystApi';

vi.mock('../../../services/repositorioApi', async (importOriginal) => {
  const original = await importOriginal();
  return {
    ...original,
    repositorioApi: { saveStory: vi.fn(), listChanges: vi.fn().mockResolvedValue([]), registerChange: vi.fn(), listLessons: vi.fn() },
  };
});
vi.mock('../../../services/analystApi', () => ({ analystApi: { sendMessage: vi.fn(), createConversation: vi.fn(), getHealth: vi.fn() } }));

const CLAVE = 'historias_usuario_prototipo';
const APROBADA = {
  id: 'HU-960', number: 'HU-960', title: 'Consulta de reclamos', status: 'aprobada', createdAt: '2026-10-29', createdBy: 'Ana',
  infoType: 'Minuta', description: 'Consulta del estado', userStory: { asA: 'Ejecutivo de Servico', iWant: 'consultar', soThat: 'atender' },
  acceptanceCriteria: [{ id: 'c1', given: 'hay un reclamo', when: 'consulta', then: 've el estado' }],
  questions: [{ id: 'q1', category: 'Reglas de negocio', question: '¿Quién?', answer: 'El ejecutivo', status: 'respondida' }],
  bitacora: [{ fecha: '2026-10-29', autor: 'Ana', texto: 'Nota inicial' }],
};

const renderAt = (ruta) => render(
  <MemoryRouter initialEntries={[ruta]}>
    <Routes>
      <Route path="/historias/:id" element={<DetalleHistoriaUsuarioComponent />} />
      <Route path="/historias/:id/editar" element={<EditarHistoriaUsuarioComponent />} />
      <Route path="/historias" element={<p>Listado de historias</p>} />
    </Routes>
  </MemoryRouter>,
);
const guardada = () => JSON.parse(localStorage.getItem(CLAVE))[0];

describe('editar una HU aprobada', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    repositorioApi.listChanges.mockResolvedValue([]);
    localStorage.setItem(CLAVE, JSON.stringify([APROBADA]));
  });
  afterEach(() => cleanup());

  it('corrige en el lugar: sigue aprobada, sin nueva revisión, sin agente, con registro y nota en la bitácora', async () => {
    const user = userEvent.setup();
    repositorioApi.saveStory.mockResolvedValue({});
    renderAt('/historias/HU-960/editar');
    expect(await screen.findByText(/Historia aprobada/)).toBeInTheDocument();
    expect(screen.queryByText(/Preguntas para Negocio/)).not.toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: /Historia de usuario/i }));
    const campo = screen.getByLabelText(/Como \(Rol \/ Actor\)/i);
    await user.clear(campo);
    await user.type(campo, 'Ejecutivo de Servicio');
    await user.click(screen.getByRole('tab', { name: /Observaciones y notas/i }));
    await user.type(screen.getByLabelText(/Agregar nota/i), 'Se corrigió el nombre del rol');
    await user.click(screen.getByRole('button', { name: /Guardar Todos los Cambios/i }));

    await waitFor(() => expect(repositorioApi.saveStory).toHaveBeenCalledTimes(1));
    expect(repositorioApi.saveStory.mock.calls[0][0]).toMatchObject({ id: 'HU-960', historia: { asA: 'Ejecutivo de Servicio' } });
    expect(analystApi.sendMessage).not.toHaveBeenCalled();
    await waitFor(() => expect(guardada().userStory.asA).toBe('Ejecutivo de Servicio'));
    expect(guardada()).toMatchObject({ status: 'aprobada' });
    expect(guardada().revision).toBeUndefined();
    expect(guardada().analisisDesactualizado).toBeUndefined();
    expect(guardada().ediciones).toHaveLength(1);
    expect(guardada().ediciones[0].campos).toEqual(['Historia (Como / Quiero / Para)', 'Observaciones']);
    expect(guardada().bitacora.map((nota) => nota.texto)).toEqual(['Nota inicial', 'Se corrigió el nombre del rol']);
    expect(guardada().bitacora[1].fecha).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(await screen.findByRole('tab', { name: /Historial/ })).toBeInTheDocument();
  });

  it('si el Repositorio rechaza el texto no guarda nada y muestra el motivo', async () => {
    const user = userEvent.setup();
    const error = Object.assign(new Error('El texto parece contener datos personales (cédula).'), { name: 'AnalystApiError' });
    repositorioApi.saveStory.mockRejectedValue(error);
    renderAt('/historias/HU-960/editar');
    const campo = await screen.findByLabelText(/Como \(Rol \/ Actor\)/i);
    await user.type(campo, ' 1');
    await user.click(screen.getByRole('button', { name: /Guardar Todos los Cambios/i }));
    expect(await screen.findByText(/datos personales/i)).toBeInTheDocument();
    expect(guardada().userStory.asA).toBe('Ejecutivo de Servico');
    expect(guardada().ediciones).toBeUndefined();
  });

  it('sin cambios no llama al Repositorio ni deja registro', async () => {
    const user = userEvent.setup();
    renderAt('/historias/HU-960/editar');
    await user.click(await screen.findByRole('button', { name: /Guardar Todos los Cambios/i }));
    await waitFor(() => expect(screen.queryByText(/Historia aprobada/)).not.toBeInTheDocument());
    expect(repositorioApi.saveStory).not.toHaveBeenCalled();
    expect(guardada().ediciones).toBeUndefined();
  });

  it('arriba solo ofrece Volver y Cancelar abajo; ambos regresan al listado', async () => {
    const user = userEvent.setup();
    renderAt('/historias/HU-960/editar');
    await screen.findByText(/Editar Historia/i);
    expect(screen.getAllByRole('button', { name: /Guardar/i })).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: /Volver/i }));
    expect(await screen.findByText('Listado de historias')).toBeInTheDocument();
    cleanup();
    renderAt('/historias/HU-960/editar');
    await user.click(await screen.findByRole('button', { name: /Cancelar/i }));
    expect(await screen.findByText('Listado de historias')).toBeInTheDocument();
  });
});
