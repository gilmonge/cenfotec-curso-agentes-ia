import { describe, expect, it } from 'vitest';
import { bitacoraConNota, leerBitacora, textosBitacora } from '../bitacora';

describe('bitácora de seguimiento de la HU', () => {
  it('una HU antigua con un solo texto de observaciones lo muestra como nota inicial', () => {
    const lista = leerBitacora({ observations: ' Tener en cuenta el límite ', createdAt: '2026-10-01', createdBy: 'Ana' });
    expect(lista).toEqual([{ fecha: '2026-10-01', autor: 'Ana', texto: 'Tener en cuenta el límite' }]);
  });

  it('agrega la nota nueva con fecha y autor sin borrar las anteriores', () => {
    const historia = { bitacora: [{ fecha: '2026-10-01', autor: 'Ana', texto: 'Primera' }] };
    const lista = bitacoraConNota(historia, '  Segunda ', { fecha: '2026-10-02', autor: 'Luis' });
    expect(lista).toEqual([
      { fecha: '2026-10-01', autor: 'Ana', texto: 'Primera' },
      { fecha: '2026-10-02', autor: 'Luis', texto: 'Segunda' },
    ]);
  });

  it('una nota vacía no cambia la bitácora y una HU sin notas devuelve lista vacía', () => {
    expect(bitacoraConNota({ bitacora: [] }, '   ')).toEqual([]);
    expect(leerBitacora({})).toEqual([]);
    expect(bitacoraConNota(null, 'Primera', { fecha: '2026-10-02', autor: 'Ana' })).toHaveLength(1);
  });

  it('para los documentos entrega solo los textos', () => {
    expect(textosBitacora({ bitacora: [{ fecha: 'x', autor: 'y', texto: 'A' }, { fecha: 'x', autor: 'y', texto: 'B' }] })).toEqual(['A', 'B']);
  });
});
