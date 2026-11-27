import { expect, test } from '@playwright/test';

const storyId = '00000000-0000-4000-8000-000000000003';
const question = {
  question_id: 'question-synthetic-1',
  pregunta: '¿Cuál es la fecha de vigencia de la póliza ficticia?',
  categoria: 'Datos requeridos',
  estado: 'pendiente',
};
const story = {
  como: 'persona usuaria ficticia',
  quiero: 'consultar una póliza ficticia',
  para: 'conocer sus fechas de cobertura',
  criterios: [{ dado: 'una póliza ficticia', cuando: 'consulto el detalle', entonces: 'veo su vigencia' }],
  observations: [],
};
const recommendation = {
  recommendation: 'aclaracion',
  comparison: [{ approved_excerpt: 'Póliza TEST-003', request_excerpt: 'mostrar fecha de vencimiento', explanation: 'Aclaración de un campo.' }],
  impact: ['Presentar la fecha en el resumen.'],
  rationale: 'La recomendación compara únicamente datos sintéticos.',
  uncertainties: [],
  lessons_proposed: [],
};

const impacto = [{ area: 'Reporte de pólizas ficticias', hoy: 'No muestra la vigencia.', debe: 'Mostrarla con el mismo formato que la consulta.' }];
const decision = '¿El reporte muestra la vigencia con el mismo formato que la consulta?';

// El Analista y el Asesor trabajan en equipo: una sola ronda con la pregunta y la decisión del impacto.
const businessSnapshot = () => ({
  workflow_id: 'workflow-pre-synthetic', mode: 'pre_grooming', status: 'interrupted', stage: 'espera_negocio',
  results: {
    analyst: {
      respuesta_markdown: 'Análisis sintético de la póliza ficticia.',
      analisis: { conocida: ['Póliza ficticia TEST-003'], faltante: ['Fecha de vigencia'], supuesta: [], ambigua: [] },
      preguntas: [question], fuentes_consultadas: [], limitaciones: [],
    },
    story: null, review_observations: [],
    technical_assessment: { impacto_negocio: impacto, decision_pendiente: [decision], affected_modules: [], dependencies: [], risks: [], critical_processes: [], consulted_sources: [], uncertainties: ['Evaluación sintética.'] },
  },
  interrupt: {
    interrupt_id: 'interrupt-business-1', kind: 'business_answers',
    payload: {
      impacto_negocio: impacto,
      questions: [{ ...question, origen: 'analista' }, { question_id: 'decision-1', pregunta: decision, origen: 'asesor_tecnico' }],
      max_answer_chars: 1000, max_total_chars: 6000,
    },
  },
});

const poSnapshot = () => ({
  workflow_id: 'workflow-pre-synthetic', mode: 'pre_grooming', status: 'interrupted', stage: 'aprobacion_po',
  results: {
    analyst: {
      respuesta_markdown: 'La vigencia quedó aclarada con una respuesta sintética.',
      analisis: { conocida: ['Vigencia al 2030-12-31'], faltante: [], supuesta: [], ambigua: [] },
      preguntas: [{ ...question, estado: 'respondida' }], fuentes_consultadas: [], limitaciones: [],
    },
    story, review_observations: [],
    technical_assessment: { affected_modules: [], dependencies: [], risks: [], critical_processes: [], consulted_sources: [], uncertainties: ['Evaluación sintética.'] },
  },
  interrupt: {
    interrupt_id: 'interrupt-po-1', kind: 'po_approval',
    payload: { story, decisions: ['aprobar', 'rechazar'], technical_assessment: { uncertainties: ['Evaluación sintética.'] } },
  },
});

const changeSnapshot = () => ({
  workflow_id: 'workflow-change-synthetic', mode: 'post_grooming', status: 'interrupted', stage: 'decision_humana',
  results: { change_recommendation: recommendation },
  interrupt: {
    interrupt_id: 'interrupt-change-1', kind: 'change_decision',
    payload: { change_recommendation: recommendation, decisions: ['aplicar', 'rechazar', 'devolver'] },
  },
});

async function fillRequirement(page) {
  await page.goto('/historias/nueva', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Nombre del requerimiento').fill('Consulta de póliza ficticia TEST-003');
  await page.locator('#req-system').selectOption({ index: 1 });
  await page.locator('#req-codigo-hu').fill('TEST-003');
  await page.getByLabel('Descripción o información de negocio').fill('Consultar vigencia de póliza ficticia TEST-003.');
}

test('pre-grooming presenta análisis y HU, recoge respuestas y solicita aprobación explícita', async ({ page }) => {
  let phase = 0;
  let persisted = false;
  const requestBodies = [];
  await page.route('**/api/workflows**', async (route) => {
    const request = route.request();
    if (request.method() === 'POST' && request.url().endsWith('/api/workflows')) {
      phase = 1;
      return route.fulfill({ status: 201, json: businessSnapshot() });
    }
    if (request.method() === 'POST' && request.url().includes('/resume')) {
      const body = request.postDataJSON();
      requestBodies.push(body);
      if (body.kind === 'business_answers') {
        expect(body.interrupt_id).toBe('interrupt-business-1');
        expect(body.response.answers).toEqual([
          { question_id: question.question_id, answer: '2030-12-31' },
          { question_id: 'decision-1', answer: 'Sí, el mismo formato.' },
        ]);
        phase = 2;
        return route.fulfill({ status: 200, json: poSnapshot() });
      }
      expect(body.kind).toBe('po_approval');
      expect(body.interrupt_id).toBe('interrupt-po-1');
      expect(body.response.decision).toBe('aprobar');
      expect(persisted).toBe(false);
      persisted = true;
      return route.fulfill({
        status: 200,
        json: {
          workflow_id: 'workflow-pre-synthetic', mode: 'pre_grooming', status: 'completed', stage: 'repositorio',
          results: { ...poSnapshot().results, po_decision: { decision: 'aprobar' }, persistence_result: { status: 'saved', story_id: storyId, title: 'Consulta póliza ficticia', approved_at: '2030-12-31T00:00:00Z' }, completion_reason: 'Aprobación sintética registrada.' },
          interrupt: null,
        },
      });
    }
    return route.fulfill({ status: 404, json: { error: { code: 'WORKFLOW_NOT_FOUND' } } });
  });

  await fillRequirement(page);
  await page.getByRole('button', { name: 'Analizar Requerimiento' }).click();
  await expect(page.getByRole('heading', { name: /Preguntas para Negocio/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Lo que encontró el Asesor Técnico' })).toBeVisible();
  await expect(page.getByText('Reporte de pólizas ficticias')).toBeVisible();
  await page.getByLabel(question.pregunta).fill('2030-12-31');
  await page.getByLabel(/El reporte muestra la vigencia/).fill('Sí, el mismo formato.');
  await page.getByRole('button', { name: 'Confirmar y continuar' }).click();
  await expect(page.getByRole('heading', { name: /Historia de Usuario Generada/ })).toBeVisible();
  await expect(page.locator('#story-i-want')).toHaveValue(story.quiero);
  await expect(page.getByRole('heading', { name: /Criterios de Aceptación \(1\)/ })).toBeVisible();
  expect(persisted).toBe(false);

  await page.getByRole('button', { name: /Aprobación del Product Owner/ }).click();
  await page.locator('#workflow-po-decision').selectOption('aprobar');
  await page.getByLabel(/Confirmo que revisé la anonimización/).check();
  await page.getByRole('button', { name: 'Confirmar y continuar' }).click();
  // La confirmación es un modal de la aplicación, no un cuadro del navegador.
  await page.getByRole('alertdialog').getByRole('button', { name: 'Confirmar', exact: true }).click();
  await expect.poll(() => persisted).toBe(true);
  await expect(page).toHaveURL(new RegExp(`/historias/${storyId}$`));
  expect(requestBodies.map((body) => body.kind)).toEqual(['business_answers', 'po_approval']);
  expect(phase).toBe(2);
});

test('post-grooming muestra al Gestor de Cambios y registra solo tras aceptar la recomendación', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(({ id }) => localStorage.setItem('historias_usuario_prototipo', JSON.stringify([
    { id, title: 'Poliza TEST-003', status: 'aprobada', approvedAt: '2030-01-01T00:00:00Z' },
  ])), { id: storyId });
  let persisted = false;
  let decisionRequest;
  await page.route('**/api/analista/repositorio/historias', (route) => route.fulfill({ status: 200, json: [{ id: storyId, titulo: 'Póliza TEST-003', aprobada_en: '2030-01-01T00:00:00Z' }] }));
  await page.route('**/api/analista/repositorio/cambios**', (route) => route.fulfill({ status: 200, json: [] }));
  await page.route('**/api/workflows**', async (route) => {
    const request = route.request();
    if (request.method() === 'POST' && request.url().endsWith('/api/workflows')) {
      expect(request.postDataJSON()).toMatchObject({ mode: 'post_grooming', approved_story_id: storyId });
      return route.fulfill({ status: 201, json: changeSnapshot() });
    }
    if (request.method() === 'POST' && request.url().includes('/resume')) {
      decisionRequest = request.postDataJSON();
      expect(decisionRequest.response.decision).toBe('aplicar');
      expect(persisted).toBe(false);
      persisted = true;
      return route.fulfill({ status: 200, json: {
        workflow_id: 'workflow-change-synthetic', mode: 'post_grooming', status: 'completed', stage: 'aplicacion_decision',
        results: { change_recommendation: recommendation, change_decision: { decision: 'aplicar' }, change_persistence_result: { status: 'recorded', change_id: 'change-synthetic' }, completion_reason: 'Decisión aplicada en el test.' }, interrupt: null,
      } });
    }
    return route.fulfill({ status: 200, json: changeSnapshot() });
  });

  await page.goto(`/historias/${storyId}/solicitar-cambio`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Solicitud de cambio').fill('mostrar fecha de vencimiento');
  await page.getByRole('button', { name: 'Analizar con Gestor de Cambios' }).click();
  await expect(page.getByRole('heading', { name: /Recomendación del Gestor de Cambios/ })).toBeVisible();
  await expect(page.getByText(recommendation.rationale)).toBeVisible();
  expect(persisted).toBe(false);
  await page.locator('#workflow-change-decision').selectOption('aplicar');
  await page.getByRole('button', { name: 'Confirmar y continuar' }).click();
  // La confirmación es un modal de la aplicación, no un cuadro del navegador.
  await page.getByRole('alertdialog').getByRole('button', { name: 'Confirmar', exact: true }).click();
  await expect(page.getByText('Decisi\u00f3n registrada', { exact: true })).toBeVisible();
  expect(persisted).toBe(true);
  expect(decisionRequest).toMatchObject({ kind: 'change_decision', interrupt_id: 'interrupt-change-1' });
});

test('el error 503 mantiene separado el modo manual', async ({ page }) => {
  const manualWrites = [];
  let workflowResumeRequests = 0;
  await page.route('**/api/analista/repositorio/historias', (route) => route.fulfill({ status: 200, json: [{ id: storyId, titulo: 'Póliza TEST-003', aprobada_en: '2030-01-01T00:00:00Z' }] }));
  await page.route('**/api/analista/repositorio/cambios**', async (route) => {
    if (route.request().method() === 'POST') {
      manualWrites.push(route.request().postDataJSON());
      return route.fulfill({ status: 201, json: { solicitud_id: 'manual-synthetic-change' } });
    }
    return route.fulfill({ status: 200, json: [] });
  });
  await page.route('**/api/workflows**', async (route) => {
    if (route.request().method() === 'POST' && route.request().url().includes('/resume')) workflowResumeRequests += 1;
    return route.fulfill({ status: 503, json: { error: { code: 'DEPENDENCY_UNAVAILABLE', message: 'synthetic service failure' } } });
  });
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(({ id }) => localStorage.setItem('historias_usuario_prototipo', JSON.stringify([
    { id, title: 'Poliza TEST-003', status: 'aprobada', approvedAt: '2030-01-01T00:00:00Z' },
  ])), { id: storyId });
  await page.goto(`/historias/${storyId}/solicitar-cambio`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Solicitud de cambio').fill('Cambio ficticio sin agentes');
  await page.getByRole('button', { name: 'Analizar con Gestor de Cambios' }).click();
  await expect(page.getByText(/Un servicio necesario/)).toBeVisible();
  await page.getByRole('button', { name: 'Continuar en modo manual' }).click();
  await expect(page.getByText(/Modo manual alternativo/)).toBeVisible();
  await expect(page.getByRole('button', { name: /Registrar decisi/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Workflow de cambio activo en memoria' })).toHaveCount(0);
  await page.getByRole('button', { name: /Registrar decisi/ }).click();
  await expect(page.getByText(/modo manual/)).toBeVisible();
  expect(manualWrites).toHaveLength(1);
  expect(manualWrites[0]).toMatchObject({ hu_id: storyId, solicitud: 'Cambio ficticio sin agentes' });
  expect(workflowResumeRequests).toBe(0);
});


test('la interfaz identifica un flujo que no se encontró (404)', async ({ page }) => {
  await page.route('**/api/workflows**', async (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ status: 404, json: { error: { code: 'WORKFLOW_NOT_FOUND' } } });
    return route.fulfill({ status: 201, json: businessSnapshot() });
  });
  await fillRequirement(page);
  await page.getByRole('button', { name: 'Analizar Requerimiento' }).click();
  await expect(page.getByRole('heading', { name: /Preguntas para Negocio/ })).toBeVisible();
  await page.getByRole('button', { name: 'Consultar estado' }).click();
  await expect(page.getByText(/El flujo no se encontró/)).toBeVisible();
  await expect(page.getByText(/HTTP 404/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Iniciar un flujo nuevo' })).toBeVisible();
});
