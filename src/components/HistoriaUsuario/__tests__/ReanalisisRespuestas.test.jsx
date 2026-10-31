import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../../App.jsx';
import { analystApi } from '../../../services/analystApi.js';

vi.mock('../../../services/analystApi.js', () => ({
  request: vi.fn(),
  analystApi: { getHealth: vi.fn(), createConversation: vi.fn(), sendMessage: vi.fn(), cancelTurn: vi.fn(), resetConversation: vi.fn(), deleteConversation: vi.fn() },
}));

const KEY = 'historias_usuario_prototipo';
const CONVERSACION = '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f';
const STORY = {
  id: '0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c55', number: 'HU-REC-001', title: 'Consulta de reclamos', type: 'Nueva Funcionalidad',
  status: 'pendiente_de_informacion', createdAt: '2026-10-29', updatedAt: '2026-10-29', infoType: 'Minuta', description: 'Descripción del requerimiento',
  system: 'Gestión de Reclamos', codigoHu: 'REC', requestType: 'Requerimiento',
  analisisDesactualizado: true, respuestasNuevas: true,
  userStory: { asA: 'a', iWant: 'b', soThat: 'c' },
  acceptanceCriteria: [{ id: 'c1', given: 'g', when: 'w', then: 't' }],
  questions: [{ id: 'q-viejo', category: 'Validaciones', question: '¿Qué pasa si no existe?', answer: 'Se muestra un mensaje', status: 'respondida' }],
  pendingQuestions: [],
};

describe('reanálisis con respuestas ya registradas', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    localStorage.setItem(KEY, JSON.stringify([STORY]));
    analystApi.getHealth.mockResolvedValue({ status: 'ready', timeout_seconds: 90, checks: {} });
    analystApi.createConversation.mockResolvedValue({ conversation_id: CONVERSACION });
    analystApi.sendMessage.mockImplementation(async (_id, payload) => ({
      conversation_id: CONVERSACION, request_id: payload.request_id, turn_id: '2a5b7c9d-1e3f-4a6b-8c0d-2e4f6a8b0c01', estado: 'completado',
      respuesta_markdown: 'Resumen', analisis: { conocida: [], faltante: [], supuesta: [], ambigua: [] },
      preguntas: [{ question_id: 'q-nuevo', categoria: 'Datos requeridos', pregunta: '¿Qué datos se muestran?', estado: 'pendiente', created_turn_id: null, updated_turn_id: null }],
      fuentes_consultadas: [], listo_para_redactor: false, limitaciones: [], duracion_ms: 1, prompt_version: '1.6.0',
    }));
  });
  afterEach(() => cleanup());

  it('envía las respuestas guardadas junto con el requerimiento y las conserva en la lista', async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, '', `/historias/${STORY.id}`);
    render(<App />);
    await user.click(await screen.findByRole('button', { name: /Volver a analizar/ }));
    await user.click(await screen.findByRole('button', { name: /Analizar Requerimiento/i }));
    await screen.findByText(/Paso 2 — Análisis del Agente Analista/i);

    const mensaje = analystApi.sendMessage.mock.calls[0][1].message;
    expect(mensaje).toContain('REQUERIMIENTO NUEVO');
    expect(mensaje).toContain('RESPUESTAS DE NEGOCIO');
    expect(mensaje).toContain('¿Qué pasa si no existe?');
    expect(mensaje).toContain('Se muestra un mensaje');

    await user.click(screen.getByRole('button', { name: /Preguntas a Negocio/i }));
    expect(await screen.findByText(/¿Qué datos se muestran\?/)).toBeInTheDocument();
    expect(screen.getByText(/¿Qué pasa si no existe\?/)).toBeInTheDocument();
    expect(screen.getByDisplayValue('Se muestra un mensaje')).toBeInTheDocument();
  });
});
