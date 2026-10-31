import { beforeEach, describe, expect, it } from 'vitest';
import { SIN_IDENTIFICAR, autorDe, guardarNombreUsuario, leerNombreUsuario, normalizarNombre } from '../usuarioActual';
import { addStory, getStoredStories, updateStory } from '../storage';

describe('usuario actual', () => {
  beforeEach(() => localStorage.clear());

  it('normaliza y recuerda el nombre', () => {
    expect(normalizarNombre('  Ana   María  ')).toBe('Ana María');
    guardarNombreUsuario('  Ana   María ');
    expect(leerNombreUsuario()).toBe('Ana María');
    guardarNombreUsuario('');
    expect(leerNombreUsuario()).toBe('');
  });

  it('registra quién crea y quién modifica una historia', () => {
    guardarNombreUsuario('Persona Uno');
    const creada = addStory({ title: 'Prueba' });
    expect(creada.createdBy).toBe('Persona Uno');
    expect(creada.updatedBy).toBe('Persona Uno');

    guardarNombreUsuario('Persona Dos');
    const modificada = updateStory(creada.id, { title: 'Prueba 2' });
    expect(modificada.createdBy).toBe('Persona Uno');
    expect(modificada.updatedBy).toBe('Persona Dos');
    expect(getStoredStories().find((s) => s.id === creada.id).updatedBy).toBe('Persona Dos');
  });

  it('muestra «Sin identificar» cuando no hay dato', () => {
    expect(autorDe({})).toBe(SIN_IDENTIFICAR);
    expect(autorDe({ createdBy: 'Persona Uno' })).toBe('Persona Uno');
    expect(autorDe({ createdBy: 'Persona Uno', updatedBy: 'Persona Dos' })).toBe('Persona Dos');
  });
});
