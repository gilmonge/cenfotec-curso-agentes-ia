import { describe, expect, it } from 'vitest';
import { LISTA_PASO, pasoPorId } from '../pasosAsistente';
import { PASO } from '../constantesAsistente';

// Barandas del registro de pasos del asistente (ver docs/arquitectura.md).
describe('registro de pasos del asistente', () => {
  it('tiene un paso por cada valor de PASO, en orden y con su vista', () => {
    expect(LISTA_PASO.map((paso) => paso.id)).toEqual(Object.values(PASO));
    LISTA_PASO.forEach((paso) => {
      expect(paso.etiqueta).toBeTruthy();
      expect(typeof paso.Componente).toBe('function');
      expect(paso.Componente.name).toMatch(/^Paso.+Component$/);
    });
  });

  it('un paso inexistente no tiene vista', () => {
    expect(pasoPorId(99)).toBeNull();
    expect(pasoPorId(PASO.PREGUNTAS).etiqueta).toBe('Preguntas a Negocio');
  });
});
