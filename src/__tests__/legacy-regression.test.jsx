import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import App from '../App.jsx';
import { INITIAL_USER_STORIES } from '../data/mockData.js';

function renderAt(path) {
  window.history.replaceState({}, '', path);
  return render(<App />);
}

function contrastRatio(foreground, background) {
  const luminance = (hex) => {
    const normalized = hex.length === 4 ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}` : hex;
    const channels = normalized.slice(1).match(/.{2}/g).map((part) => parseInt(part, 16) / 255);
    const linear = channels.map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return (0.2126 * linear[0]) + (0.7152 * linear[1]) + (0.0722 * linear[2]);
  };
  const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

describe('legacy StoryCraft regression', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('storycraft_user_stories', JSON.stringify(INITIAL_USER_STORIES));
  });

  afterEach(() => cleanup());

  it.each([
    ['/', /Dashboard de Historias de Usuario/i],
    ['/historias', /^Historias de Usuario$/i],
    ['/historias/nueva', /Creación de Historia de Usuario/i],
    ['/historias/HU-101', /HU-101/],
    ['/historias/HU-101/editar', /Editar Historia HU-101/i],
    ['/skills', /Dashboard de Skills/],
    ['/ayuda', /Centro de Ayuda y Documentación/i],
  ])('keeps page and navigation available at %s', async (path, heading) => {
    renderAt(path);
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  it('keeps the dashboard action navigating to the existing Stepper', async () => {
    const user = userEvent.setup();
    renderAt('/');
    await user.click(screen.getByRole('button', { name: /Crear Historia con Stepper/i }));
    expect(await screen.findByRole('heading', { name: /Creación de Historia de Usuario/i })).toBeInTheDocument();
    expect(screen.getByText(/Paso 1/)).toBeInTheDocument();
  });

  it('keeps dashboard and story-list actions available', async () => {
    const user = userEvent.setup();
    renderAt('/');
    await user.click(screen.getByRole('button', { name: /Ver listado completo de historias/i }));
    expect(await screen.findByRole('heading', { name: /^Historias de Usuario$/i })).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText(/Buscar por título o código ID/i), 'HU-101');
    expect(screen.getAllByRole('button', { name: 'Ver' })).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: 'Ver' }));
    expect(await screen.findByRole('heading', { name: /HU-101/ })).toBeInTheDocument();
  });

  it('keeps the existing simulated analysis and Stepper navigation intact', async () => {
    const user = userEvent.setup();
    renderAt('/historias/nueva');
    await user.type(screen.getByLabelText(/Nombre del requerimiento/i), 'Consulta ficticia');
    await user.type(screen.getByLabelText(/Descripción o información de negocio/i), 'Revisar una regla de ejemplo.');
    await user.click(screen.getByRole('button', { name: /Analizar Requerimiento/i }));
    expect(await screen.findByText(/Análisis Completado/i, {}, { timeout: 4000 })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Preguntas de Aclaración/i }));
    expect(await screen.findByText(/Paso 3/)).toBeInTheDocument();
  });

  it('keeps Accordion sections independently expandable', async () => {
    const user = userEvent.setup();
    renderAt('/historias/HU-101/editar');
    const section = screen.getByRole('button', { name: /1\. Requerimiento Inicial/i });
    expect(section).toHaveAttribute('aria-expanded', 'true');
    await user.click(section);
    expect(section).toHaveAttribute('aria-expanded', 'false');
    await user.click(section);
    expect(section).toHaveAttribute('aria-expanded', 'true');
  });

  it('does not mutate preexisting storage when the dashboard mounts or unmounts', async () => {
    localStorage.setItem('legacy_other_key', 'keep-this-value');
    const before = Object.fromEntries(Object.keys(localStorage).map((key) => [key, localStorage.getItem(key)]));
    const view = renderAt('/');
    await waitFor(() => expect(screen.getByRole('heading', { name: /Dashboard de Historias de Usuario/i })).toBeInTheDocument());
    view.unmount();
    expect(Object.fromEntries(Object.keys(localStorage).map((key) => [key, localStorage.getItem(key)]))).toEqual(before);
  });

  it('defines phone, tablet and desktop chat layout rules', () => {
    const analystChatStyles = readFileSync(resolve(process.cwd(), 'src/styles/_analyst-chat.scss'), 'utf8');
    expect(analystChatStyles).toMatch(/max-width:\s*768px/);
    expect(analystChatStyles).toMatch(/max-width:\s*600px/);
    expect(analystChatStyles).toMatch(/calc\(100vw\s*-\s*1\.5rem\)/);
    expect(analystChatStyles).toMatch(/prefers-reduced-motion/);
  });

  it('keeps core chat text and status colors above WCAG AA contrast for normal text', () => {
    const analystChatStyles = readFileSync(resolve(process.cwd(), 'src/styles/_analyst-chat.scss'), 'utf8');
    const pairs = [
      ['#fff', '#1d4ed8'],
      ['#475569', '#f8fafc'],
      ['#166534', '#fff'],
      ['#92400e', '#fff'],
      ['#b91c1c', '#fff'],
      ['#334155', '#fff'],
    ];
    for (const [foreground, background] of pairs) {
      expect(analystChatStyles.toLowerCase()).toContain(foreground);
      expect(analystChatStyles.toLowerCase()).toContain(background);
      expect(contrastRatio(foreground, background)).toBeGreaterThanOrEqual(4.5);
    }
  });
});
