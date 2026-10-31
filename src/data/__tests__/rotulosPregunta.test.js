import { describe, expect, it } from 'vitest';
import { ayudaCategoria, rotuloCategoria } from '../rotulosPregunta';

describe('rótulos de las categorías de pregunta', () => {
  const categoria = ['Reglas de negocio', 'Datos requeridos', 'Validaciones', 'Excepciones', 'Comportamiento esperado'];

  it('cada categoría del agente tiene un rótulo en lenguaje natural y una ayuda', () => {
    categoria.forEach((valor) => {
      expect(rotuloCategoria(valor)).not.toBe(valor);
      expect(ayudaCategoria(valor).length).toBeGreaterThan(10);
    });
    expect(rotuloCategoria('Excepciones')).toBe('Qué pasa si algo sale mal');
  });

  it('una categoría desconocida se muestra tal cual', () => {
    expect(rotuloCategoria('Otra cosa')).toBe('Otra cosa');
    expect(ayudaCategoria('Otra cosa')).toBe('');
  });
});
