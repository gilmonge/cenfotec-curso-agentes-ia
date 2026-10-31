import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../../App.jsx';
import { AsistenteAnalistaComponent } from '../AsistenteAnalistaComponent';
import { PanelAsistenteComponent } from '../PanelAsistenteComponent';
import { MarkdownAsistenteComponent, safeMarkdownUrl } from '../MarkdownAsistenteComponent';
import { analystApi } from '../../../services/analystApi.js';

vi.mock('../../../services/analystApi.js', () => ({
  analystApi: {
    getHealth: vi.fn().mockResolvedValue({ status: 'degraded', checks: {} }),
    createConversation: vi.fn().mockResolvedValue({
      conversation_id: '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
    }),
    sendMessage: vi.fn(),
    cancelTurn: vi.fn(),
    resetConversation: vi.fn(),
    deleteConversation: vi.fn(),
  },
}));

const ROUTES = [
  '/',
  '/historias',
  '/historias/nueva',
  '/historias/HU-101',
  '/historias/HU-101/editar',
  '/skills',
  '/ayuda',
];

function validResponse(conversationId, requestId) {
  return {
    conversation_id: conversationId,
    request_id: requestId,
    turn_id: '2a5b7c9d-1e3f-4a6b-8c0d-2e4f6a8b0c1d',
    estado: 'completado',
    respuesta_markdown: 'Respuesta de prueba aislada.',
    analisis: { conocida: [], faltante: [], supuesta: [], ambigua: [] },
    preguntas: [],
    fuentes_consultadas: [],
    listo_para_redactor: true,
    limitaciones: [],
    duracion_ms: 2,
    prompt_version: '1.0.0',
  };
}

// El chat flotante ya no está montado en el layout (el agente se integra al flujo de pasos),
// pero el componente sigue en el repositorio y se prueba montándolo junto a la aplicación.
function renderAt(path) {
  window.history.replaceState({}, '', path);
  return render(<><App /><AsistenteAnalistaComponent /></>);
}

describe('AnalystChat shell', () => {
  beforeEach(() => {
    localStorage.clear();
    analystApi.getHealth.mockReset();
    analystApi.getHealth.mockResolvedValue({ status: 'degraded', checks: {} });
    analystApi.createConversation.mockReset();
    analystApi.createConversation.mockResolvedValue({
      conversation_id: '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
    });
    analystApi.sendMessage.mockReset();
    analystApi.cancelTurn.mockReset();
    analystApi.resetConversation.mockReset();
    analystApi.deleteConversation.mockReset();
  });

  afterEach(() => cleanup());

  it.each(ROUTES)('exposes one launcher on route %s', async (path) => {
    renderAt(path);
    expect(await screen.findByRole('button', { name: /abrir chat del agente analista/i })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /abrir chat del agente analista/i })).toHaveLength(1);
  });

  it('opens and closes without creating browser storage for chat state', async () => {
    const user = userEvent.setup();
    localStorage.setItem('historias_usuario_prototipo', JSON.stringify([{ id: 'HU-TEST', title: 'Dato previo' }]));
    localStorage.setItem('legacy_preexisting', 'preservar');
    const before = Object.fromEntries(Object.keys(localStorage).map((key) => [key, localStorage.getItem(key)]));

    const view = renderAt('/');
    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    expect(await screen.findByRole('dialog', { name: /agente analista/i })).toBeVisible();
    await user.click(screen.getByRole('button', { name: /cerrar chat/i }));
    view.unmount();

    expect(Object.fromEntries(Object.keys(localStorage).map((key) => [key, localStorage.getItem(key)]))).toEqual(before);
    expect(Object.keys(localStorage).some((key) => /analyst|chat/i.test(key))).toBe(false);
  });

  it('closes with Escape and returns focus to the launcher', async () => {
    const user = userEvent.setup();
    renderAt('/ayuda');
    const launcher = await screen.findByRole('button', { name: /abrir chat del agente analista/i });
    await user.click(launcher);
    expect(screen.getByRole('button', { name: /cerrar chat/i })).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog', { name: /agente analista/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /abrir chat del agente analista/i })).toHaveFocus();
  });

  it('follows a new message when the reader is within 80 pixels of the end', () => {
    const initial = [{ id: 'm1', role: 'assistant', text: 'Primer mensaje' }];
    const view = render(<PanelAsistenteComponent open messages={initial} />);
    const log = screen.getByRole('log', { name: /mensajes del chat/i });
    Object.defineProperties(log, {
      clientHeight: { configurable: true, value: 300 },
      scrollHeight: { configurable: true, value: 1000 },
    });
    log.scrollTop = 650;
    fireEvent.scroll(log);

    Object.defineProperty(log, 'scrollHeight', { configurable: true, value: 1100 });
    view.rerender(<PanelAsistenteComponent open messages={[...initial, { id: 'm2', role: 'user', text: 'Nuevo mensaje' }]} />);
    expect(log.scrollTop).toBe(1100);
    expect(screen.queryByRole('button', { name: /ir al último mensaje/i })).not.toBeInTheDocument();
  });

  it('preserves a prior position above 80 pixels and offers a jump to the end', async () => {
    const user = userEvent.setup();
    const initial = [{ id: 'm1', role: 'assistant', text: 'Primer mensaje' }];
    const view = render(<PanelAsistenteComponent open messages={initial} />);
    const log = screen.getByRole('log', { name: /mensajes del chat/i });
    Object.defineProperties(log, {
      clientHeight: { configurable: true, value: 300 },
      scrollHeight: { configurable: true, value: 1000 },
    });
    log.scrollTop = 600;
    fireEvent.scroll(log);

    Object.defineProperty(log, 'scrollHeight', { configurable: true, value: 1100 });
    view.rerender(<PanelAsistenteComponent open messages={[...initial, { id: 'm2', role: 'user', text: 'Nuevo mensaje' }]} />);
    expect(log.scrollTop).toBe(600);
    const jumpButton = screen.getByRole('button', { name: /ir al último mensaje/i });
    await user.click(jumpButton);
    expect(log.scrollTop).toBe(1100);
    expect(jumpButton).not.toBeInTheDocument();
  });

  it('does not change scroll position when only health state changes', () => {
    const messages = [{ id: 'm1', role: 'assistant', text: 'Mensaje previo' }];
    const view = render(<PanelAsistenteComponent open messages={messages} healthStatus="ready" />);
    const log = screen.getByRole('log', { name: /mensajes del chat/i });
    Object.defineProperties(log, {
      clientHeight: { configurable: true, value: 300 },
      scrollHeight: { configurable: true, value: 1000 },
    });
    log.scrollTop = 500;
    fireEvent.scroll(log);
    view.rerender(<PanelAsistenteComponent open messages={messages} healthStatus="degraded" />);
    expect(log.scrollTop).toBe(500);
  });

  it('sends a real chat turn through the backend API and renders its structured response', async () => {
    const user = userEvent.setup();
    analystApi.sendMessage.mockResolvedValue({
      conversation_id: '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
      request_id: '9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d',
      turn_id: '2a5b7c9d-1e3f-4a6b-8c0d-2e4f6a8b0c1d',
      estado: 'completado',
      respuesta_markdown: 'Hay dos datos por confirmar.',
      analisis: { conocida: ['Solicitud de póliza'], faltante: ['Plazo'], supuesta: [], ambigua: [] },
      preguntas: [{ question_id: 'q1', categoria: 'Validaciones', pregunta: '¿Cuál es el plazo?', estado: 'pendiente', created_turn_id: '2a5b7c9d-1e3f-4a6b-8c0d-2e4f6a8b0c1d', updated_turn_id: null }],
      fuentes_consultadas: [{ nombre: 'consultar_glosario', resultados: 2, duracion_ms: 8 }],
      limitaciones: [],
      listo_para_redactor: false,
      duracion_ms: 1250,
      prompt_version: '1.0.0',
    });
    renderAt('/');

    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    const composer = screen.getByRole('textbox', { name: /escribe tu requerimiento/i });
    await waitFor(() => expect(composer).toBeEnabled());
    await user.type(composer, 'Analizar solicitud de póliza');
    await user.click(screen.getByRole('button', { name: /enviar/i }));

    expect(composer).toHaveValue('');
    expect(await screen.findByText('Hay dos datos por confirmar.')).toBeInTheDocument();
    expect(screen.getByText('Plazo')).toBeInTheDocument();
    expect(screen.getByText(/¿Cuál es el plazo\?/)).toBeInTheDocument();
    expect(screen.getByText(/Qué se debe revisar/)).toBeInTheDocument();
    expect(screen.getByText(/Pendiente de aclaraciones/)).toBeInTheDocument();
    expect(screen.getByText(/consultar_glosario: 2 resultados · 8 ms/)).toBeInTheDocument();
    expect(screen.getByText(/Duración: 1250 ms/)).toBeInTheDocument();
    expect(analystApi.createConversation).toHaveBeenCalledOnce();
    expect(analystApi.sendMessage).toHaveBeenCalledWith(
      '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
      expect.objectContaining({ message: 'Analizar solicitud de póliza' }),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it('cancels through FastAPI and aborts the pending browser request', async () => {
    const user = userEvent.setup();
    let requestSignal;
    analystApi.cancelTurn.mockResolvedValue({ canceled: true });
    analystApi.sendMessage.mockImplementation((_conversationId, _payload, options) => {
      requestSignal = options.signal;
      return new Promise((_resolve, reject) => {
        requestSignal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
      });
    });
    renderAt('/');

    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    const composer = screen.getByRole('textbox', { name: /escribe tu requerimiento/i });
    await waitFor(() => expect(composer).toBeEnabled());
    await user.type(composer, 'Consulta de prueba');
    await user.click(screen.getByRole('button', { name: /enviar/i }));
    await user.click(await screen.findByRole('button', { name: /cancelar/i }));

    await waitFor(() => expect(requestSignal.aborted).toBe(true));
    expect(analystApi.cancelTurn).toHaveBeenCalledWith(
      '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
      expect.any(String),
    );
    expect(screen.queryByText('Analizando con el agente…')).not.toBeInTheDocument();
  });

  it('ignores a successful response that arrives after cancellation', async () => {
    const user = userEvent.setup();
    let finishTurn;
    let requestSignal;
    analystApi.cancelTurn.mockResolvedValue({ canceled: true });
    analystApi.sendMessage.mockImplementation((_conversationId, _payload, options) => {
      requestSignal = options.signal;
      return new Promise((resolve) => { finishTurn = resolve; });
    });
    renderAt('/');

    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    const composer = screen.getByRole('textbox', { name: /escribe tu requerimiento/i });
    await waitFor(() => expect(composer).toBeEnabled());
    await user.type(composer, 'Discard late result');
    await user.click(screen.getByRole('button', { name: /enviar/i }));
    await waitFor(() => expect(analystApi.sendMessage).toHaveBeenCalledOnce());

    await user.click(await screen.findByRole('button', { name: /cancelar/i }));
    expect(requestSignal.aborted).toBe(true);
    finishTurn(validResponse(
      '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
      analystApi.sendMessage.mock.calls[0][1].request_id,
    ));

    await waitFor(() => expect(composer).toHaveValue('Discard late result'));
    expect(screen.queryByText('Respuesta de prueba aislada.')).not.toBeInTheDocument();
  });

  it('counts Unicode code points and submits at most one active turn', async () => {
    const user = userEvent.setup();
    let finishTurn;
    analystApi.sendMessage.mockImplementation(() => new Promise((resolve) => { finishTurn = resolve; }));
    renderAt('/');
    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    const composer = screen.getByRole('textbox', { name: /escribe tu requerimiento/i });
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: '😀'.repeat(4001) } });
    expect(screen.getByText('4001/4000')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /enviar/i })).toBeDisabled();
    fireEvent.change(composer, { target: { value: '😀'.repeat(4000) } });
    expect(screen.getByText('4000/4000')).toBeInTheDocument();
    const form = composer.closest('form');
    fireEvent.submit(form);
    fireEvent.submit(form);

    await waitFor(() => expect(analystApi.sendMessage).toHaveBeenCalledOnce());
    expect(analystApi.sendMessage.mock.calls[0][1].message).toBe('😀'.repeat(4000));
    finishTurn(validResponse(
      '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f',
      analystApi.sendMessage.mock.calls[0][1].request_id,
    ));
    expect(await screen.findByText('Respuesta de prueba aislada.')).toBeInTheDocument();
    expect(analystApi.sendMessage).toHaveBeenCalledOnce();
  });

  it('clears the composer immediately and retries a failed 429 message without adding a duplicate', async () => {
    const user = userEvent.setup();
    analystApi.sendMessage
      .mockRejectedValueOnce({
        code: 'OPENCODE_RATE_LIMITED',
        status: 429,
        retryable: true,
        retryAt: new Date(Date.now() + 60_000).toISOString(),
      })
      .mockImplementationOnce((conversationId, payload) => Promise.resolve(validResponse(conversationId, payload.request_id)));
    renderAt('/');

    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    const composer = screen.getByRole('textbox', { name: /escribe tu requerimiento/i });
    await waitFor(() => expect(composer).toBeEnabled());
    await user.type(composer, 'Solicitud para reintentar');
    await user.click(screen.getByRole('button', { name: /enviar/i }));
    expect(composer).toHaveValue('');
    expect(await screen.findByText(/dentro de (?:1 minuto|\d+ segundos)/)).toBeInTheDocument();
    expect(screen.getByText('Cuota agotada (429)')).toBeInTheDocument();
    const sentMessage = screen.getByText('Solicitud para reintentar');
    const firstRequestId = analystApi.sendMessage.mock.calls[0][1].request_id;

    await user.click(screen.getByRole('button', { name: /reintentar este mensaje/i }));
    expect(await screen.findByText('Respuesta de prueba aislada.')).toBeInTheDocument();
    expect(analystApi.sendMessage.mock.calls[1][1].request_id).not.toBe(firstRequestId);
    expect(analystApi.sendMessage.mock.calls[1][1].message).toBe('Solicitud para reintentar');
    expect(screen.getAllByText('Solicitud para reintentar')).toHaveLength(1);
    expect(sentMessage).toBeInTheDocument();
    expect(composer).toHaveValue('');
  });

  it('keeps one user message and the same request identity after a network error', async () => {
    const user = userEvent.setup();
    analystApi.sendMessage
      .mockRejectedValueOnce({ code: 'NETWORK_ERROR', retryable: true })
      .mockImplementationOnce((conversationId, payload) => Promise.resolve(validResponse(conversationId, payload.request_id)));
    renderAt('/');

    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    const composer = screen.getByRole('textbox', { name: /escribe tu requerimiento/i });
    await waitFor(() => expect(composer).toBeEnabled());
    await user.type(composer, 'Reintento de red');
    await user.click(screen.getByRole('button', { name: /enviar/i }));
    expect(await screen.findByRole('button', { name: /reintentar este mensaje/i })).toBeInTheDocument();
    const requestId = analystApi.sendMessage.mock.calls[0][1].request_id;

    await user.click(screen.getByRole('button', { name: /reintentar este mensaje/i }));
    expect(await screen.findByText('Respuesta de prueba aislada.')).toBeInTheDocument();
    expect(analystApi.sendMessage.mock.calls[1][1].request_id).toBe(requestId);
    expect(screen.getAllByText('Reintento de red')).toHaveLength(1);
    expect(composer).toHaveValue('');
  });

  it('reports backend connectivity separately from unverified model generation capability', async () => {
    const user = userEvent.setup();
    analystApi.getHealth.mockResolvedValue({
      status: 'ready',
      timeout_seconds: 90,
      checks: { opencode: { status: 'ok' }, mcp: { status: 'ok' }, langfuse: { status: 'ok' } },
    });
    renderAt('/');

    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    expect(await screen.findByText('Backend conectado')).toBeInTheDocument();
    expect(screen.getByText('OpenCode Server conectado')).toBeInTheDocument();
    expect(screen.getByText('Generación del modelo sin verificar')).toBeInTheDocument();
  });

  it('distinguishes an OpenCode server outage from a connected backend', () => {
    render(<PanelAsistenteComponent
      open
      messages={[]}
      draft="Consulta"
      backendConnection="connected"
      health={{ status: 'unavailable', checks: { opencode: { status: 'unavailable' } } }}
    />);
    expect(screen.getByText('Backend conectado')).toBeInTheDocument();
    expect(screen.getByText('OpenCode Server desconectado')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /escribe tu requerimiento/i })).toBeDisabled();
  });

  it.each([
    ['model-unavailable', 'Modelo no disponible'],
    ['quota-exhausted', 'Cuota agotada (429)'],
    ['timeout', 'Timeout de 90 segundos'],
  ])('shows the generation state %s independently of backend health', (generationStatus, label) => {
    render(<PanelAsistenteComponent
      open
      messages={[]}
      health={{ status: 'ready', timeout_seconds: 90, checks: { opencode: { status: 'ok' } } }}
      backendConnection="connected"
      generationStatus={generationStatus}
    />);
    expect(screen.getByText('Backend conectado')).toBeInTheDocument();
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('shows a disconnected backend when health cannot be reached', () => {
    render(<PanelAsistenteComponent open messages={[]} backendConnection="disconnected" health={null} />);
    expect(screen.getByText('Backend desconectado')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /escribe tu requerimiento/i })).toBeDisabled();
  });

  it('starts a new conversation immediately and invalidates the active request', async () => {
    const user = userEvent.setup();
    let requestSignal;
    let finishReset;
    let finishRequest;
    let activePayload;
    analystApi.resetConversation.mockImplementation(() => new Promise((resolve) => { finishReset = resolve; }));
    analystApi.sendMessage.mockImplementation((_conversationId, payload, options) => {
      activePayload = payload;
      requestSignal = options.signal;
      return new Promise((resolve) => { finishRequest = resolve; });
    });
    renderAt('/');

    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    const composer = screen.getByRole('textbox', { name: /escribe tu requerimiento/i });
    await waitFor(() => expect(composer).toBeEnabled());
    await user.type(composer, 'Consulta en curso');
    await user.click(screen.getByRole('button', { name: /enviar/i }));
    await waitFor(() => expect(analystApi.sendMessage).toHaveBeenCalledOnce());

    await user.click(screen.getByRole('button', { name: /nuevo chat/i }));
    expect(analystApi.resetConversation).toHaveBeenCalledWith('3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f');
    expect(screen.queryByText('Consulta en curso')).not.toBeInTheDocument();
    expect(requestSignal.aborted).toBe(false);

    finishReset({ conversation_id: '4f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f' });
    await waitFor(() => expect(requestSignal.aborted).toBe(true));
    finishRequest(validResponse('3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f', activePayload.request_id));
    await waitFor(() => expect(screen.queryByText('Consulta en curso')).not.toBeInTheDocument());
    expect(screen.queryByText('Respuesta de prueba aislada.')).not.toBeInTheDocument();
  });

  it('keeps the conversation when the delete dialog is canceled', async () => {
    const user = userEvent.setup();
    renderAt('/');
    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    const trigger = screen.getByRole('button', { name: /eliminar conversación/i });
    await user.click(trigger);
    expect(screen.getByRole('alertdialog', { name: /eliminar conversación/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /conservar conversación/i })).toHaveFocus();
    await user.click(screen.getByRole('button', { name: /conservar conversación/i }));

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(analystApi.deleteConversation).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog', { name: /agente analista/i })).toBeVisible();
  });

  it('deletes a confirmed conversation and closes the chat', async () => {
    const user = userEvent.setup();
    analystApi.sendMessage.mockImplementationOnce((conversationId, payload) => Promise.resolve(validResponse(conversationId, payload.request_id)));
    analystApi.deleteConversation.mockResolvedValue(null);
    renderAt('/');
    await user.click(await screen.findByRole('button', { name: /abrir chat del agente analista/i }));
    const composer = screen.getByRole('textbox', { name: /escribe tu requerimiento/i });
    await waitFor(() => expect(composer).toBeEnabled());
    await user.type(composer, 'Contexto para borrar');
    await user.click(screen.getByRole('button', { name: /enviar/i }));
    expect(await screen.findByText('Respuesta de prueba aislada.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /eliminar conversación/i }));
    await user.click(screen.getByRole('button', { name: /^eliminar$/i }));

    await waitFor(() => expect(analystApi.deleteConversation).toHaveBeenCalledWith('3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f'));
    expect(screen.queryByText('Respuesta de prueba aislada.')).not.toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /abrir chat del agente analista/i })).toBeInTheDocument();
  });

  it('keeps send disabled while health is unavailable', async () => {
    const view = render(<PanelAsistenteComponent open messages={[]} health="unavailable" />);
    expect(screen.getByRole('button', { name: /enviar/i })).toBeDisabled();
    expect(screen.getByRole('textbox', { name: /escribe tu requerimiento/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /reintentar conexión/i })).toBeInTheDocument();
    view.unmount();
  });

  it.each([
    ['ready', 'Backend conectado', false],
    ['degraded', 'Backend conectado', false],
    ['unavailable', 'Backend conectado', true],
  ])('renders health state %s and gates the composer accordingly', (health, label, disabled) => {
    render(<PanelAsistenteComponent open messages={[]} draft="Consulta" health={health} />);
    expect(screen.getByRole('status')).toHaveTextContent(label);
    expect(screen.getByRole('textbox', { name: /escribe tu requerimiento/i }).disabled).toBe(disabled);
  });

  it('renders GFM but blocks raw HTML, active links, and remote images', () => {
    const { container } = render(
      <MarkdownAsistenteComponent content={'<script>alert(1)</script>\n\n[unsafe](javascript:alert(1))\n\n![remote](https://example.invalid/a.png)\n\n- [x] Revisado'} />,
    );
    expect(container.querySelector('script')).not.toBeInTheDocument();
    expect(container.querySelector('img')).not.toBeInTheDocument();
    expect(container.querySelector('a[href^="javascript:"]')).not.toBeInTheDocument();
    expect(screen.getByText('unsafe').tagName).toBe('SPAN');
    expect(screen.getByRole('checkbox')).toBeDisabled();
    expect(safeMarkdownUrl('data:text/html,alert(1)')).toBe('');
    expect(safeMarkdownUrl('blob:https://example.invalid/id')).toBe('');
    expect(safeMarkdownUrl('file:///private/document')).toBe('');
    expect(safeMarkdownUrl('JaVaScRiPt:alert(1)')).toBe('');
    expect(safeMarkdownUrl('#section')).toBe('#section');
  });

  it('keeps allowed external Markdown links isolated from the opener', () => {
    render(<MarkdownAsistenteComponent content="[Documentación](https://example.invalid/docs)" />);
    expect(screen.getByRole('link', { name: 'Documentación' })).toHaveAttribute('rel', 'noopener noreferrer');
    expect(screen.getByRole('link', { name: 'Documentación' })).toHaveAttribute('target', '_blank');
  });

  it.each([
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    '<iframe src="javascript:alert(1)"></iframe>',
    '[x](javascript:alert(1))',
    '[x](data:text/html,alert(1))',
    '[x](blob:https://example.invalid/id)',
    '[x](file:///private/document)',
    '[x](JaVaScRiPt:alert(1))',
    '![remote](https://example.invalid/remote.png)',
  ])('renders unsafe Markdown payload as inert text: %s', (payload) => {
    const view = render(<MarkdownAsistenteComponent content={payload} />);
    expect(view.container.querySelector('script, iframe, svg, img')).not.toBeInTheDocument();
    expect(view.container.querySelector('[onerror], [onload]')).not.toBeInTheDocument();
    expect(view.container.querySelector('a[href^="javascript:"], a[href^="data:"], a[href^="blob:"], a[href^="file:"]')).not.toBeInTheDocument();
    view.unmount();
  });
});
