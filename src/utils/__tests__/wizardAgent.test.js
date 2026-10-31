import { describe, expect, it } from 'vitest';
import {
  buildAnswersMessage,
  buildRequirementMessage,
  describeSources,
  latestAssistantResponse,
  latestFailedMessage,
  mapAnalysis,
  mergeQuestions,
  questionsToSend,
  requirementSignature,
} from '../wizardAgent.js';

describe('wizardAgent', () => {
  it('builds a new and an updated requirement message', () => {
    const data = { name: ' Cobertura ', infoType: 'Correo', description: ' Texto ' };
    expect(buildRequirementMessage(data)).toBe('REQUERIMIENTO NUEVO\nNombre: Cobertura\nTipo de información: Correo\nDescripción:\nTexto');
    expect(buildRequirementMessage(data, { isUpdate: true })).toContain('REQUERIMIENTO ACTUALIZADO');
  });

  it('uses the trimmed fields as the requirement signature', () => {
    expect(requirementSignature({ name: ' a ', infoType: 'x', description: 'b ' }))
      .toBe(requirementSignature({ name: 'a', infoType: 'x', description: 'b' }));
  });

  it('only sends answers that are new or changed', () => {
    const questions = [
      { id: 'q1', category: 'Validaciones', question: '¿Qué valida?', answer: 'El monto' },
      { id: 'q2', category: 'Datos requeridos', question: '¿Qué dato?', answer: '' },
      { id: 'q3', category: 'Excepciones', question: '¿Qué falla?', answer: 'Se rechaza' },
    ];
    expect(questionsToSend(questions, { q1: 'El monto' }).map((q) => q.id)).toEqual(['q3']);
    expect(buildAnswersMessage(questions, { q1: 'El monto' })).toContain('1. [Excepciones] ¿Qué falla?\nRespuesta: Se rechaza');
    expect(buildAnswersMessage(questions, { q1: 'El monto', q3: 'Se rechaza' })).toBe('');
  });

  it('keeps local answers when the agent returns an updated question list', () => {
    const previous = [{ id: 'q1', answer: 'Mi respuesta' }];
    const incoming = [
      { question_id: 'q1', categoria: 'Validaciones', pregunta: 'A', estado: 'pendiente' },
      { question_id: 'q2', categoria: 'Excepciones', pregunta: 'B', estado: 'respondida' },
    ];
    expect(mergeQuestions(previous, incoming)).toEqual([
      { id: 'q1', category: 'Validaciones', question: 'A', answer: 'Mi respuesta', status: 'respondida' },
      { id: 'q2', category: 'Excepciones', question: 'B', answer: '', status: 'pendiente' },
    ]);
  });

  it('conserva las respuestas aunque el agente cambie el id o reorganice las preguntas', () => {
    const previous = [
      { id: 'viejo-1', category: 'Validaciones', question: '¿Qué valida?', answer: 'El monto', status: 'respondida' },
      { id: 'viejo-2', category: 'Datos requeridos', question: 'Pregunta que desaparece', answer: 'Mi dato', status: 'respondida' },
      { id: 'viejo-3', category: 'Excepciones', question: 'Sin respuesta', answer: '', status: 'pendiente' },
    ];
    const incoming = [
      { question_id: 'nuevo-1', categoria: 'Validaciones', pregunta: '¿Qué  valida?', estado: 'respondida' },
      { question_id: 'nuevo-2', categoria: 'Excepciones', pregunta: 'Otra', estado: 'respondida' },
    ];
    const merged = mergeQuestions(previous, incoming);
    expect(merged[0]).toMatchObject({ id: 'nuevo-1', answer: 'El monto', status: 'respondida' });
    expect(merged[1]).toMatchObject({ id: 'nuevo-2', answer: '', status: 'pendiente' });
    expect(merged[2]).toMatchObject({ id: 'viejo-2', answer: 'Mi dato', status: 'respondida' });
    expect(merged).toHaveLength(3);
  });

  it('maps the analysis, sources and last messages', () => {
    expect(mapAnalysis({ conocida: ['a'], faltante: ['b'], supuesta: [], ambigua: ['c'] })).toEqual({
      knownData: ['a'], missingData: ['b'], assumptions: [], ambiguities: ['c'],
    });
    expect(describeSources([{ nombre: 'consultar_glosario', resultados: 2, duracion_ms: 1 }]))
      .toEqual([{ key: 'consultar_glosario', label: 'Glosario', count: 2 }]);
    const messages = [{ role: 'user', status: 'completed' }, { role: 'assistant', response: { turn_id: 'x' } }];
    expect(latestAssistantResponse(messages)).toEqual({ turn_id: 'x' });
    expect(latestFailedMessage(messages)).toBeNull();
    expect(latestFailedMessage([{ role: 'user', status: 'failed' }])).not.toBeNull();
  });
});
