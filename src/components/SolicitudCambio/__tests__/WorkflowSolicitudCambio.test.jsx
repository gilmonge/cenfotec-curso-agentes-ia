import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SolicitudCambioComponent } from '../SolicitudCambioComponent.jsx';
import { repositorioApi } from '../../../services/repositorioApi.js';
import { resumeWorkflow, startWorkflow } from '../../../services/workflowApi.js';

vi.mock('../../../services/analystApi.js', () => ({ request: vi.fn() }));
vi.mock('../../../services/workflowApi.js', () => ({
  startWorkflow: vi.fn(), getWorkflow: vi.fn(), resumeWorkflow: vi.fn(),
  WorkflowApiError: class WorkflowApiError extends Error {},
}));
vi.mock('../../../services/repositorioApi.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, repositorioApi: {
    saveStory: vi.fn(), listStories: vi.fn(), registerChange: vi.fn(), listChanges: vi.fn(),
    listLessons: vi.fn(), decideLesson: vi.fn(),
  } };
});

const HU_ID = '52392004-c645-4ccc-a08d-e9d279427e5f';
const story = {
  id: HU_ID, title: 'Consultar vigencia', number: 'HU-POL-001', status: 'aprobada',
  description: 'Consultar vigencia de póliza',
  userStory: { asA: 'Ejecutivo', iWant: 'consultar vigencia', soThat: 'responder con precisión' },
  acceptanceCriteria: [{ id: 'c1', given: 'una póliza', when: 'consulto', then: 'veo la fecha' }],
  questions: [], revisiones: [],
};
const recommendation = {
  recommendation: 'aclaracion',
  comparison: [{ approved_excerpt: 'fecha de vigencia', request_excerpt: 'mostrar hora final', explanation: 'Precisa el detalle mostrado.' }],
  impact: ['No cambia la regla de negocio.'], rationale: 'La solicitud precisa una presentación existente.',
  uncertainties: [],
  lessons_proposed: [{ category: 'Datos requeridos', suggested_question: '¿Se incluye la hora?', terms: ['hora'] }],
};
const pendingDecision = {
  workflow_id: 'a9c393e3-aef7-475d-b0bf-883ece58f481', mode: 'post_grooming', status: 'interrupted', stage: 'decision_humana',
  results: { analyst: null, story: null, review_observations: [], technical_assessment: null, po_decision: null, persistence_result: null, change_recommendation: recommendation, change_decision: null, change_persistence_result: null, completion_reason: null },
  interrupt: { interrupt_id: 'change-interrupt-1', kind: 'change_decision', payload: { change_recommendation: recommendation, decisions: ['aplicar', 'rechazar', 'devolver'], lesson_decisions: ['aprobar', 'rechazar'] }, response_schema: { type: 'object' } },
};

const renderPanel = () => render(<MemoryRouter initialEntries={[`/historias/${HU_ID}/solicitar-cambio`]}>
  <Routes>
    <Route path="/historias/:id/solicitar-cambio" element={<SolicitudCambioComponent story={story} />} />
    <Route path="/historias/nueva" element={<div data-testid="workflow-review">Workflow de revisión de la HU</div>} />
  </Routes>
</MemoryRouter>);

describe('Gestor de Cambios post_grooming', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    repositorioApi.listChanges.mockResolvedValue([]);
    repositorioApi.listStories.mockResolvedValue([{ id: HU_ID, titulo: 'HU aprobada', aprobada_en: '2026-11-20T12:00:00Z' }]);
  });
  afterEach(() => cleanup());

  it('starts from the real approved HU, shows clarification recommendation, and records only a confirmed decision', async () => {
    const user = userEvent.setup();
    startWorkflow.mockResolvedValue(pendingDecision);
    resumeWorkflow.mockResolvedValue({
      ...pendingDecision, status: 'completed', stage: 'decision_humana', interrupt: null,
      results: { ...pendingDecision.results, change_decision: { decision: 'aplicar' }, change_persistence_result: { status: 'recorded', change_id: 'change-42', lesson_ids: [] }, completion_reason: 'La aclaración autorizada quedó registrada.' },
    });

    renderPanel();
    await user.type(await screen.findByLabelText(/Solicitud de cambio/i), 'Mostrar la hora final de vigencia');
    await user.click(screen.getByRole('button', { name: /Analizar con Gestor de Cambios/i }));
    expect(await screen.findByText(/Recomendación del Gestor de Cambios: aclaracion/i)).toBeInTheDocument();
    expect(screen.getByText('HU aprobada')).toBeInTheDocument();
    expect(screen.getByText(/No cambia la regla de negocio/)).toBeInTheDocument();
    expect(screen.getByText(/Lecciones propuestas \(no aprobadas\)/)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Decisión'), 'aplicar');
    expect(screen.getByLabelText('Decisión sobre la lección')).toHaveValue('');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    await waitFor(() => expect(resumeWorkflow).toHaveBeenCalledTimes(1));
    expect(startWorkflow).toHaveBeenCalledWith({ mode: 'post_grooming', approved_story_id: HU_ID, change_request: 'Mostrar la hora final de vigencia' }, expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(resumeWorkflow.mock.calls[0][1]).toEqual({ kind: 'change_decision', interrupt_id: 'change-interrupt-1', response: { decision: 'aplicar', lesson_decisions: [] } });
    expect(repositorioApi.registerChange).not.toHaveBeenCalled();
  });

  it('returns scope changes to the existing workflow review and does not force scope classification', async () => {
    const user = userEvent.setup();
    const scopeRecommendation = { ...recommendation, recommendation: 'cambio_alcance' };
    startWorkflow.mockResolvedValue({
      ...pendingDecision,
      results: { ...pendingDecision.results, change_recommendation: scopeRecommendation },
      interrupt: { ...pendingDecision.interrupt, payload: { ...pendingDecision.interrupt.payload, change_recommendation: scopeRecommendation } },
    });
    resumeWorkflow.mockResolvedValue({
      ...pendingDecision, interrupt: { interrupt_id: 'po-next', kind: 'po_approval', payload: { story: {} }, response_schema: {} },
    });

    renderPanel();
    await user.type(await screen.findByLabelText(/Solicitud de cambio/i), 'Agregar fecha alternativa');
    await user.click(screen.getByRole('button', { name: /Analizar con Gestor de Cambios/i }));
    await screen.findByText(/Recomendación del Gestor de Cambios: cambio_alcance/i);
    await user.selectOptions(screen.getByLabelText('Decisión'), 'aplicar');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));

    expect(resumeWorkflow).toHaveBeenCalledWith(pendingDecision.workflow_id, expect.objectContaining({ interrupt_id: 'change-interrupt-1', response: { decision: 'aplicar', lesson_decisions: [] } }), expect.anything());
    expect(await screen.findByTestId('workflow-review')).toBeInTheDocument();
  });
});
