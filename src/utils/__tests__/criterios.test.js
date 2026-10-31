import { describe, expect, it } from 'vitest';
import {
  criteriosCambiaron, criteriosGenericos, criteriosParaEditar, limpiarCriterios, resumenCriterio, validarCriterios,
} from '../criterios';

const completo = { id: 'a', given: 'hay datos', when: 'se guarda', then: 'se registra' };

describe('criterios de aceptación (Dado que / Cuando / Entonces)', () => {
  it('los criterios genéricos están completos y no traen datos del requerimiento', () => {
    const lista = criteriosGenericos();
    expect(lista).toHaveLength(3);
    expect(validarCriterios(lista).ok).toBe(true);
    expect(new Set(lista.map((criterio) => criterio.id)).size).toBe(3);
  });

  it('exige al menos un criterio completo y rechaza los incompletos', () => {
    expect(validarCriterios([]).ok).toBe(false);
    expect(validarCriterios([{ id: 'x', given: '', when: '', then: '' }]).ok).toBe(false);
    const parcial = validarCriterios([completo, { id: 'y', given: 'algo', when: '', then: '' }]);
    expect(parcial.ok).toBe(false);
    expect(parcial.error).toMatch(/criterio 2/);
    expect(validarCriterios([completo, { id: 'z', given: '', when: '', then: '' }]).ok).toBe(true);
  });

  it('limpia criterios vacíos y etiquetas repetidas antes de guardar', () => {
    const lista = limpiarCriterios([
      { id: 'a', given: 'Dado que hay datos', when: ' Cuando se guarda ', then: 'Entonces se registra' },
      { id: 'b', given: '', when: '', then: '' },
    ]);
    expect(lista).toEqual([{ id: 'a', given: 'hay datos', when: 'se guarda', then: 'se registra' }]);
  });

  it('arma la frase resumen y conserva criterios antiguos de solo texto', () => {
    expect(resumenCriterio(completo)).toBe('Dado que hay datos, cuando se guarda, entonces se registra.');
    expect(resumenCriterio({ text: 'Criterio libre' })).toBe('Criterio libre');
    expect(criteriosParaEditar([{ text: 'Criterio libre' }])[0]).toMatchObject({ given: '', when: '', then: 'Criterio libre' });
  });

  it('detecta si cambió algún campo, aunque sea solo el Cuando o el Entonces', () => {
    expect(criteriosCambiaron([completo], [{ ...completo }])).toBe(false);
    expect(criteriosCambiaron([completo], [{ ...completo, when: 'se cancela' }])).toBe(true);
    expect(criteriosCambiaron([completo], [{ ...completo, then: 'se rechaza' }])).toBe(true);
    expect(criteriosCambiaron([completo], [completo, { ...completo, id: 'b' }])).toBe(true);
  });
});
