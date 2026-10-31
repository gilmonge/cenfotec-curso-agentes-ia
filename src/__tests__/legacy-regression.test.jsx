import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import App from '../App.jsx';
import { INITIAL_USER_STORIES } from './fixtures/historiasEjemplo.js';

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

describe('legacy regression (Historias de Usuario)', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('historias_usuario_prototipo', JSON.stringify(INITIAL_USER_STORIES));
  });

  afterEach(() => cleanup());

  it.each([
    ['/', /Panel de Historias de Usuario/i],
    ['/historias', /^Historias de Usuario$/i],
    ['/historias/nueva', /Creación de Historia de Usuario/i],
    ['/historias/HU-101', /HU-101/],
    ['/historias/HU-101/editar', /Editar Historia HU-101/i],
    ['/skills', /Dashboard de Skills/],
    ['/ayuda', /Centro de Ayuda y Documentación/i],
    ['/lecciones', /Lecciones y checklist de vacíos/i],
  ])('keeps page and navigation available at %s', async (path, heading) => {
    renderAt(path);
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  it('keeps the dashboard action navigating to the existing Stepper', async () => {
    const user = userEvent.setup();
    renderAt('/');
    await user.click(screen.getByRole('button', { name: /^Crear$/i }));
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

  it('keeps the Stepper on step 1 and explains the problem when the agent backend is unreachable', async () => {
    const user = userEvent.setup();
    renderAt('/historias/nueva');
    await user.type(screen.getByLabelText(/Nombre del requerimiento/i), 'Consulta ficticia');
    await user.type(screen.getByLabelText(/Descripción o información de negocio/i), 'Revisar una regla de ejemplo.');
    await user.click(screen.getByRole('button', { name: /Analizar Requerimiento/i }));
    expect((await screen.findAllByText(/El agente no responde|No se pudo completar el análisis/i)).length).toBeGreaterThan(0);
    expect(screen.getByText(/Paso 1/)).toBeInTheDocument();
  });

  it('edit page shows one section at a time through its tabs and keeps what was typed', async () => {
    const user = userEvent.setup();
    renderAt('/historias/HU-101/editar');
    const primera = screen.getByRole('tab', { name: /Requerimiento inicial/i });
    expect(primera).toHaveAttribute('aria-selected', 'true');
    const titulo = screen.getByLabelText(/Título del Requerimiento/i);
    await user.type(titulo, ' extra');
    await user.click(screen.getByRole('tab', { name: /Historia de usuario/i }));
    expect(primera).toHaveAttribute('aria-selected', 'false');
    await user.click(primera);
    expect(screen.getByLabelText(/Título del Requerimiento/i)).toHaveValue(`${titulo.value}`);
    expect(titulo.value.endsWith(' extra')).toBe(true);
  });

  it('does not mutate preexisting storage when the dashboard mounts or unmounts', async () => {
    localStorage.setItem('legacy_other_key', 'keep-this-value');
    const before = Object.fromEntries(Object.keys(localStorage).map((key) => [key, localStorage.getItem(key)]));
    const view = renderAt('/');
    await waitFor(() => expect(screen.getByRole('heading', { name: /Panel de Historias de Usuario/i })).toBeInTheDocument());
    view.unmount();
    expect(Object.fromEntries(Object.keys(localStorage).map((key) => [key, localStorage.getItem(key)]))).toEqual(before);
  });

  it('defines the Proyecto Contexto palette tokens and keeps button text readable (WCAG AA)', () => {
    const variables = readFileSync(resolve(process.cwd(), 'src/styles/_variables.scss'), 'utf8').toLowerCase();
    for (const token of ['#f36c21', '#6f3fa0', '#333333', '#f4f4f4', '#d93025', '#2e7d32']) {
      expect(variables).toContain(token);
    }
    expect(contrastRatio('#1a1a1a', '#f36c21')).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio('#1a1a1a', '#f77f3a')).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio('#ffffff', '#6f3fa0')).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio('#c2410c', '#ffffff')).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio('#333333', '#f4f4f4')).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio('#ffffff', '#d93025')).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio('#ffffff', '#2e7d32')).toBeGreaterThanOrEqual(4.5);
  });

  it('defines phone, tablet and desktop chat layout rules', () => {
    const analystChatStyles = readFileSync(resolve(process.cwd(), 'src/styles/_analyst-chat.scss'), 'utf8');
    expect(analystChatStyles).toMatch(/max-width:\s*768px/);
    expect(analystChatStyles).toMatch(/max-width:\s*600px/);
    expect(analystChatStyles).toMatch(/calc\(100vw\s*-\s*1\.5rem\)/);
    expect(analystChatStyles).toMatch(/prefers-reduced-motion/);
  });

  it('keeps chat text and status colors above WCAG AA contrast in light and dark themes', () => {
    const theme = readFileSync(resolve(process.cwd(), 'src/styles/_theme.scss'), 'utf8');
    const [lightBlock, darkBlock] = theme.split(":root[data-theme='dark']");
    const token = (block, name) => new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`).exec(block)[1];
    const pairs = [
      ['--color-text-secondary', '--color-bg'],
      ['--color-text-secondary', '--color-surface'],
      ['--color-success-text', '--color-surface'],
      ['--color-warning-text', '--color-surface'],
      ['--color-danger-text', '--color-surface'],
      ['--color-text-primary', '--color-surface-hover'],
      ['--color-text-muted', '--color-surface'],
      ['--color-secondary-text', '--color-surface'],
    ];
    for (const [foreground, background] of pairs) {
      for (const block of [lightBlock, darkBlock]) {
        expect(contrastRatio(token(block, foreground), token(block, background))).toBeGreaterThanOrEqual(4.5);
      }
    }
    expect(contrastRatio('#ffffff', '#6f3fa0')).toBeGreaterThanOrEqual(4.5);
  });
});
