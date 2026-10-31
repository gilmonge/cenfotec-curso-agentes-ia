import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AsistenteAyudaComponent } from '../AsistenteAyudaComponent';
import { AyudaComponent } from '../../Ayuda/AyudaComponent';
import { buscarPregunta } from '../../../data/ayudaChat';

const abrir = async (user) => {
  render(<AsistenteAyudaComponent />);
  await user.click(screen.getByRole('button', { name: 'Abrir chat de ayuda' }));
  return screen.getByRole('dialog', { name: 'Chat de ayuda' });
};

describe('chat de ayuda sin modelo', () => {
  it('abre con preguntas sugeridas y responde con texto fijo y pasos', async () => {
    const user = userEvent.setup();
    const panel = await abrir(user);
    await user.click(within(panel).getByRole('button', { name: '¿Cómo creo una historia?' }));
    const registro = within(panel).getByRole('log');
    expect(within(registro).getAllByRole('listitem').length).toBeGreaterThanOrEqual(5);
    expect(registro).toHaveTextContent(/Nueva Historia/);
  });

  it('explica que el código no es el identificador técnico', async () => {
    const user = userEvent.setup();
    const panel = await abrir(user);
    await user.click(within(panel).getByRole('button', { name: '¿Qué es el código de la HU?' }));
    expect(within(panel).getByRole('log')).toHaveTextContent(/HU-CODIGO-001/);
    expect(within(panel).getByRole('log')).toHaveTextContent(/GUID/);
  });

  it('busca por palabra clave y avisa cuando no entiende', async () => {
    const user = userEvent.setup();
    const panel = await abrir(user);
    await user.type(within(panel).getByLabelText('Escriba una palabra clave'), 'criterios');
    await user.click(within(panel).getByRole('button', { name: 'Enviar' }));
    expect(within(panel).getByRole('log')).toHaveTextContent(/Dado que/);
    await user.type(within(panel).getByLabelText('Escriba una palabra clave'), 'zzzz qqqq');
    await user.click(within(panel).getByRole('button', { name: 'Enviar' }));
    expect(within(panel).getByRole('log')).toHaveTextContent(/No tengo una respuesta fija/);
    expect(buscarPregunta('')).toBeNull();
  });

  it('se cierra desde el botón de cierre', async () => {
    const user = userEvent.setup();
    const panel = await abrir(user);
    await user.click(within(panel).getByRole('button', { name: 'Cerrar chat de ayuda' }));
    expect(screen.queryByRole('dialog', { name: 'Chat de ayuda' })).not.toBeInTheDocument();
  });
});

describe('página de Ayuda', () => {
  it('explica el asistente, las acciones, el agente, las tecnologías, lo pendiente y el equipo', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><AyudaComponent /></MemoryRouter>);
    expect(screen.getByText('¿Cómo funciona el Asistente IA?')).toBeInTheDocument();
    expect(screen.getByText(/Paso 5 — Aprobación del Product Owner/)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Acciones sobre una HU/ }));
    ['Ver detalle', 'Editar', 'Solicitar cambio (solo HU aprobada)', 'Descargar', 'Eliminar'].forEach((titulo) => {
      expect(screen.getByRole('heading', { name: titulo })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /El agente Analista/ }));
    expect(screen.getByRole('heading', { name: 'El agente que trabaja en el sistema' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Qué no hace' })).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Ejemplo de HU generada/ }));
    expect(screen.getByRole('img', { name: /historia de usuario generada/i })).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Tecnologías/ }));
    expect(screen.getByText(/FastAPI/)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Por definir/ }));
    expect(screen.getByRole('heading', { name: 'Flujo de aprobación' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Roles y permisos' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Usuarios e inicio de sesión' })).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Equipo/ }));
    const nombres = screen.getAllByRole('listitem').map((item) => item.textContent);
    expect(nombres).toEqual(['Allam Fernandez', 'Gilberth Monge', 'Yuvania Castillo']);
  });

  it('no mantiene secciones antiguas de la Ayuda', () => {
    render(<MemoryRouter><AyudaComponent /></MemoryRouter>);
    expect(screen.queryByText(/Edición mediante Accordion/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Preguntas Frecuentes/)).not.toBeInTheDocument();
  });
});
