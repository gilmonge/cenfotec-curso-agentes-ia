import { describe, expect, it } from 'vitest';
import { isValidAnalystResponse, validateAnalystResponse } from '../utils/analystResponse.js';

const validResponse = {
  conversation_id: '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
  request_id: '9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d',
  turn_id: '2a5b7c9d-1e3f-4a6b-8c0d-2e4f6a8b0c1d',
  estado: 'completado',
  respuesta_markdown: 'Análisis completo.',
  analisis: { conocida: ['Solicitud'], faltante: [], supuesta: [], ambigua: [] },
  preguntas: [],
  fuentes_consultadas: [{ nombre: 'consultar_glosario', resultados: 0, duracion_ms: 12 }],
  listo_para_redactor: true,
  limitaciones: [],
  duracion_ms: 80,
  prompt_version: '1.0.0',
};

describe('analyst response validation', () => {
  it('accepts the complete public response contract', () => {
    expect(validateAnalystResponse(validResponse)).toEqual(validResponse);
    expect(isValidAnalystResponse(validResponse)).toBe(true);
  });

  it('rejects incomplete payloads and never returns partial content', () => {
    expect(isValidAnalystResponse({ ...validResponse, analisis: { conocida: [] } })).toBe(false);
    let raised;
    try { validateAnalystResponse({ ...validResponse, respuesta_markdown: '' }); } catch (error) { raised = error; }
    expect(raised).toMatchObject({ code: 'AGENT_OUTPUT_INVALID', retryable: false });
  });

  it('rejects readiness that conflicts with unresolved gaps', () => {
    const contradictory = {
      ...validResponse,
      analisis: { conocida: [], faltante: ['Plazo'], supuesta: [], ambigua: [] },
      listo_para_redactor: true,
    };
    expect(isValidAnalystResponse(contradictory)).toBe(false);
  });

  it('rejects unexpected fields before rendering', () => {
    expect(isValidAnalystResponse({ ...validResponse, internal_trace_id: 'private' })).toBe(false);
  });
});
