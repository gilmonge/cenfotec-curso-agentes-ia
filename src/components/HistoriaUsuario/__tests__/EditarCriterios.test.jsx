import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../../App.jsx';
import { analystApi } from '../../../services/analystApi.js';

vi.mock('../../../services/analystApi.js', () => ({
  request: vi.fn(),
  analystApi: { getHealth: vi.fn(), createConversation: vi.fn(), sendMessage: vi.fn(), cancelTurn: vi.fn(), resetConversation: vi.fn(), deleteConversation: vi.fn() },
}));

const KEY = 'historias_usuario_prototipo';
const STORY = {
  id: '0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c33', number: 'HU-PRU-001', title: 'Registro de solicitud', type: 'Nueva Funcionalidad',
  status: 'revisada', createdAt: '2026-10-29', updatedAt: '2026-10-29', infoType: 'Minuta', description: 'Descripción',
  userStory: { asA: 'analista', iWant: 'registrar', soThat: 'tener control' },
  acceptanceCriteria: [{ id: 'c1', given: 'hay datos', when: 'se guarda', then: 'se registra' }],
};

function renderAt(path) {
  window.history.replaceState({}, '', path);
  return render(<App />);
}

const abrir = (user, nombre) => user.click(screen.getByRole('tab', { name: nombre }));
const guardado = () => JSON.parse(localStorage.getItem(KEY))[0];

describe('edición de criterios de aceptación', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    analystApi.getHealth.mockResolvedValue({ status: 'ready', timeout_seconds: 90, checks: {} });
    localStorage.setItem(KEY, JSON.stringify([STORY]));
  });
  afterEach(() => cleanup());

  it('permite cambiar solo el Cuando y avisa que los criterios cambiaron sin pedir un nuevo análisis', async () => {
    const user = userEvent.setup();
    renderAt(`/historias/${STORY.id}/editar`);
    await screen.findByText(/Editar Historia/);
    await abrir(user, /Criterios de aceptación/);
    const cuando = await screen.findByLabelText('Cuando');
    await user.clear(cuando);
    await user.type(cuando, 'se cancela');
    await user.click(screen.getByRole('button', { name: /Guardar Todos los Cambios/i }));
    await waitFor(() => expect(guardado().acceptanceCriteria[0].when).toBe('se cancela'));
    expect(guardado().criteriosModificados).toBe(true);
    expect(guardado().analisisDesactualizado).toBeUndefined();
    expect(await screen.findByText('Criterios modificados')).toBeInTheDocument();
    expect(screen.queryByText('Análisis desactualizado')).not.toBeInTheDocument();
  });

  it('no marca criterios modificados si no se tocaron', async () => {
    const user = userEvent.setup();
    renderAt(`/historias/${STORY.id}/editar`);
    await screen.findByText(/Editar Historia/);
    await user.click(screen.getByRole('button', { name: /Guardar Todos los Cambios/i }));
    await waitFor(() => expect(guardado().updatedBy).toBeDefined());
    expect(guardado().criteriosModificados).toBeUndefined();
  });

  it('no deja guardar un criterio incompleto', async () => {
    const user = userEvent.setup();
    renderAt(`/historias/${STORY.id}/editar`);
    await screen.findByText(/Editar Historia/);
    await abrir(user, /Criterios de aceptación/);
    const entonces = await screen.findByLabelText('Entonces');
    await user.clear(entonces);
    await user.click(screen.getByRole('button', { name: /Guardar Todos los Cambios/i }));
    expect(await screen.findByText('Revise los criterios de aceptación')).toBeInTheDocument();
    expect(screen.getAllByText(/Complete Dado que, Cuando y Entonces del criterio 1/).length).toBeGreaterThan(0);
    expect(guardado().acceptanceCriteria[0].then).toBe('se registra');
  });

  it('el selector de sistema y de área ofrecen sus listas', async () => {
    const user = userEvent.setup();
    renderAt(`/historias/${STORY.id}/editar`);
    await screen.findByText(/Editar Historia/);
    await abrir(user, /Datos de la plantilla/);
    const sistema = await screen.findByLabelText('Sistema');
    expect(sistema.tagName).toBe('SELECT');
    expect(sistema.querySelectorAll('option').length).toBeGreaterThanOrEqual(6);
    expect(screen.getByLabelText('Área solicitante').querySelectorAll('option').length).toBeGreaterThanOrEqual(6);
  });
});
