import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../services/repositorioApi', () => ({
  historiasApi: { list: vi.fn(), save: vi.fn(), remove: vi.fn() },
}));

import { historiasApi } from '../../services/repositorioApi';
import { addStory, deleteStory, getStoredStories, habilitarSincronizacion, sincronizarHistorias } from '../storage';

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
});
