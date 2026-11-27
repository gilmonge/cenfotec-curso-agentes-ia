import React from 'react';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../../App.jsx';
import { analystApi } from '../../../services/analystApi.js';
import { repositorioApi } from '../../../services/repositorioApi.js';
import { deleteWorkflow, getWorkflow, listWorkflows, resumeWorkflow, retryWorkflow, saveWorkflowDraft, startWorkflow, WorkflowApiError } from '../../../services/workflowApi.js';

vi.mock('../../../services/analystApi.js', () => ({
  analystApi: {
    getHealth: vi.fn(), createConversation: vi.fn(), sendMessage: vi.fn(), cancelTurn: vi.fn(),
    resetConversation: vi.fn(), deleteConversation: vi.fn(),
  },
}));
vi.mock('../../../services/workflowApi.js', () => ({
  startWorkflow: vi.fn(), getWorkflow: vi.fn(), resumeWorkflow: vi.fn(),
  listWorkflows: vi.fn(), deleteWorkflow: vi.fn(), saveWorkflowDraft: vi.fn(), retryWorkflow: vi.fn(),
  WorkflowApiError: class WorkflowApiError extends Error {
    constructor(status, message) { super(message); this.status = status; }
  },
}));
vi.mock('../../../services/repositorioApi.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, repositorioApi: {
    saveStory: vi.fn(), listStories: vi.fn(), registerChange: vi.fn(), listChanges: vi.fn(),
    listLessons: vi.fn(), decideLesson: vi.fn(),
  } };
});

const WORKFLOW_ID = '7b5966dc-d30a-4b2b-9f52-a9076eba2818';
const baseResults = {
  analyst: {
    conversation_id: '00000000-0000-4000-8000-000000000001',
    request_id: '00000000-0000-4000-8000-000000000002',
    turn_id: '00000000-0000-4000-8000-000000000003',
    estado: 'completado', respuesta_markdown: 'Análisis real del Analista',
    analisis: { conocida: ['Vigencia'], faltante: ['Duración'], supuesta: [], ambigua: [] },
    preguntas: [{ question_id: 'q-plazo', categoria: 'Reglas de negocio', pregunta: '¿Cuál es el plazo?', estado: 'pendiente' }],
    fuentes_consultadas: [], listo_para_redactor: false, limitaciones: [], duracion_ms: 3, prompt_version: '1.0.0',
  },
  story: null, review_observations: [], technical_assessment: null,
  po_decision: null, persistence_result: null, change_recommendation: null,
  change_decision: null, change_persistence_result: null, completion_reason: null,
};
const analystInterrupt = {
  interrupt_id: 'interrupt-business-1', kind: 'business_answers',
  payload: { questions: [{ question_id: 'q-plazo', categoria: 'Reglas de negocio', pregunta: '¿Cuál es el plazo?', estado: 'pendiente' }], max_answer_chars: 1000, max_total_chars: 3500 },
  response_schema: { type: 'object' },
};
const draftStory = {
  como: 'Ejecutivo de seguros', quiero: 'consultar la vigencia', para: 'responder con precisión',
  criterios: [{ dado: 'una póliza vigente', cuando: 'consulto la fecha', entonces: 'veo el plazo correcto' }],
  review_status: 'reviewed', review_round: 1, observations: ['Criterio verificable'],
};
const poInterrupt = {
  interrupt_id: 'interrupt-po-2', kind: 'po_approval',
  payload: {
    story: draftStory, review_observations: ['Criterio verificable'],
    technical_assessment: {
      affected_modules: [{ source_id: 'ejemplos/polizas_demo/servicios/polizas.py', source_ref: 'ejemplos/polizas_demo/servicios/polizas.py', evidence: 'Consulta el módulo de pólizas.' }],
      dependencies: [], risks: [], critical_processes: [],
      consulted_sources: [{ source_id: 'ejemplos/polizas_demo/servicios/polizas.py', source_ref: 'ejemplos/polizas_demo/servicios/polizas.py' }], uncertainties: [],
    }, decisions: ['aprobar', 'rechazar'], return_requires_reason: true,
  }, response_schema: { type: 'object' },
};
const impactoNegocio = [{
  area: 'Carga masiva de pólizas',
  hoy: 'Calcula la vigencia con otra regla.',
  debe: 'Usar el mismo plazo que la consulta.',
}];
const decisionImpacto = '¿La carga masiva usa el mismo plazo que la consulta?';
// El Analista y el Asesor trabajan en equipo: una sola ronda con la pregunta y la decisión del impacto.
const impactInterrupt = {
  interrupt_id: 'interrupt-business-1', kind: 'business_answers',
  payload: {
    impacto_negocio: impactoNegocio,
    questions: [
      { question_id: 'q-plazo', categoria: 'Reglas de negocio', pregunta: '¿Cuál es el plazo?', estado: 'pendiente', origen: 'analista' },
      { question_id: 'decision-1', categoria: 'Decisión de impacto', pregunta: decisionImpacto, origen: 'asesor_tecnico' },
    ],
    max_answer_chars: 1000, max_total_chars: 3500,
  },
  response_schema: { type: 'object' },
};
const poResults = {
  ...baseResults,
  analyst: {
    ...baseResults.analyst, listo_para_redactor: true, preguntas: [],
    analisis: { ...baseResults.analyst.analisis, faltante: [] },
    supuesto_validar_po: ['Se supone: el plazo se cuenta en días naturales'],
  },
  story: draftStory,
  review_observations: ['Ronda anterior ya atendida', 'Criterio verificable'],
  ultima_revision: ['Criterio verificable'],
  notas_hu: [{ tipo: 'dependencia', texto: 'Servicio al Cliente avisará el nuevo plazo.' }],
  technical_assessment: { ...poInterrupt.payload.technical_assessment, impacto_negocio: impactoNegocio, decision_pendiente: [decisionImpacto] },
  impact_decisions: [{ question_id: 'decision-1', pregunta: decisionImpacto, respuesta: 'Sí, el mismo plazo.' }],
};
const impactResults = { ...baseResults, analyst: poResults.analyst, technical_assessment: poResults.technical_assessment };

// Las confirmaciones usan el modal de la aplicación (no el cuadro del navegador).
async function aceptarConfirmacion(user) {
  const dialogo = await screen.findByRole('alertdialog');
  await user.click(within(dialogo).getByRole('button', { name: /^(Confirmar|Descartar)$/ }));
}

function renderAt(path = '/historias/nueva') {
  window.history.replaceState({}, '', path);
  return render(<App />);
}

async function fillRequirement(user) {
  await user.type(screen.getByLabelText(/Nombre del requerimiento/i), 'Consultar vigencia');
  await user.type(screen.getByLabelText(/Descripci[oó]n o informaci[oó]n de negocio/i), 'Negocio solicita conocer el plazo de vigencia.');
  await user.selectOptions(screen.getByLabelText(/^Sistema/), 'Portal de Clientes');
  await user.type(screen.getByLabelText(/^C[oó]digo de HU/), 'POL-OF');
}

describe('workflow LangGraph conectado al wizard de HU', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    analystApi.getHealth.mockResolvedValue({ status: 'ready', timeout_seconds: 90, checks: {} });
    analystApi.createConversation.mockResolvedValue({ conversation_id: '00000000-0000-4000-8000-000000000001' });
    repositorioApi.listStories.mockResolvedValue([]);
  });

  afterEach(() => cleanup());

  it('muestra el estado y el motivo cuando el flujo se detiene sin preguntas ni borrador', async () => {
    const user = userEvent.setup();
    startWorkflow.mockResolvedValue({
      workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'interrupted', stage: 'espera_negocio',
      results: baseResults, interrupt: analystInterrupt,
    });
    resumeWorkflow.mockResolvedValueOnce({
      workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'failed', stage: 'analista',
      results: { ...baseResults, analyst: { ...baseResults.analyst, preguntas: [] }, completion_reason: 'El Analista reportó vacíos sin preguntas pendientes.' },
      interrupt: null,
    });

    renderAt();
    await fillRequirement(user);
    await user.click(screen.getByRole('button', { name: /Analizar Requerimiento/i }));
    await user.type(await screen.findByLabelText(/¿Cuál es el plazo\?/i), '12 meses');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));

    expect(await screen.findByText(/Flujo detenido por un error/i)).toBeInTheDocument();
    expect(screen.getByText(/El Analista reportó vacíos sin preguntas pendientes/i)).toBeInTheDocument();
    expect(screen.queryByText(/Queda(n)? \d+ pregunta/i)).not.toBeInTheDocument();
  });

  it('retoma una HU en proceso en el paso de preguntas con el formulario y las respuestas guardadas', async () => {
    const user = userEvent.setup();
    getWorkflow.mockResolvedValue({
      workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'interrupted', stage: 'espera_negocio',
      results: impactResults, interrupt: impactInterrupt,
      guardado: {
        titulo: 'Consultar vigencia', creado_por: 'Analista', persistente: true, reintentable: false, estado: 'esperando',
        formulario: { requirementName: 'Consultar vigencia', system: 'Portal de Clientes', codigoHu: 'POL-OF', description: 'Plazo de vigencia.' },
        borrador_respuestas: { 'decision-1': 'Lo consulto con Negocio' },
      },
    });
    saveWorkflowDraft.mockResolvedValue(null);

    renderAt(`/historias/nueva?flujo=${WORKFLOW_ID}`);

    expect(await screen.findByText(/Paso 3 — Preguntas para Negocio/i)).toBeInTheDocument();
    expect(getWorkflow).toHaveBeenCalledWith(WORKFLOW_ID, expect.anything());
    expect(screen.getByText(/El avance se guarda automáticamente/i)).toBeInTheDocument();
    const respuesta = screen.getByLabelText(/La carga masiva usa el mismo plazo/);
    expect(respuesta).toHaveValue('Lo consulto con Negocio');
    await user.type(respuesta, ': sí');
    await user.click(screen.getByRole('button', { name: /Guardar sin enviar/i }));

    await waitFor(() => expect(saveWorkflowDraft).toHaveBeenCalledWith(
      WORKFLOW_ID, { 'decision-1': 'Lo consulto con Negocio: sí' },
    ));
    expect(await screen.findByText(/Puede salir y retomarlas después/i)).toBeInTheDocument();
    await user.click(screen.getByText('Requerimiento'));
    expect(screen.getByLabelText(/Nombre del requerimiento/i)).toHaveValue('Consultar vigencia');
  });

  it('ofrece reintentar el paso que falló sin perder el avance', async () => {
    const user = userEvent.setup();
    getWorkflow.mockResolvedValue({
      workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'running', stage: 'asesor_tecnico',
      results: { ...baseResults, analyst: poResults.analyst }, interrupt: null,
      guardado: { titulo: 'Consultar vigencia', persistente: true, reintentable: true, estado: 'error', formulario: {}, borrador_respuestas: {} },
    });
    retryWorkflow.mockResolvedValue({
      workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'interrupted', stage: 'espera_negocio',
      results: impactResults, interrupt: impactInterrupt,
      guardado: { persistente: true, reintentable: false, estado: 'esperando', formulario: {}, borrador_respuestas: {} },
    });

    renderAt(`/historias/nueva?flujo=${WORKFLOW_ID}`);
    await user.click(await screen.findByRole('button', { name: /Reintentar el paso que falló/i }));

    expect(retryWorkflow).toHaveBeenCalledWith(WORKFLOW_ID, expect.anything());
    expect(await screen.findByText(/Paso 3 — Preguntas para Negocio/i)).toBeInTheDocument();
    expect(screen.getByText('Lo que encontró el Asesor Técnico')).toBeInTheDocument();
  });

  it('lista las HU en proceso para retomarlas o descartarlas', async () => {
    const user = userEvent.setup();
    listWorkflows.mockResolvedValue([
      { workflow_id: WORKFLOW_ID, modo: 'pre_grooming', titulo: 'Teléfono opcional', creado_por: 'Analista',
        estado: 'esperando', etapa: 'espera_negocio', espera: 'business_answers',
        creado_en: '2026-11-26T10:00:00+00:00', actualizado_en: '2026-11-26T11:00:00+00:00' },
      { workflow_id: 'otro', modo: 'pre_grooming', titulo: 'Ya terminada', estado: 'completado', etapa: 'repositorio',
        espera: null, creado_en: '2026-11-26T10:00:00+00:00', actualizado_en: '2026-11-26T11:00:00+00:00' },
    ]);
    deleteWorkflow.mockResolvedValue(null);

    renderAt('/historias');

    expect(await screen.findByText('Teléfono opcional')).toBeInTheDocument();
    expect(screen.getByText(/Esperando respuestas de Negocio/i)).toBeInTheDocument();
    expect(screen.queryByText('Ya terminada')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Descartar/i }));
    await aceptarConfirmacion(user);
    await waitFor(() => expect(deleteWorkflow).toHaveBeenCalledWith(WORKFLOW_ID));
    await waitFor(() => expect(screen.queryByText('Teléfono opcional')).not.toBeInTheDocument());
  });

  it('answers the Analyst and the Advisor in one round, shows the impact in business language, then saves only through backend PO approval', async () => {
    const user = userEvent.setup();
    startWorkflow.mockResolvedValue({
      workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'interrupted', stage: 'espera_negocio',
      results: impactResults, interrupt: impactInterrupt,
    });
    resumeWorkflow
      .mockResolvedValueOnce({ workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'interrupted', stage: 'aprobacion_po', results: poResults, interrupt: poInterrupt })
      .mockResolvedValueOnce({ workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'completed', stage: 'repositorio', results: { ...poResults, po_decision: { decision: 'aprobar' }, persistence_result: { status: 'saved', story_id: WORKFLOW_ID, title: draftStory.quiero, approved_at: '2026-11-21T12:00:00Z' }, completion_reason: 'HU aprobada por el Product Owner y guardada en el Repositorio.' }, interrupt: null });

    renderAt();
    await fillRequirement(user);
    await user.click(screen.getByRole('button', { name: /Analizar Requerimiento/i }));
    // Paso 3: el impacto sin detalle técnico y una sola ronda con la pregunta del Analista y la decisión del Asesor.
    expect(await screen.findByLabelText(/¿Cuál es el plazo\?/i)).toBeInTheDocument();
    expect(screen.getByText('Lo que encontró el Asesor Técnico')).toBeInTheDocument();
    expect(screen.getByText('Carga masiva de pólizas')).toBeInTheDocument();
    expect(screen.getByText(/Decisiones sobre el impacto en otros módulos/)).toBeInTheDocument();
    expect(screen.queryByText(/polizas\.py/i)).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/¿Cuál es el plazo\?/i), '12 meses');
    await user.type(screen.getByLabelText(/La carga masiva usa el mismo plazo/), 'Sí, el mismo plazo.');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));

    expect(await screen.findByLabelText(/^Quiero/i)).toHaveValue('consultar la vigencia');
    expect(screen.getByText(/Criterio verificable/)).toBeInTheDocument();
    // Solo la última revisión; lo que quedará en la HU se muestra aparte.
    expect(screen.queryByText(/Ronda anterior ya atendida/)).not.toBeInTheDocument();
    expect(screen.getByText(/Quedará registrado en la HU/)).toBeInTheDocument();
    expect(screen.getByText(/Servicio al Cliente avisará el nuevo plazo\./)).toBeInTheDocument();
    expect(screen.getByText(/Supuestos a validar por el Product Owner/i)).toBeInTheDocument();
    expect(screen.getByText(/el plazo se cuenta en días naturales/i)).toBeInTheDocument();
    expect(screen.getByText(/Revisada por el Redactor-Revisor/i)).toBeInTheDocument();
    expect(screen.getByText(/Sí, el mismo plazo\./)).toBeInTheDocument();
    // Ningún detalle técnico ni el aviso viejo de RAG llegan a la persona usuaria.
    expect(screen.queryByText(/archivos ficticios/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/RAG\/Pinecone aún no está integrada/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/polizas\.py/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Aprobación del Product Owner/i }));
    await user.click(screen.getByRole('checkbox'));
    await user.selectOptions(screen.getByLabelText('Decisión'), 'aprobar');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    await aceptarConfirmacion(user);

    expect(resumeWorkflow).toHaveBeenNthCalledWith(1, WORKFLOW_ID, {
      kind: 'business_answers', interrupt_id: 'interrupt-business-1',
      response: { answers: [
        { question_id: 'q-plazo', answer: '12 meses' },
        { question_id: 'decision-1', answer: 'Sí, el mismo plazo.' },
      ] },
    }, expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(resumeWorkflow).toHaveBeenNthCalledWith(2, WORKFLOW_ID, {
      kind: 'po_approval', interrupt_id: 'interrupt-po-2', response: { decision: 'aprobar' },
    }, expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(repositorioApi.saveStory).not.toHaveBeenCalled();
    await waitFor(() => expect(JSON.parse(localStorage.getItem('historias_usuario_prototipo'))[0]).toMatchObject({ id: WORKFLOW_ID, status: 'aprobada' }));
    const guardada = JSON.parse(localStorage.getItem('historias_usuario_prototipo'))[0];
    // El impacto no es una sección de la HU: queda cubierto por los criterios de aceptación.
    expect(guardada.impactoNegocio).toBeUndefined();
    expect(guardada.bitacora.map((nota) => nota.tipo)).toEqual(['decision', 'supuesto', 'dependencia']);
    expect(guardada.bitacora[2]).toMatchObject({ autor: 'Redactor-Revisor', estado: 'abierto' });
    expect(JSON.stringify(guardada.bitacora)).not.toContain('Criterio verificable');
  });

  it('returns to the Redactor with a reason and does not send duplicate resumes', async () => {
    const user = userEvent.setup();
    startWorkflow.mockResolvedValue({ workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'interrupted', stage: 'aprobacion_po', results: poResults, interrupt: poInterrupt });
    resumeWorkflow.mockResolvedValue({ workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'interrupted', stage: 'redactor', results: poResults, interrupt: poInterrupt });

    renderAt();
    await fillRequirement(user);
    await user.click(screen.getByRole('button', { name: /Analizar Requerimiento/i }));
    await screen.findByLabelText(/^Quiero/i);
    await user.click(screen.getByRole('button', { name: /Aprobación del Product Owner/i }));
    await user.click(screen.getByRole('checkbox'));
    await user.selectOptions(screen.getByLabelText('Decisión'), 'devolver_redactor');
    await user.type(screen.getByLabelText(/Motivo de devolución/i), 'Aclare el criterio');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    await aceptarConfirmacion(user);

    await waitFor(() => expect(resumeWorkflow).toHaveBeenCalledTimes(1));
    expect(resumeWorkflow.mock.calls[0][1]).toMatchObject({
      kind: 'po_approval', interrupt_id: 'interrupt-po-2',
      response: { decision: 'devolver_redactor', reason: 'Aclare el criterio' },
    });
    expect(repositorioApi.saveStory).not.toHaveBeenCalled();
  });

  it('shows a missing workflow after 404 and offers a new one without claiming recovery', async () => {
    const user = userEvent.setup();
    startWorkflow.mockResolvedValue({ workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'interrupted', stage: 'aprobacion_po', results: poResults, interrupt: poInterrupt });
    getWorkflow.mockRejectedValue(new WorkflowApiError(404, 'El checkpoint se perdió. Inicie un workflow nuevo.'));

    renderAt();
    await fillRequirement(user);
    await user.click(screen.getByRole('button', { name: /Analizar Requerimiento/i }));
    await user.click(await screen.findByRole('button', { name: /Consultar estado/i }));
    expect(await screen.findByText(/Workflow: HTTP 404/i)).toBeInTheDocument();
    expect(screen.getByText(/El flujo no se encontró/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Iniciar un flujo nuevo/i })).toBeInTheDocument();
    expect(Object.values(localStorage).some((value) => value.includes(WORKFLOW_ID))).toBe(false);
  });

  it('abandons an edited checkpoint before manual save so the HU is persisted only once', async () => {
    const user = userEvent.setup();
    startWorkflow.mockResolvedValue({ workflow_id: WORKFLOW_ID, mode: 'pre_grooming', status: 'interrupted', stage: 'aprobacion_po', results: poResults, interrupt: poInterrupt });
    repositorioApi.saveStory.mockResolvedValue({ id: 'manual-story-id', titulo: 'HU manual', aprobada_en: '2026-11-21T12:00:00Z' });

    renderAt();
    await fillRequirement(user);
    await user.click(screen.getByRole('button', { name: /Analizar Requerimiento/i }));
    await user.clear(await screen.findByLabelText(/^Quiero/i));
    await user.type(screen.getByLabelText(/^Quiero/i), 'revisar el plazo editado');
    await user.click(screen.getByRole('button', { name: /Abandonar workflow y continuar en modo manual/i }));
    await user.click(screen.getByRole('button', { name: /Aprobación del Product Owner/i }));
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: /Aprobar y guardar en el Repositorio/i }));

    await waitFor(() => expect(repositorioApi.saveStory).toHaveBeenCalledTimes(1));
    expect(resumeWorkflow).not.toHaveBeenCalled();
    expect(repositorioApi.saveStory.mock.calls[0][0].historia.iWant).toBe('revisar el plazo editado');
  });
});
