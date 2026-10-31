import React from 'react';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../../App.jsx';
import { repositorioApi } from '../../../services/repositorioApi.js';
import { INITIAL_USER_STORIES } from '../../../__tests__/fixtures/historiasEjemplo.js';

vi.mock('../../../services/analystApi.js', () => ({
  request: vi.fn(),
  analystApi: {
    getHealth: vi.fn(), createConversation: vi.fn(), sendMessage: vi.fn(),
    cancelTurn: vi.fn(), resetConversation: vi.fn(), deleteConversation: vi.fn(),
  },
}));

vi.mock('../../../services/repositorioApi.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    repositorioApi: {
      saveStory: vi.fn(), listStories: vi.fn(), registerChange: vi.fn(), listChanges: vi.fn(),
      listLessons: vi.fn(), decideLesson: vi.fn(), deleteStory: vi.fn(),
    },
  };
});

const KEY = 'historias_usuario_prototipo';
const SYNCED = {
  ...INITIAL_USER_STORIES[0], id: 'HU-777', number: 'HU-777', title: 'Historia aprobada y sincronizada',
  status: 'aprobada', repositorySynced: true,
};

const storedIds = () => JSON.parse(localStorage.getItem(KEY) ?? '[]').map((story) => story.id);

function renderAt(path) {
  window.history.replaceState({}, '', path);
  return render(<App />);
}

describe('eliminar historias', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem(KEY, JSON.stringify([...INITIAL_USER_STORIES, SYNCED]));
    vi.clearAllMocks();
    repositorioApi.deleteStory.mockResolvedValue(null);
  });
  afterEach(() => cleanup());

  it('elimina desde el listado una historia local tras confirmar en el diálogo, sin tocar el repositorio', async () => {
    const user = userEvent.setup();
    renderAt('/historias');
    await user.click(await screen.findByRole('button', { name: /Eliminar historia HU-101/i }));

    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByText(/Esta acción no se puede deshacer/i)).toBeInTheDocument();
    expect(within(dialog).queryByText(/Repositorio de HU/i)).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: /^Eliminar historia$/i }));

    await waitFor(() => expect(storedIds()).not.toContain('HU-101'));
    expect(repositorioApi.deleteStory).not.toHaveBeenCalled();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('conserva la historia si se cancela o se pulsa Escape', async () => {
    const user = userEvent.setup();
    renderAt('/historias');
    await user.click(await screen.findByRole('button', { name: /Eliminar historia HU-101/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: /Conservar historia/i }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Eliminar historia HU-101/i }));
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(storedIds()).toContain('HU-101');
  });

  it('una historia aprobada también se elimina del Repositorio de HU', async () => {
    const user = userEvent.setup();
    renderAt('/historias');
    await user.click(await screen.findByRole('button', { name: /Eliminar historia HU-777/i }));
    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByText(/También se eliminará del Repositorio de HU/i)).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: /^Eliminar historia$/i }));

    await waitFor(() => expect(repositorioApi.deleteStory).toHaveBeenCalledWith('HU-777'));
    await waitFor(() => expect(storedIds()).not.toContain('HU-777'));
  });

  it('si el repositorio no responde, no borra nada y explica el motivo', async () => {
    const error = Object.assign(new Error('sin red'), { code: 'NETWORK_ERROR' });
    repositorioApi.deleteStory.mockRejectedValueOnce(error);
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const user = userEvent.setup();
    renderAt('/historias');
    await user.click(await screen.findByRole('button', { name: /Eliminar historia HU-777/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: /^Eliminar historia$/i }));

    expect(await screen.findByText(/No hay conexión con el backend local/i)).toBeInTheDocument();
    expect(storedIds()).toContain('HU-777');
  });

  it('si el repositorio ya no la tiene, igual se elimina localmente', async () => {
    repositorioApi.deleteStory.mockRejectedValueOnce(Object.assign(new Error('no existe'), { code: 'REPOSITORY_NOT_FOUND' }));
    const user = userEvent.setup();
    renderAt('/historias');
    await user.click(await screen.findByRole('button', { name: /Eliminar historia HU-777/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: /^Eliminar historia$/i }));
    await waitFor(() => expect(storedIds()).not.toContain('HU-777'));
  });

  it('el detalle no ofrece acciones: se elimina desde el listado', async () => {
    renderAt('/historias/HU-101');
    expect(await screen.findByRole('button', { name: /Volver/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Eliminar$/i })).not.toBeInTheDocument();
  });

  it('permite cambiar entre cuadros y lista, recuerda la vista y sigue eliminando', async () => {
    const user = userEvent.setup();
    renderAt('/historias');
    const lista = await screen.findByRole('button', { name: /Lista/i });
    expect(lista).toHaveAttribute('aria-pressed', 'false');
    await user.click(lista);
    expect(lista).toHaveAttribute('aria-pressed', 'true');
    expect(localStorage.getItem('historias_usuario_vista')).toBe('lista');
    expect(document.querySelector('.story-list')).not.toBeNull();
    expect(document.querySelector('.grid-3')).toBeNull();

    await user.click(screen.getByRole('button', { name: /Eliminar historia HU-777/i }));
    await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: /^Eliminar historia$/i }));
    await waitFor(() => expect(storedIds()).not.toContain('HU-777'));

    await user.click(screen.getByRole('button', { name: /Cuadros/i }));
    expect(document.querySelector('.grid-3')).not.toBeNull();
  });
});
