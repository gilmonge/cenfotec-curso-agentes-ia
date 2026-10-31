import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { EnvolturaPaginaComponent } from '../EnvolturaPaginaComponent';
import { CLAVE_ALMACENAMIENTO_TEMA } from '../../../hooks/useTema';

const renderLayout = () =>
  render(
    <MemoryRouter>
      <Routes>
        <Route element={<EnvolturaPaginaComponent />}>
          <Route index element={<p>Contenido</p>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );

describe('MainLayout', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('no muestra las pestañas Skills ni Lecciones en el menú', () => {
    renderLayout();
    const nav = screen.getByRole('navigation');
    expect(nav).not.toHaveTextContent(/skills/i);
    expect(nav).not.toHaveTextContent(/lecciones/i);
    expect(nav).toHaveTextContent('Dashboard');
    expect(nav).toHaveTextContent('Nueva Historia');
    expect(nav).toHaveTextContent('Ayuda');
  });

  it('muestra en el pie de página los derechos reservados con el año y la versión configurados', () => {
    renderLayout();
    expect(screen.getByRole('contentinfo')).toHaveTextContent(/^HISTORIAS DE USUARIO ® Derechos Reservados \d{4} - V\.\S+$/);
  });

  it('alterna entre modo claro y oscuro, lo aplica al documento y lo recuerda', async () => {
    const user = userEvent.setup();
    renderLayout();
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');

    await user.click(screen.getByRole('button', { name: /cambiar a modo oscuro/i }));
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(localStorage.getItem(CLAVE_ALMACENAMIENTO_TEMA)).toBe('dark');

    await user.click(screen.getByRole('button', { name: /cambiar a modo claro/i }));
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(localStorage.getItem(CLAVE_ALMACENAMIENTO_TEMA)).toBe('light');
  });

  it('arranca en oscuro si la persona ya lo había elegido', () => {
    localStorage.setItem(CLAVE_ALMACENAMIENTO_TEMA, 'dark');
    renderLayout();
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(screen.getByRole('button', { name: /cambiar a modo claro/i })).toBeInTheDocument();
  });

  it('permite identificarse y muestra el nombre en el encabezado', async () => {
    const user = userEvent.setup();
    renderLayout();
    await user.click(screen.getByRole('button', { name: /Identificarse/i }));
    await user.type(screen.getByLabelText(/^Nombre/), 'Persona Uno');
    await user.click(screen.getByRole('button', { name: /Guardar nombre/i }));
    expect(await screen.findByRole('button', { name: /Usuario: Persona Uno/i })).toBeInTheDocument();
    expect(localStorage.getItem('historias_usuario_nombre')).toBe('Persona Uno');
  });
});
