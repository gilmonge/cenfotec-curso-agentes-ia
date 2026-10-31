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
  id: '0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c44', number: 'HU-PRU-002', title: 'Consulta de reclamos', type: 'Nueva Funcionalidad',
  status: 'pendiente_de_informacion', createdAt: '2026-10-29', updatedAt: '2026-10-29', infoType: 'Minuta', description: 'Descripción',
  userStory: { asA: 'analista', iWant: 'consultar', soThat: 'informar' },
  acceptanceCriteria: [{ id: 'c1', given: 'hay datos', when: 'se consulta', then: 'se muestra' }],
  questions: [{ id: 'q1', category: 'Validaciones', question: '¿Qué pasa si no existe?', answer: '', status: 'pendiente' }],
  pendingQuestions: ['¿Qué pasa si no existe?'],
};

const renderAt = (path) => {
  window.history.replaceState({}, '', path);
  return render(<App />);
};
const guardado = () => JSON.parse(localStorage.getItem(KEY))[0];

describe('responder preguntas pendientes desde Editar', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    analystApi.getHealth.mockResolvedValue({ status: 'ready', timeout_seconds: 90, checks: {} });
    localStorage.setItem(KEY, JSON.stringify([STORY]));
  });
  afterEach(() => cleanup());

  it('guarda la respuesta, quita la pendiente y obliga a volver a analizar', async () => {
    const user = userEvent.setup();
    renderAt(`/historias/${STORY.id}/editar`);
    await screen.findByText(/Editar Historia/);
    await user.click(screen.getByRole('tab', { name: /Preguntas para Negocio/ }));
    await user.type(await screen.findByLabelText('Respuesta de Negocio'), 'Se muestra un mensaje');
    expect(screen.getByText(/Ya no quedan preguntas pendientes/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Guardar Todos los Cambios/i }));
    await waitFor(() => expect(guardado().questions[0].answer).toBe('Se muestra un mensaje'));
    expect(guardado().questions[0].status).toBe('respondida');
    expect(guardado().pendingQuestions).toEqual([]);
    expect(guardado().analisisDesactualizado).toBe(true);
    expect(guardado().respuestasNuevas).toBe(true);
    expect(await screen.findByText('Análisis desactualizado')).toBeInTheDocument();
    expect(screen.getByText(/respuestas de Negocio después del último análisis/)).toBeInTheDocument();
  });

  it('no pide reanalizar si no se tocaron las respuestas', async () => {
    const user = userEvent.setup();
    renderAt(`/historias/${STORY.id}/editar`);
    await screen.findByText(/Editar Historia/);
    await user.click(screen.getByRole('button', { name: /Guardar Todos los Cambios/i }));
    await waitFor(() => expect(guardado().updatedBy).toBeDefined());
    expect(guardado().analisisDesactualizado).toBeUndefined();
    expect(guardado().pendingQuestions).toEqual(['¿Qué pasa si no existe?']);
  });

  it('el detalle ofrece responder las preguntas pendientes', async () => {
    const user = userEvent.setup();
    renderAt(`/historias/${STORY.id}`);
    await user.click(await screen.findByRole('tab', { name: /Preguntas pendientes/ }));
    await user.click(await screen.findByRole('button', { name: /Responder preguntas/ }));
    await screen.findByText(/Editar Historia/);
    expect(await screen.findByLabelText('Respuesta de Negocio')).toBeInTheDocument();
  });
});
