import { describe, expect, it } from 'vitest';
import { OPCION_AREA_SOLICITANTE, OPCION_SISTEMA, armarOpcion } from '../catalogos';

describe('listas de los selectores', () => {
  it('tienen al menos cinco áreas y cinco sistemas sin repetir', () => {
    expect(OPCION_AREA_SOLICITANTE.length).toBeGreaterThanOrEqual(5);
    expect(OPCION_SISTEMA.length).toBeGreaterThanOrEqual(5);
    expect(new Set(OPCION_AREA_SOLICITANTE).size).toBe(OPCION_AREA_SOLICITANTE.length);
    expect(new Set(OPCION_SISTEMA).size).toBe(OPCION_SISTEMA.length);
  });

  it('empiezan con una opción vacía y no ofrecen "Otro"', () => {
    const opcion = armarOpcion(OPCION_SISTEMA, '', 'Seleccione un sistema');
    expect(opcion[0]).toEqual({ value: '', label: 'Seleccione un sistema' });
    expect(opcion.map((item) => item.label.toLowerCase())).not.toContain('otro');
  });

  it('conserva un valor guardado que ya no está en la lista para no perderlo al editar', () => {
    const opcion = armarOpcion(OPCION_SISTEMA, 'Sistema anterior', 'Seleccione un sistema');
    expect(opcion.at(-1)).toEqual({ value: 'Sistema anterior', label: 'Sistema anterior' });
  });
});
