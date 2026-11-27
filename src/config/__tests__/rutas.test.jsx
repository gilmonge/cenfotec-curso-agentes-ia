import { describe, expect, it } from 'vitest';
import { listaOpcionMenu, listaRuta } from '../rutas';

// Barandas del registro único de pantallas (ver docs/arquitectura.md, skill «agregar-ruta»).
describe('registro de pantallas', () => {
  it('cada ruta es única y tiene componente', () => {
    const ruta = listaRuta.map((entrada) => entrada.ruta);
    expect(new Set(ruta).size).toBe(ruta.length);
    listaRuta.forEach((entrada) => expect(typeof entrada.componente).toBe('function'));
  });

  it('el menú sale del registro, en orden y sin órdenes repetidos', () => {
    const listaOpcion = listaOpcionMenu();
    expect(listaOpcion.map((opcion) => opcion.etiqueta)).toEqual(['Inicio', 'Pendientes', 'Historias de usuario', 'Nueva historia', 'Mantenimiento', 'Ayuda']);
    expect(new Set(listaOpcion.map((opcion) => opcion.orden)).size).toBe(listaOpcion.length);
    listaOpcion.forEach((opcion) => {
      expect(opcion.titulo).toBeTruthy();
      expect(opcion.icono).toBeTruthy();
    });
  });
});
