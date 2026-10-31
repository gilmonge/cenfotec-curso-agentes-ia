import React from 'react';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../../App.jsx';
import { analystApi } from '../../../services/analystApi.js';
import { repositorioApi } from '../../../services/repositorioApi.js';

vi.mock('../../../services/analystApi.js', () => ({
  request: vi.fn(),
  analystApi: {
    getHealth: vi.fn(),
    createConversation: vi.fn(),
    sendMessage: vi.fn(),
    cancelTurn: vi.fn(),
    resetConversation: vi.fn(),
    deleteConversation: vi.fn(),
  },
}));

vi.mock('../../../services/repositorioApi.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    repositorioApi: {
      saveStory: vi.fn(),
      listStories: vi.fn(),
      registerChange: vi.fn(),
      listChanges: vi.fn(),
      listLessons: vi.fn(),
      decideLesson: vi.fn(),
    },
  };
});

const CONVERSATION_ID = '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f';

function agentResponse(payload, turn, { ready, questions }) {
  return {
    conversation_id: CONVERSATION_ID,
    request_id: payload.request_id,
    turn_id: `2a5b7c9d-1e3f-4a6b-8c0d-2e4f6a8b0c0${turn}`,
    estado: 'completado',
    respuesta_markdown: `Resumen del agente ${turn}`,
    analisis: {
      conocida: ['Dato conocido de prueba'],
      faltante: ready ? [] : ['Falta la vigencia'],
      supuesta: [],
      ambigua: [],
    },
    preguntas: questions,
    fuentes_consultadas: [{ nombre: 'consultar_glosario', resultados: 1, duracion_ms: 3 }],
    listo_para_redactor: ready,
    limitaciones: [],
    duracion_ms: 5,
    prompt_version: '1.2.0',
  };
}

const QUESTION = (estado) => ({
  question_id: 'q-vigencia',
  categoria: 'Reglas de negocio',
  pregunta: '¿Desde cuándo aplica la vigencia (checklist CHK-RN-04)?',
  estado,
  created_turn_id: null,
  updated_turn_id: null,
});

function renderAt(path) {
  window.history.replaceState({}, '', path);
  return render(<App />);
}

async function analyzeRequirement(user) {
  await user.type(screen.getByLabelText(/Nombre del requerimiento/i), 'Vigencia de cobertura');
  await user.type(screen.getByLabelText(/Descripción o información de negocio/i), 'Negocio pide ajustar la vigencia de la cobertura adicional.');
  await user.selectOptions(screen.getByLabelText(/^Sistema/), 'Portal de Clientes');
  await user.type(screen.getByLabelText(/^Código de HU/), 'POL-OF');
  await user.click(screen.getByRole('button', { name: /Analizar Requerimiento/i }));
  await screen.findByText(/Paso 2 — Análisis del Agente Analista/i);
}

describe('wizard conectado al Agente Analista', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    analystApi.getHealth.mockResolvedValue({ status: 'ready', timeout_seconds: 90, checks: {} });
    analystApi.createConversation.mockResolvedValue({ conversation_id: CONVERSATION_ID });
    let turn = 0;
    analystApi.sendMessage.mockImplementation(async (_id, payload) => {
      turn += 1;
      if (turn === 1) return agentResponse(payload, turn, { ready: false, questions: [QUESTION('pendiente')] });
      return agentResponse(payload, turn, { ready: true, questions: [QUESTION('respondida')] });
    });
    repositorioApi.saveStory.mockResolvedValue({ id: 'HU-X', titulo: 'x', aprobada_en: '2026-10-29' });
    repositorioApi.listChanges.mockResolvedValue([]);
    repositorioApi.listLessons.mockResolvedValue([]);
  });

  afterEach(() => cleanup());

  it('analiza, pregunta, reenvía respuestas y solo aprueba el Product Owner tras confirmar anonimización', async () => {
    const user = userEvent.setup();
    renderAt('/historias/nueva');
    await analyzeRequirement(user);

    expect(analystApi.sendMessage.mock.calls[0][1].message).toContain('REQUERIMIENTO NUEVO');
    expect(screen.getByText('Dato conocido de prueba')).toBeInTheDocument();
    expect(screen.getByText(/Glosario \(1\)/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Preguntas a Negocio \(1\)/i }));
    expect(screen.getByText(/Quedan 1 preguntas pendientes/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Enviar respuestas al agente/i })).toBeDisabled();

    await user.type(screen.getByPlaceholderText(/Escriba aquí la respuesta de Negocio/i), 'Desde la próxima renovación');
    await user.click(screen.getByRole('button', { name: /Enviar respuestas al agente \(1\)/i }));
    expect(await screen.findByText(/No quedan vacíos relevantes/i)).toBeInTheDocument();
    expect(analystApi.sendMessage.mock.calls[1][1].message).toContain('RESPUESTAS DE NEGOCIO');
    expect(analystApi.sendMessage.mock.calls[1][1].message).toContain('Desde la próxima renovación');
    expect(analystApi.createConversation).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: /Generar Historia de Usuario/i }));
    expect(await screen.findByText(/Borrador simulado: edítelo antes de continuar/i, {}, { timeout: 4000 })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Aprobación del Product Owner/i }));

    const approve = await screen.findByRole('button', { name: /Aprobar y guardar en el Repositorio/i });
    expect(approve).toBeDisabled();
    await user.click(screen.getByRole('checkbox'));
    expect(approve).toBeEnabled();
    await user.click(approve);

    await waitFor(() => expect(repositorioApi.saveStory).toHaveBeenCalledTimes(1));
    const payload = repositorioApi.saveStory.mock.calls[0][0];
    expect(payload.confirmo_anonimizada).toBe(true);
    expect(payload.aclaraciones).toEqual([{
      pregunta: '¿Desde cuándo aplica la vigencia (checklist CHK-RN-04)?',
      respuesta: 'Desde la próxima renovación',
    }]);
    const stored = JSON.parse(localStorage.getItem('historias_usuario_prototipo'));
    const saved = stored.find((story) => story.id === payload.id);
    expect(saved.status).toBe('aprobada');
    expect(saved.repositorySynced).toBe(true);
  });

  it('no permite aprobar con preguntas pendientes y guarda un borrador', async () => {
    const user = userEvent.setup();
    renderAt('/historias/nueva');
    await analyzeRequirement(user);
    await user.click(screen.getByRole('button', { name: /Preguntas a Negocio/i }));
    await user.click(screen.getByRole('button', { name: /Continuar con preguntas pendientes/i }));
    await screen.findByText(/edítelo antes de continuar/i, {}, { timeout: 4000 });
    await user.click(screen.getByRole('button', { name: /Aprobación del Product Owner/i }));

    expect(await screen.findByText(/No se puede aprobar con preguntas pendientes/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Aprobar y guardar en el Repositorio/i })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: /Guardar borrador/i }));
    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem('historias_usuario_prototipo'));
      expect(stored[0].status).toBe('pendiente_de_informacion');
    });
    expect(repositorioApi.saveStory).not.toHaveBeenCalled();
  });

  it('muestra el motivo si el Repositorio rechaza la HU y no la marca como aprobada', async () => {
    repositorioApi.saveStory.mockRejectedValue(Object.assign(new Error('El texto parece contener datos personales (correo electrónico). Anonimícelo antes de guardarlo.'), {
      name: 'AnalystApiError', code: 'INVALID_REQUEST',
    }));
    const user = userEvent.setup();
    renderAt('/historias/nueva');
    await analyzeRequirement(user);
    await user.click(screen.getByRole('button', { name: /Preguntas a Negocio/i }));
    await user.type(screen.getByPlaceholderText(/Escriba aquí la respuesta de Negocio/i), 'Respuesta');
    await user.click(screen.getByRole('button', { name: /Enviar respuestas al agente/i }));
    await screen.findByText(/No quedan vacíos relevantes/i);
    await user.click(screen.getByRole('button', { name: /Generar Historia de Usuario/i }));
    await screen.findByText(/edítelo antes de continuar/i, {}, { timeout: 4000 });
    await user.click(screen.getByRole('button', { name: /Aprobación del Product Owner/i }));
    expect(screen.queryByText(/No se puede aprobar con preguntas pendientes/)).not.toBeInTheDocument();
    await user.click(await screen.findByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: /Aprobar y guardar en el Repositorio/i }));

    expect(await screen.findByText(/datos personales \(correo electrónico\)/i)).toBeInTheDocument();
    const stored = JSON.parse(localStorage.getItem('historias_usuario_prototipo') ?? '[]');
    expect(stored.some((story) => story.status === 'aprobada')).toBe(false);
  });

  it('muestra un error y permite reintentar cuando el agente falla', async () => {
    analystApi.sendMessage.mockRejectedValueOnce(Object.assign(new Error('x'), { code: 'MODEL_UNAVAILABLE', retryable: false }));
    const user = userEvent.setup();
    renderAt('/historias/nueva');
    await user.type(screen.getByLabelText(/Nombre del requerimiento/i), 'Vigencia');
    await user.type(screen.getByLabelText(/Descripción o información de negocio/i), 'Texto');
    await user.selectOptions(screen.getByLabelText(/^Sistema/), 'Portal de Clientes');
    await user.type(screen.getByLabelText(/^Código de HU/), 'POL-OF');
    await user.click(screen.getByRole('button', { name: /Analizar Requerimiento/i }));
    expect(await screen.findByText(/No se pudo completar el análisis/i)).toBeInTheDocument();
    expect(screen.getByText(/Paso 1/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Reintentar$/i }));
    await screen.findByText(/Paso 2 — Análisis del Agente Analista/i);
  });
});

describe('después del grooming', () => {
  const APPROVED = {
    id: 'HU-950', number: 'HU-950', title: 'Vigencia de cobertura', type: 'Nueva Funcionalidad', status: 'aprobada',
    createdAt: '2026-10-29', updatedAt: '2026-10-29', infoType: 'Minuta',
    userStory: { asA: 'analista', iWant: 'ajustar vigencia', soThat: 'renovar bien' },
    acceptanceCriteria: [{ text: 'Se valida' }], repositorySynced: true,
  };

  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    localStorage.setItem('historias_usuario_prototipo', JSON.stringify([APPROVED]));
    analystApi.getHealth.mockResolvedValue({ status: 'ready', timeout_seconds: 90, checks: {} });
    repositorioApi.listChanges.mockResolvedValue([]);
    repositorioApi.listLessons.mockResolvedValue([]);
    repositorioApi.registerChange.mockResolvedValue({ solicitud_id: 1, leccion_id: 7, estado: 'propuesta' });
  });

  afterEach(() => cleanup());

  const CAMBIO = {
    id: 's1', hu_id: 'HU-950', solicitud: 'Negocio pide aplicar también a endosos', clasificacion: 'cambio_alcance',
    causa_raiz: 'Datos requeridos', leccion_estado: 'propuesta',
  };

  async function solicitarCambioDeAlcance(user) {
    renderAt('/historias/HU-950/solicitar-cambio');
    await screen.findByText(/Después del grooming — Solicitudes de cambio/i);
    await user.type(screen.getByLabelText(/Solicitud de cambio/i), 'Negocio pide aplicar también a endosos');
    await user.selectOptions(screen.getByLabelText(/qué no se preguntó a tiempo/i), 'Datos requeridos');
    await user.type(screen.getByLabelText(/Pregunta que debió hacerse/i), '¿Aplica también a endosos?');
    await user.click(screen.getByRole('button', { name: /Registrar y analizar cambio/i }));
  }

  it('registra la solicitud de cambio de alcance y abre directo el análisis sobre la misma HU', async () => {
    const user = userEvent.setup();
    await solicitarCambioDeAlcance(user);
    expect(repositorioApi.registerChange).toHaveBeenCalledWith({
      hu_id: 'HU-950',
      solicitud: 'Negocio pide aplicar también a endosos',
      clasificacion: 'cambio_alcance',
      causa_raiz: 'Datos requeridos',
      pregunta_sugerida: '¿Aplica también a endosos?',
      terminos: [],
    });
    expect(await screen.findByLabelText(/Nombre del requerimiento/i)).toHaveValue('Vigencia de cobertura');
    expect(screen.getByLabelText(/Descripción o información de negocio/i).value).toContain('Negocio pide aplicar también a endosos');
    expect(screen.getByText(/pasará de Rev\. 1 a Rev\. 2/)).toBeInTheDocument();
  });

  it('si no se puede registrar la solicitud, no abre el análisis y muestra el motivo', async () => {
    repositorioApi.registerChange.mockRejectedValueOnce(new Error('falla'));
    const user = userEvent.setup();
    await solicitarCambioDeAlcance(user);
    expect(await screen.findByText(/No se pudo registrar/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Nombre del requerimiento/i)).not.toBeInTheDocument();
  });

  it('si no fue un vacío del análisis, no pide ni genera lección', async () => {
    const user = userEvent.setup();
    renderAt('/historias/HU-950/solicitar-cambio');
    await user.type(await screen.findByLabelText(/Solicitud de cambio/i), 'Negocio decidió quitar el campo');
    await user.click(screen.getByLabelText(/No fue un vacío del análisis/i));
    expect(screen.queryByLabelText(/Pregunta que debió hacerse/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Registrar y analizar cambio/i }));
    await waitFor(() => expect(repositorioApi.registerChange).toHaveBeenCalledWith({
      hu_id: 'HU-950', solicitud: 'Negocio decidió quitar el campo', clasificacion: 'cambio_alcance',
    }));
    expect(await screen.findByLabelText(/Nombre del requerimiento/i)).toBeInTheDocument();
  });

  it('exige la pregunta cuando sí fue un vacío del análisis', async () => {
    const user = userEvent.setup();
    renderAt('/historias/HU-950/solicitar-cambio');
    await user.type(await screen.findByLabelText(/Solicitud de cambio/i), 'Aplicar a endosos');
    await user.click(screen.getByRole('button', { name: /Registrar y analizar cambio/i }));
    expect(await screen.findByText(/Escriba la pregunta que debió hacerse/i)).toBeInTheDocument();
    expect(repositorioApi.registerChange).not.toHaveBeenCalled();
  });

  it('al aprobar la revisión la misma HU pasa a Rev. 2 y la anterior queda en el historial', async () => {
    const user = userEvent.setup();
    localStorage.setItem('historias_usuario_prototipo', JSON.stringify([{
      ...APPROVED, system: 'Portal de Clientes', codigoHu: 'POL-OF', approvedAt: '2026-10-29T10:00:00.000Z',
      acceptanceCriteria: [{ id: 'c1', given: 'hay una renovación', when: 'cambia la vigencia', then: 'se valida' }],
      questions: [{ id: 'q1', category: 'Reglas de negocio', question: '¿Desde cuándo?', answer: 'Desde la renovación', status: 'respondida' }],
    }]));
    analystApi.createConversation.mockResolvedValue({ conversation_id: CONVERSATION_ID });
    analystApi.sendMessage.mockImplementation(async (_id, payload) => ({
      ...agentResponse(payload, 1, { ready: true, questions: [] }),
    }));
    repositorioApi.saveStory.mockResolvedValue({ id: 'HU-950', titulo: 'x', aprobada_en: '2026-10-30' });

    await solicitarCambioDeAlcance(user);
    await user.click(await screen.findByRole('button', { name: /Analizar Requerimiento/i }));
    await screen.findByText(/Paso 2 — Análisis del Agente Analista/i);
    expect(analystApi.sendMessage.mock.calls[0][1].message).toContain('Desde la renovación');

    await user.click(screen.getByRole('button', { name: /Preguntas a Negocio/i }));
    await user.click(await screen.findByRole('button', { name: /Generar Historia de Usuario/i }));
    expect(await screen.findByText(/Borrador simulado: edítelo antes de continuar/i, {}, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Guardar borrador/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Aprobación del Product Owner/i }));
    expect(screen.queryByText(/No se puede aprobar con preguntas pendientes/)).not.toBeInTheDocument();
    await user.click(await screen.findByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: /Aprobar y guardar en el Repositorio/i }));

    await waitFor(() => expect(repositorioApi.saveStory).toHaveBeenCalledTimes(1));
    expect(repositorioApi.saveStory.mock.calls[0][0].id).toBe('HU-950');
    const lista = JSON.parse(localStorage.getItem('historias_usuario_prototipo'));
    expect(lista).toHaveLength(1);
    expect(lista[0]).toMatchObject({ id: 'HU-950', status: 'aprobada', revision: 2, motivoRevision: 'Negocio pide aplicar también a endosos' });
    expect(lista[0].revisiones).toHaveLength(1);
    expect(lista[0].revisiones[0]).toMatchObject({ revision: 1, motivo: 'Aprobación inicial', userStory: APPROVED.userStory });
    expect(lista[0].acceptanceCriteria[0]).toMatchObject({ given: 'hay una renovación' });
    expect(await screen.findByText('Historial de revisiones')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Rev\. 2/ })).toBeInTheDocument();
  });

  it('las solicitudes pendientes del historial siguen ofreciendo analizar al volver a la HU', async () => {
    repositorioApi.listChanges.mockResolvedValue([CAMBIO]);
    const user = userEvent.setup();
    renderAt('/historias/HU-950/solicitar-cambio');
    await user.click(await screen.findByRole('tab', { name: /Historial de solicitudes/i }));
    expect(await screen.findByRole('button', { name: /Analizar el cambio con el agente/i })).toBeInTheDocument();
  });

  it('las solicitudes anteriores (aclaración o corrección) se leen pero ya no ofrecen aplicar nada', async () => {
    repositorioApi.listChanges.mockResolvedValue([
      { id: 's2', hu_id: 'HU-950', solicitud: 'Cambiar el nombre del rol', clasificacion: 'correccion', causa_raiz: '', leccion_estado: null },
    ]);
    const user = userEvent.setup();
    renderAt('/historias/HU-950/solicitar-cambio');
    await user.click(await screen.findByRole('tab', { name: /Historial de solicitudes/i }));
    expect(await screen.findByText(/Corrección de error/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Analizar el cambio con el agente/i })).not.toBeInTheDocument();
  });

  it('no ofrece solicitudes de cambio para una HU que no está aprobada', async () => {
    localStorage.setItem('historias_usuario_prototipo', JSON.stringify([{ ...APPROVED, status: 'revisada' }]));
    renderAt('/historias/HU-950/solicitar-cambio');
    expect(await screen.findByText(/Solo una historia aprobada admite solicitudes de cambio/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Solicitud de cambio/i)).not.toBeInTheDocument();
  });

  it('el detalle solo consulta: sin formulario de solicitudes ni acciones, solo Volver', async () => {
    renderAt('/historias/HU-950');
    await screen.findByRole('heading', { name: /HU-950/ });
    expect(screen.queryByRole('tab', { name: /Solicitudes de cambio/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Solicitud de cambio/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Volver/i })).toBeInTheDocument();
    ['Editar', 'Solicitar cambio', 'Descargar'].forEach((nombre) => {
      expect(screen.queryByRole('button', { name: nombre })).not.toBeInTheDocument();
    });
  });

  it('el Product Owner aprueba una lección propuesta', async () => {
    repositorioApi.listLessons.mockResolvedValue([{
      id: '0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c07', codigo: 'LEC-007', hu_codigo: 'HU-PRU-001', hu_id: 'HU-950', categoria: 'Datos requeridos', pregunta_sugerida: '¿Aplica también a endosos?',
      terminos: ['endoso'], estado: 'propuesta',
    }]);
    repositorioApi.decideLesson.mockResolvedValue({});
    const user = userEvent.setup();
    renderAt('/lecciones');
    const item = (await screen.findByText(/LEC-007/)).closest('li');
    await user.click(within(item).getByRole('button', { name: /Aprobar/i }));
    await waitFor(() => expect(repositorioApi.decideLesson).toHaveBeenCalledWith('0b3f6f0e-52c8-4f0b-9c1e-6a1d2f3b4c07', 'aprobar'));
  });
});
