import { describe, expect, it } from 'vitest';
import { construirSecciones, seccionActiva } from '../secciones';

const ids = (story) => construirSecciones(story).map((seccion) => seccion.id);

describe('secciones del detalle de la HU', () => {
  it('una HU sin datos opcionales solo muestra Historia y Criterios', () => {
    expect(ids({ status: 'borrador' })).toEqual(['historia', 'criterios']);
  });

  it('muestra cada sección opcional solo cuando la HU tiene ese dato', () => {
    const story = {
      status: 'aprobada', acceptanceCriteria: [{}, {}], pendingQuestions: ['¿a?'], observations: 'nota',
      revisiones: [{ revision: 1 }], analysis: { resumen: 'x' }, system: 'Portal',
    };
    expect(ids(story)).toEqual([
      'historia', 'criterios', 'preguntas', 'observaciones', 'revisiones', 'analisis', 'plantilla',
    ]);
  });

  it('el detalle no incluye solicitudes de cambio, ni siquiera en una HU aprobada', () => {
    expect(ids({ status: 'aprobada' })).not.toContain('solicitudes');
  });

  it('lleva el contador de criterios, preguntas y revisiones', () => {
    const secciones = construirSecciones({ acceptanceCriteria: [{}, {}, {}], pendingQuestions: ['a'], revisiones: [{}, {}] });
    const contador = Object.fromEntries(secciones.map((seccion) => [seccion.id, seccion.contador]));
    expect(contador).toMatchObject({ historia: null, criterios: 3, preguntas: 1, revisiones: 2 });
  });

  it('si la sección pedida no existe vuelve a la primera', () => {
    const secciones = construirSecciones({ status: 'borrador' });
    expect(seccionActiva(secciones, 'analisis')).toBe('historia');
    expect(seccionActiva(secciones, 'criterios')).toBe('criterios');
  });
});
