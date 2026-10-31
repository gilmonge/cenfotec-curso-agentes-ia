import { describe, expect, it } from 'vitest';
import { aplicarRevision, construirRevision, etiquetaRevision, fotoRevision, numeroRevision } from '../revisiones';

const HU = {
  id: 'hu-1', number: 'HU-REC-001', title: 'Consulta', system: 'Gestión de Reclamos', codigoHu: 'REC', approvedAt: '2026-10-29',
  userStory: { asA: 'a', iWant: 'b', soThat: 'c' }, acceptanceCriteria: [{ id: 'c1', given: 'g', when: 'w', then: 't' }],
  questions: [{ id: 'q', question: 'P', answer: 'R', status: 'respondida' }],
};

describe('revisiones de una HU aprobada', () => {
  it('empieza en Rev. 1 y sube de a una', () => {
    expect(numeroRevision(HU)).toBe(1);
    expect(etiquetaRevision({ revision: 3 })).toBe('Rev. 3');
    expect(aplicarRevision(HU, { title: 'x' }, ' cambio ').revision).toBe(2);
  });

  it('el análisis parte de la HU vigente: mismos datos, respuestas y referencia a la misma HU', () => {
    const prefill = construirRevision(HU, 'Aplicar a endosos');
    expect(prefill).toMatchObject({ name: 'Consulta', system: 'Gestión de Reclamos', codigoHu: 'REC', number: 'HU-REC-001', revisionDeId: 'hu-1', motivoRevision: 'Aplicar a endosos' });
    expect(prefill.description).toContain('Aplicar a endosos');
    expect(prefill.questions).toEqual(HU.questions);
    expect(prefill.userStory).toEqual(HU.userStory);
  });

  it('guarda la revisión anterior en el historial con su motivo', () => {
    const nueva = aplicarRevision(HU, { title: 'Consulta v2' }, 'Aplicar a endosos');
    expect(nueva.revisiones).toEqual([fotoRevision(HU)]);
    expect(nueva.revisiones[0]).toMatchObject({ revision: 1, motivo: 'Aprobación inicial' });
    const otra = aplicarRevision({ ...HU, ...nueva, revision: 2 }, { title: 'v3' }, 'Otro cambio');
    expect(otra.revisiones.map((r) => [r.revision, r.motivo])).toEqual([[1, 'Aprobación inicial'], [2, 'Aplicar a endosos']]);
    expect(otra.revision).toBe(3);
  });
});
