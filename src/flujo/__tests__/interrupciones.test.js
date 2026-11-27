import { describe, expect, it } from 'vitest';
import { registroInterrupcion } from '../interrupciones';

// Cada tipo de intervención humana que manda el backend tiene su formulario y su respuesta.
const TIPO_BACKEND = ['business_answers', 'po_approval', 'change_decision'];

describe('registro de intervenciones humanas', () => {
  it('cubre todos los tipos del backend con campos y respuesta', () => {
    expect(Object.keys(registroInterrupcion).sort()).toEqual([...TIPO_BACKEND].sort());
    Object.values(registroInterrupcion).forEach((tipo) => {
      expect(typeof tipo.Campos).toBe('function');
      expect(typeof tipo.construir).toBe('function');
    });
  });

  it('la aprobación del PO exige motivo al devolver y pide confirmación', () => {
    const vacio = { answers: {}, decision: '', reason: '', lessonDecisions: {} };
    const { construir } = registroInterrupcion.po_approval;
    expect(construir({}, vacio).error).toMatch(/Seleccione/);
    expect(construir({}, { ...vacio, decision: 'devolver_redactor' }).error).toMatch(/motivo/);
    expect(construir({}, { ...vacio, decision: 'aprobar' })).toMatchObject({
      response: { decision: 'aprobar' }, confirmar: expect.stringContaining('Aprobar HU'),
    });
  });
});
