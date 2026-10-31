import { describe, expect, it } from 'vitest';
import { construirReanalisis } from '../plantillaHu';
import { aplicarRespuestas, respuestasCambiaron, respuestasDePreguntas, textoPendiente } from '../preguntas';

const lista = [
  { id: 'a', question: 'Pregunta A', answer: 'Algo', status: 'respondida' },
  { id: 'b', question: 'Pregunta B', answer: '', status: 'pendiente' },
];

describe('respuestas de Negocio en Editar', () => {
  it('detecta respuestas agregadas o cambiadas, pero no espacios sobrantes', () => {
    expect(respuestasCambiaron(lista, respuestasDePreguntas(lista))).toBe(false);
    expect(respuestasCambiaron(lista, ['Algo ', '  '])).toBe(false);
    expect(respuestasCambiaron(lista, ['Algo', 'Nueva'])).toBe(true);
    expect(respuestasCambiaron(lista, ['Otro', ''])).toBe(true);
  });

  it('solo marca respondida si hay texto y calcula los pendientes desde las preguntas', () => {
    const aplicada = aplicarRespuestas(lista, ['Algo', 'Nueva']);
    expect(aplicada.map((p) => p.status)).toEqual(['respondida', 'respondida']);
    expect(textoPendiente(aplicada)).toEqual([]);
    expect(textoPendiente(aplicarRespuestas(lista, ['', '']))).toEqual(['Pregunta A', 'Pregunta B']);
  });

  it('el reanálisis lleva las preguntas con sus respuestas para que el agente no las repita', () => {
    expect(construirReanalisis({ title: 'X', questions: lista }).questions).toEqual(lista);
    expect(construirReanalisis({ title: 'X' }).questions).toEqual([]);
  });
});
