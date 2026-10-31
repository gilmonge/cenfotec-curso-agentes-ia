import { beforeEach, describe, expect, it } from 'vitest';
import { borrarBorrador, borradorTieneContenido, guardarBorrador, leerBorrador } from '../borradorAsistente';

describe('borrador del asistente', () => {
  beforeEach(() => localStorage.clear());

  it('guarda, lee y borra el avance', () => {
    expect(leerBorrador()).toBeNull();
    guardarBorrador({ requirementName: 'Consulta', activeStep: 3 });
    expect(leerBorrador()).toEqual({ requirementName: 'Consulta', activeStep: 3 });
    borrarBorrador();
    expect(leerBorrador()).toBeNull();
  });

  it('ignora un borrador dañado o de otra versión', () => {
    localStorage.setItem('historias_borrador_nueva', '{no es json');
    expect(leerBorrador()).toBeNull();
    localStorage.setItem('historias_borrador_nueva', JSON.stringify({ version: 99, estado: { a: 1 } }));
    expect(leerBorrador()).toBeNull();
  });

  it('solo vale la pena guardar si la persona ya escribió algo', () => {
    expect(borradorTieneContenido({ requirementName: ' ', description: '' })).toBe(false);
    expect(borradorTieneContenido({ requirementName: 'Algo', description: '' })).toBe(true);
  });
});
