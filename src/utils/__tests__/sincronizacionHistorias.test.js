import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../services/repositorioApi', () => ({
  historiasApi: { list: vi.fn(), save: vi.fn(), remove: vi.fn() },
}));

import { historiasApi } from '../../services/repositorioApi';
import { addStory, deleteStory, getStoredStories, guardarHistoria, habilitarSincronizacion, sincronizarHistorias } from '../storage';

const GUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  historiasApi.save.mockResolvedValue({});
  historiasApi.remove.mockResolvedValue(null);
  habilitarSincronizacion(true);
});

describe('historias en la base de datos', () => {
  it('empieza vacía: no se siembran historias de ejemplo', () => {
    expect(getStoredStories()).toEqual([]);
    expect(localStorage.getItem('historias_usuario_prototipo')).toBeNull();
  });

  it('no llama al backend si la sincronización no está habilitada', async () => {
    habilitarSincronizacion(false);
    addStory({ title: 'Local' });
    expect(await sincronizarHistorias()).toBe(false);
    expect(historiasApi.save).not.toHaveBeenCalled();
  });

  it('la base es la fuente de verdad: reemplaza la caché con altas y bajas de otros dispositivos', async () => {
    localStorage.setItem('historias_usuario_prototipo', JSON.stringify([{ id: 'viejo', createdAt: '2026-10-01' }]));
    const remota = { id: '0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c01', title: 'Otro dispositivo', createdAt: '2026-10-05' };
    historiasApi.list.mockResolvedValue([remota]);
    const evento = vi.fn();
    window.addEventListener('historias-sincronizadas', evento);
    expect(await sincronizarHistorias()).toBe(true);
    expect(getStoredStories()).toEqual([remota]);
    expect(historiasApi.save).not.toHaveBeenCalled();
    expect(evento).toHaveBeenCalled();
  });

  it('una base vacía deja la caché vacía', async () => {
    localStorage.setItem('historias_usuario_prototipo', JSON.stringify([{ id: 'x', createdAt: '2026-10-01' }]));
    historiasApi.list.mockResolvedValue([]);
    await sincronizarHistorias();
    expect(getStoredStories()).toEqual([]);
  });

  it('crear usa un GUID aleatorio y escribe en la base; eliminar también', async () => {
    const creada = addStory({ title: 'Nueva' });
    expect(creada.id).toMatch(GUID);
    deleteStory(creada.id);
    await vi.waitFor(() => expect(historiasApi.remove).toHaveBeenCalledWith(creada.id));
    expect(historiasApi.save).toHaveBeenCalledWith(expect.objectContaining({ id: creada.id, title: 'Nueva' }));
  });

  it('la HU aprobada por el flujo se envía a la base y sobrevive a la siguiente sincronización', async () => {
    const aprobada = { id: '7c1d2e3f-4a5b-4c6d-8e7f-9a0b1c2d3e4f', title: 'Aprobada', status: 'aprobada', createdAt: '2026-11-26' };
    guardarHistoria(aprobada);
    expect(getStoredStories()).toEqual([aprobada]);
    // La base devuelve lo que se le envió: la sincronización espera la cola de escritura antes de leer.
    historiasApi.list.mockImplementation(async () => historiasApi.save.mock.calls.map(([historia]) => historia));
    await sincronizarHistorias();
    expect(historiasApi.save).toHaveBeenCalledWith(aprobada);
    expect(getStoredStories()).toEqual([aprobada]);
  });

  it('guardarHistoria reemplaza la copia existente con el mismo identificador', () => {
    const id = '7c1d2e3f-4a5b-4c6d-8e7f-9a0b1c2d3e4f';
    guardarHistoria({ id, title: 'Antes' });
    guardarHistoria({ id, title: 'Después' });
    expect(getStoredStories()).toEqual([{ id, title: 'Después' }]);
  });

  it('una lectura de la base que empezó antes de guardar no borra la HU recién guardada', async () => {
    const aprobada = { id: '7c1d2e3f-4a5b-4c6d-8e7f-9a0b1c2d3e4f', title: 'Recién aprobada', createdAt: '2026-11-26' };
    let lectura = 0;
    historiasApi.list.mockImplementation(async () => {
      lectura += 1;
      if (lectura === 1) {
        guardarHistoria(aprobada); // se guarda mientras la primera lectura está en curso
        return [];
      }
      return historiasApi.save.mock.calls.map(([historia]) => historia);
    });
    await sincronizarHistorias();
    expect(lectura).toBe(2);
    expect(getStoredStories()).toEqual([aprobada]);
  });
});
