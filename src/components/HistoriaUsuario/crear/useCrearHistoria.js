// Controlador del asistente para crear una historia: estado, efectos y acciones de los 6 pasos.
// Las vistas (un componente por paso) lo leen con useAsistenteHistoria(); no tienen estado propio del flujo.
import { FIRMANTE_VACIO, TIPOS_SOLICITUD, limpiarLista, normalizarCodigoHu, numeroSugerido } from '../../../utils/plantillaHu';
import { MAX_AGENT_MESSAGE_CODEPOINTS, buildAnswersMessage, buildRequirementMessage, codepointLength, describeSources, latestAssistantResponse, latestFailedMessage, mapAnalysis, mergeQuestions, questionsToSend, requirementSignature } from '../../../utils/wizardAgent';
import { SIN_IDENTIFICAR, leerNombreUsuario } from '../../../utils/usuarioActual';
import { avisarCambioPendientes } from '../../../hooks/usePendientes';
import { WorkflowApiError, getWorkflow, resumeWorkflow, retryWorkflow, saveWorkflowDraft, startWorkflow } from '../../../services/workflowApi';
import { addStory, deleteStory, generateStoryId, getStoredStories, getStoryById, guardarHistoria, updateStory } from '../../../utils/storage';
import { aplicarRevision } from '../../../utils/revisiones';
import { bitacoraConNota, bitacoraDelFlujo } from '../../../utils/bitacora';
import { borradorTieneContenido, borrarBorrador, guardarBorrador, leerBorrador } from '../../../utils/borradorAsistente';
import { buildRepositoryPayload, repositorioApi, repositorioErrorMessage } from '../../../services/repositorioApi';
import { criteriosGenericos, criteriosParaEditar, limpiarCriterios, validarCriterios } from '../../../utils/criterios';
import { descargarPdf } from '../../../utils/exportarPdf';
import { descargarWord } from '../../../utils/exportarWord';
import { useAsistenteAnalista } from '../../../hooks/useAsistenteAnalista';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { CAMPO_FORMULARIO, PASO, pasoDelFlujo } from './constantesAsistente';

export function useCrearHistoria() {
  // ── Navegación, retomar y estado general del flujo ───────────────────
  const navigate = useNavigate();
  const ubicacion = useLocation();
  const workflowFromChange = ubicacion.state?.workflowSnapshot ?? null;
  // Retomar una HU en proceso: /historias/nueva?flujo=<id>
  const flujoRetomado = new URLSearchParams(ubicacion.search).get('flujo');
  const prefill = ubicacion.state?.prefill;
  const reanalizarId = ubicacion.state?.reanalizarId;
  // Revisión: el cambio de alcance se analiza sobre la misma HU (mismo código), no como una HU nueva.
  const revisionDeId = ubicacion.state?.revisionDeId;
  const [historiaOrigen] = useState(() => (revisionDeId ? getStoryById(revisionDeId) : null));
  // Borrador automático: solo para una historia nueva (no al reanalizar o prellenar).
  const [borrador] = useState(() => (prefill || reanalizarId || workflowFromChange || flujoRetomado ? null : leerBorrador()));
  const [borradorRecuperado, setBorradorRecuperado] = useState(Boolean(borrador));
  const [activeStep, setActiveStep] = useState(workflowFromChange
    ? (workflowFromChange.interrupt?.kind === 'business_answers' ? PASO.ANALISIS : (pasoDelFlujo(workflowFromChange) ?? PASO.HISTORIA))
    : (borrador?.activeStep ?? PASO.REQUERIMIENTO));
  const [retomando, setRetomando] = useState(Boolean(flujoRetomado));
  const [isGeneratingStory, setIsGeneratingStory] = useState(false);
  const [formError, setFormError] = useState('');
  const [workflowResponse, setWorkflowResponse] = useState(workflowFromChange);
  const [workflowError, setWorkflowError] = useState('');
  const [workflowErrorStatus, setWorkflowErrorStatus] = useState(null);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const workflowOperationRef = useRef(false);
  const workflowControllerRef = useRef(null);

  // Agente Analista: la conversación vive mientras dura el wizard.
  const agent = useAsistenteAnalista();
  const afterSuccessStep = useRef(null);
  const [analyzedSignature, setAnalyzedSignature] = useState(borrador?.analyzedSignature ?? null);
  const [sentAnswers, setSentAnswers] = useState(borrador?.sentAnswers ?? {});

  // ── Paso 1: requerimiento ─────────────────────────────────────────────
  const [requirementName, setRequirementName] = useState(borrador?.requirementName ?? prefill?.name ?? '');
  const [infoType, setInfoType] = useState(borrador?.infoType ?? prefill?.infoType ?? 'Minuta');
  const [description, setDescription] = useState(borrador?.description ?? prefill?.description ?? '');
  const [requestType, setRequestType] = useState(borrador?.requestType ?? prefill?.requestType ?? TIPOS_SOLICITUD[0]);
  const [system, setSystem] = useState(borrador?.system ?? prefill?.system ?? '');
  const [codigoHu, setCodigoHu] = useState(borrador?.codigoHu ?? prefill?.codigoHu ?? '');
  const [requester, setRequester] = useState(borrador?.requester ?? prefill?.requester ?? '');

  // ── Paso 2: análisis del Agente Analista ─────────────────────────────
  const [analysis, setAnalysis] = useState(borrador?.analysis ?? {
    knownData: [],
    missingData: [],
    assumptions: [],
    ambiguities: []
  });

  // ── Paso 3: preguntas del Analista y respuestas de Negocio ───────────
  const [questions, setQuestions] = useState(borrador?.questions ?? prefill?.questions ?? []);

  // ── Paso 5: historia y criterios (del Redactor-Revisor o del modo manual) ──
  const [userStory, setUserStory] = useState(borrador?.userStory ?? {
    asA: '',
    iWant: '',
    soThat: ''
  });
  const [acceptanceCriteria, setAcceptanceCriteria] = useState(borrador?.acceptanceCriteria ?? []);
  const [plantilla, setPlantilla] = useState(borrador?.plantilla ?? {
    number: prefill?.number ?? '',
    benefits: prefill?.benefits?.length ? prefill.benefits : [''],
    signers: { ...FIRMANTE_VACIO, ...(prefill?.signers || {}) },
  });
  const [beneficiosPropuestos, setBeneficiosPropuestos] = useState(false);
  const actualizarPlantilla = (cambio) => setPlantilla((previo) => ({ ...previo, ...cambio }));
  const [descargaError, setDescargaError] = useState('');
  const [pendingQuestions, setPendingQuestions] = useState(borrador?.pendingQuestions ?? []);

  // ── Paso 6: nota para la bitácora y aprobación del Product Owner ─────
  const [observations, setObservations] = useState(borrador?.observations ?? '');
  const [confirmAnonymized, setConfirmAnonymized] = useState(false);
  const [approvalError, setApprovalError] = useState('');
  const [isApproving, setIsApproving] = useState(false);

  // Guarda el avance cada vez que cambia algo (solo en historias nuevas).
  useEffect(() => {
    if (prefill || reanalizarId || workflowResponse) return;
    const estado = {
      activeStep, requirementName, infoType, description, requestType, system, codigoHu, requester,
      analyzedSignature, sentAnswers, analysis, questions, userStory, acceptanceCriteria, plantilla,
      pendingQuestions, observations,
    };
    if (borradorTieneContenido(estado)) guardarBorrador(estado);
  }, [activeStep, requirementName, infoType, description, requestType, system, codigoHu, requester,
    analyzedSignature, sentAnswers, analysis, questions, userStory, acceptanceCriteria, plantilla,
    pendingQuestions, observations, prefill, reanalizarId, workflowResponse]);

  const legacyAgentResponse = useMemo(() => latestAssistantResponse(agent.messages), [agent.messages]);
  const agentResponse = workflowResponse?.results?.analyst ?? legacyAgentResponse;
  const failedMessage = useMemo(() => latestFailedMessage(agent.messages), [agent.messages]);
  const isProcessing = agent.isProcessing || isGeneratingStory || workflowBusy;
  const unsentQuestions = questionsToSend(questions, sentAnswers);
  const agentError = failedMessage?.error || agent.error;
  const agentReady = Boolean(agentResponse?.listo_para_redactor) && unsentQuestions.length === 0;
  const esperaRespuesta = workflowResponse?.interrupt?.kind === 'business_answers';
  // Con workflow activo, las preguntas pendientes son las que el backend pide en la interrupción.
  const pendingCount = workflowResponse
    ? (esperaRespuesta ? (workflowResponse.interrupt.payload?.questions ?? []).length : 0)
    : questions.filter((q) => q.status === 'pendiente').length;
  const workflowSinSiguientePaso = Boolean(workflowResponse) && !esperaRespuesta && !agentReady
    && !workflowResponse?.results?.story && !workflowResponse?.results?.technical_assessment;
  const guardado = workflowResponse?.guardado ?? null;
  const sources = describeSources(agentResponse?.fuentes_consultadas);

  const setWorkflowSnapshot = (snapshot) => {
    setWorkflowResponse(snapshot);
    setWorkflowError('');
    setWorkflowErrorStatus(null);
    const analystResult = snapshot?.results?.analyst;
    if (analystResult) {
      setAnalysis(mapAnalysis(analystResult.analisis));
      setQuestions((previous) => mergeQuestions(previous, analystResult.preguntas));
    }
    const activeQuestions = snapshot?.interrupt?.payload?.questions;
    if (Array.isArray(activeQuestions)) {
      setQuestions((previous) => mergeQuestions(previous, activeQuestions));
      setPendingQuestions(activeQuestions.map((question) => question.pregunta));
    } else if (snapshot?.interrupt?.kind !== 'business_answers') {
      setPendingQuestions([]);
    }
    const story = snapshot?.results?.story ?? snapshot?.interrupt?.payload?.story;
    if (story) {
      setUserStory({ asA: story.como, iWant: story.quiero, soThat: story.para });
      setAcceptanceCriteria((story.criterios ?? []).map((criterion) => ({
        // La etiqueta ya dice «Dado que»: no se repite el «que» del texto.
        given: String(criterion.dado ?? '').replace(/^\s*que\s+/i, ''),
        when: criterion.cuando,
        then: criterion.entonces,
      })));
    }
    // Los beneficios que propuso el Analista se cargan si la persona aún no escribió los suyos.
    const beneficioFlujo = limpiarLista(snapshot?.results?.analyst?.beneficios ?? []);
    if (story && beneficioFlujo.length > 0) {
      setPlantilla((previo) => {
        if (previo.benefits.some((beneficio) => beneficio.trim())) return previo;
        setBeneficiosPropuestos(true);
        return { ...previo, benefits: beneficioFlujo };
      });
    }
    const paso = pasoDelFlujo(snapshot);
    if (paso) setActiveStep(paso);
  };

  // Al retomar se recupera también el formulario del paso 1 (nombre, sistema, código...).
  const restaurarFormulario = (formulario = {}) => {
    const setter = {
      requirementName: setRequirementName, infoType: setInfoType, requestType: setRequestType, system: setSystem,
      codigoHu: setCodigoHu, requester: setRequester, description: setDescription,
    };
    Object.entries(formulario).forEach(([campo, valor]) => {
      if (setter[campo] && typeof valor === 'string') setter[campo](valor);
    });
  };

  const formularioActual = () => Object.fromEntries(CAMPO_FORMULARIO.map((campo) => [campo, String({
    requirementName, infoType, requestType, system, codigoHu: normalizarCodigoHu(codigoHu), requester, description,
  }[campo] ?? '')]));

  const datosParaRetomar = () => ({
    titulo: requirementName.trim().slice(0, 200) || undefined,
    creado_por: (leerNombreUsuario() || '').slice(0, 120) || undefined,
    formulario: formularioActual(),
  });

  const runWorkflowRequest = async (operation) => {
    if (workflowOperationRef.current) return null;
    workflowOperationRef.current = true;
    workflowControllerRef.current?.abort();
    const controller = new AbortController();
    workflowControllerRef.current = controller;
    setWorkflowBusy(true);
    setWorkflowError('');
    setWorkflowErrorStatus(null);
    try {
      return await operation(controller.signal);
    } catch (cause) {
      if (cause?.name === 'AbortError') return null;
      setWorkflowError(cause instanceof WorkflowApiError ? cause.message : 'No se pudo comunicar con el servicio del workflow.');
      setWorkflowErrorStatus(cause?.status || null);
      return null;
    } finally {
      workflowOperationRef.current = false;
      workflowControllerRef.current = null;
      setWorkflowBusy(false);
    }
  };

  const refreshWorkflow = async () => {
    if (!workflowResponse?.workflow_id) return;
    const snapshot = await runWorkflowRequest((signal) => getWorkflow(workflowResponse.workflow_id, { signal }));
    if (snapshot) setWorkflowSnapshot(snapshot);
  };

  const startFreshWorkflow = async () => {
    if (!requirementName.trim() || !description.trim()) {
      setWorkflowError('Complete el nombre y la descripción del requerimiento antes de iniciar otro flujo.');
      return;
    }
    const requirement = buildRequirementMessage(
      { name: requirementName, infoType, description, system, codigoHu: normalizarCodigoHu(codigoHu), requestType },
    );
    const snapshot = await runWorkflowRequest((signal) => startWorkflow({ mode: 'pre_grooming', requirement, ...datosParaRetomar() }, { signal }));
    if (snapshot) setWorkflowSnapshot(snapshot);
  };

  // Guarda respuestas escritas y no enviadas, para terminarlas otro día.
  const guardarRespuestasSinEnviar = async (respuestas) => {
    if (!workflowResponse?.workflow_id) return false;
    const limpias = Object.fromEntries(Object.entries(respuestas).filter(([, valor]) => String(valor).trim()));
    // Es rápido y no ejecuta agentes: no se muestra la pantalla de espera, para no perder lo que está escrito.
    try {
      await saveWorkflowDraft(workflowResponse.workflow_id, limpias);
    } catch (cause) {
      setWorkflowError(cause instanceof WorkflowApiError ? cause.message : 'No se pudieron guardar las respuestas.');
      setWorkflowErrorStatus(cause?.status || null);
      return false;
    }
    setWorkflowResponse((actual) => (actual ? { ...actual, guardado: { ...(actual.guardado ?? {}), borrador_respuestas: limpias } } : actual));
    return true;
  };

  // Vuelve a ejecutar el paso que falló, desde el último punto guardado.
  const reintentarFlujo = async () => {
    if (!workflowResponse?.workflow_id) return;
    const snapshot = await runWorkflowRequest((signal) => retryWorkflow(workflowResponse.workflow_id, { signal }));
    if (snapshot) setWorkflowSnapshot(snapshot);
  };

  // Tras un error, el estado guardado dice si se puede reintentar; se consulta sin ocultar el error.
  const actualizarTrasError = async (workflowId) => {
    try {
      const snapshot = await getWorkflow(workflowId);
      setWorkflowResponse(snapshot);
    } catch (cause) {
      console.warn('No se pudo consultar el estado del flujo después del error:', cause?.message ?? cause);
    }
  };

  const resumeWorkflowInterrupt = async (pedido) => {
    if (!workflowResponse?.workflow_id || !pedido?.interrupt_id) return;
    const workflowId = workflowResponse.workflow_id;
    const resultadoPrevio = workflowResponse.results;
    // La nota del PO al aprobar viaja con la aprobación y queda en la bitácora de la HU.
    const notaAprobacion = observations.trim().slice(0, 1000);
    const body = pedido.kind === 'po_approval' && pedido.response?.decision === 'aprobar' && notaAprobacion
      ? { ...pedido, response: { ...pedido.response, reason: notaAprobacion } }
      : pedido;
    const snapshot = await runWorkflowRequest((signal) => resumeWorkflow(workflowId, body, { signal }));
    if (!snapshot) {
      await actualizarTrasError(workflowId);
      return;
    }
    setWorkflowSnapshot(snapshot);
    avisarCambioPendientes();
    const persistence = snapshot.results?.persistence_result;
    if (body.kind === 'po_approval' && body.response?.decision === 'aprobar' && persistence?.status === 'saved') {
      const id = persistence.story_id;
      const previa = getStoryById(id);
      const hoy = new Date().toISOString().slice(0, 10);
      const persona = leerNombreUsuario() || SIN_IDENTIFICAR;
      const resultado = { ...resultadoPrevio, ...snapshot.results };
      const approved = {
        ...baseStoryData(),
        // Bitácora: decisiones, supuestos, dependencias, pendientes técnicos, devoluciones y la nota del PO.
        // Las observaciones de control de calidad del Redactor-Revisor no se guardan en la HU.
        bitacora: [
          ...bitacoraConNota(historiaOrigen ?? (reanalizarId ? getStoryById(reanalizarId) : null), ''),
          ...bitacoraDelFlujo(resultado, { fecha: hoy, persona, notaAprobacion }),
        ],
        id,
        status: 'aprobada',
        approvedAt: persistence.approved_at ?? new Date().toISOString(),
        repositorySynced: true,
        analisisDesactualizado: false,
        respuestasNuevas: false,
        criteriosModificados: false,
      };
      // El Repositorio de HU ya lo escribió el backend; aquí se guarda la copia de trabajo que muestran
      // el listado y el detalle, también en la base para que la sincronización no la borre.
      guardarHistoria({
        ...(previa ?? { createdAt: hoy, createdBy: leerNombreUsuario() }),
        ...approved,
        updatedAt: hoy,
        updatedBy: leerNombreUsuario(),
      });
      borrarBorrador();
      navigate(`/historias/${id}`);
    } else if (body.kind === 'po_approval' && body.response?.decision === 'aprobar'
      && persistence?.status === 'failed') {
      setWorkflowError(snapshot.results?.completion_reason || 'El backend no pudo persistir la HU aprobada.');
    }
  };

  useEffect(() => () => workflowControllerRef.current?.abort(), []);

  useEffect(() => {
    if (!workflowFromChange) return;
    setWorkflowSnapshot(workflowFromChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowFromChange?.workflow_id]);

  // Retomar una HU en proceso: se carga el flujo guardado y se abre en el paso donde quedó.
  useEffect(() => {
    if (!flujoRetomado) return;
    (async () => {
      const snapshot = await runWorkflowRequest((signal) => getWorkflow(flujoRetomado, { signal }));
      if (snapshot) {
        restaurarFormulario(snapshot.guardado?.formulario);
        setAnalyzedSignature('retomado');
        setWorkflowSnapshot(snapshot);
        if (!pasoDelFlujo(snapshot)) setActiveStep(PASO.PREGUNTAS);
      }
      setRetomando(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flujoRetomado]);

  // Cada respuesta nueva del agente actualiza el análisis y las preguntas.
  const turnId = agentResponse?.turn_id;
  useEffect(() => {
    if (!agentResponse) return;
    setAnalysis(mapAnalysis(agentResponse.analisis));
    setQuestions((previous) => mergeQuestions(previous, agentResponse.preguntas));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [turnId]);

  const runAgentTurn = async (message, targetStep) => {
    afterSuccessStep.current = targetStep;
    const ok = await agent.sendMessage(message);
    if (ok) setActiveStep(targetStep);
    return ok;
  };

  // Paso 1 → el Agente Analista analiza el requerimiento.
  const handleAnalyzeRequirement = async (e) => {
    e.preventDefault();
    setFormError('');
    if (!requirementName.trim() || !description.trim()) {
      setFormError('Complete el nombre y la descripción del requerimiento.');
      return;
    }
    if (!system.trim() || !normalizarCodigoHu(codigoHu)) {
      setFormError('Indique el sistema y el código de HU: se usan para numerar la historia y para el documento Word.');
      return;
    }
    const signature = requirementSignature({ name: requirementName, infoType, description });
    if (agentResponse && signature === analyzedSignature) {
      setActiveStep(2);
      return;
    }
    const message = buildRequirementMessage(
      { name: requirementName, infoType, description, system, codigoHu: normalizarCodigoHu(codigoHu), requestType },
      { isUpdate: Boolean(agentResponse) },
    );
    if (codepointLength(message) > MAX_AGENT_MESSAGE_CODEPOINTS) {
      setFormError(`El requerimiento supera el máximo de ${MAX_AGENT_MESSAGE_CODEPOINTS} caracteres. Resuma o divida la información.`);
      return;
    }

    const snapshot = await runWorkflowRequest((signal) => startWorkflow({
      mode: 'pre_grooming',
      requirement: message,
      ...datosParaRetomar(),
    }, { signal }));
    if (snapshot) {
      setWorkflowSnapshot(snapshot);
      setAnalyzedSignature(signature);
      if (snapshot.status === 'failed') {
        setWorkflowError(snapshot.results?.completion_reason || 'El workflow no pudo completar el análisis. Puede continuar con el modo manual.');
      }
      return;
    }

    setWorkflowResponse(null);
    setWorkflowError((current) => current || 'El servicio de workflow no respondió. Se continuará con el Analista existente en modo manual.');
    // Al reanalizar una historia guardada, las respuestas de Negocio ya registradas viajan con el requerimiento.
    const respuestas = agentResponse ? '' : buildAnswersMessage(questions, sentAnswers);
    const mensajeCompleto = respuestas ? `${message}\n\n${respuestas}` : message;
    if (codepointLength(mensajeCompleto) > MAX_AGENT_MESSAGE_CODEPOINTS) {
      setFormError(`El requerimiento con sus respuestas supera el máximo de ${MAX_AGENT_MESSAGE_CODEPOINTS} caracteres. Resuma la información.`);
      return;
    }
    const enviadas = Object.fromEntries(questionsToSend(questions, sentAnswers).map((q) => [q.id, q.answer.trim()]));
    const ok = await runAgentTurn(mensajeCompleto, 2);
    if (ok) {
      setAnalyzedSignature(signature);
      if (respuestas) setSentAnswers((previous) => ({ ...previous, ...enviadas }));
    }
  };

  // Paso 3 → las respuestas de Negocio vuelven al Analista.
  const handleSendAnswers = async () => {
    if (workflowResponse?.interrupt?.kind === 'business_answers') {
      const pending = workflowResponse.interrupt.payload?.questions ?? [];
      const unanswered = pending.filter((question) => {
        const local = questions.find((item) => item.id === question.question_id);
        return !String(local?.answer ?? '').trim();
      });
      if (unanswered.length) {
        setFormError('Responda todas las preguntas pendientes de Negocio antes de continuar.');
        return;
      }
      const resumeBody = {
        kind: 'business_answers',
        interrupt_id: workflowResponse.interrupt.interrupt_id,
        response: {
          answers: pending.map((question) => ({
            question_id: question.question_id,
            answer: questions.find((item) => item.id === question.question_id).answer.trim(),
          })),
        },
      };
      setFormError('');
      const workflowId = workflowResponse.workflow_id;
      const snapshot = await runWorkflowRequest((signal) => resumeWorkflow(workflowId, resumeBody, { signal }));
      if (snapshot) setWorkflowSnapshot(snapshot);
      else await actualizarTrasError(workflowId);
      return;
    }
    const respuestas = buildAnswersMessage(questions, sentAnswers);
    if (!respuestas) return;
    // Si se recuperó un borrador, el agente ya no tiene la conversación: se le reenvía el requerimiento.
    const message = agentResponse
      ? respuestas
      : `${buildRequirementMessage(
        { name: requirementName, infoType, description, system, codigoHu: normalizarCodigoHu(codigoHu), requestType },
        { isUpdate: false },
      )}\n\n${respuestas}`;
    if (codepointLength(message) > MAX_AGENT_MESSAGE_CODEPOINTS) {
      setFormError('Las respuestas superan el máximo permitido por envío. Envíe primero algunas y luego el resto.');
      return;
    }
    setFormError('');
    const snapshot = Object.fromEntries(questionsToSend(questions, sentAnswers).map((q) => [q.id, q.answer.trim()]));
    const ok = await runAgentTurn(message, 3);
    if (ok) setSentAnswers((previous) => ({ ...previous, ...snapshot }));
  };

  const handleRetryAgent = async () => {
    if (!failedMessage) return;
    const ok = await agent.retryMessage(failedMessage.id);
    if (!ok) return;
    if (afterSuccessStep.current) setActiveStep(afterSuccessStep.current);
    if (afterSuccessStep.current === 2) {
      setAnalyzedSignature(requirementSignature({ name: requirementName, infoType, description }));
    }
  };

  const handleRestartAnalysis = async () => {
    await agent.resetConversation();
    setAnalysis({ knownData: [], missingData: [], assumptions: [], ambiguities: [] });
    setQuestions([]);
    setSentAnswers({});
    setAnalyzedSignature(null);
    setUserStory({ asA: '', iWant: '', soThat: '' });
    setAcceptanceCriteria([]);
    setPendingQuestions([]);
    setWorkflowResponse(null);
    setWorkflowError('');
    setFormError('');
    setActiveStep(1);
  };

  // Modo manual (sin el flujo de agentes): borrador de partida para que la persona lo complete.
  const handleGenerateStory = () => {
    if (workflowResponse) {
      if (workflowResponse.interrupt?.kind === 'business_answers' || !workflowResponse.results?.story) {
        setFormError('El Analista tiene preguntas de Negocio pendientes; deben responderse y enviarse al workflow primero.');
        return;
      }
      setActiveStep(PASO.HISTORIA);
      return;
    }
    if (pendingCount > 0 || unsentQuestions.length > 0) {
      setFormError('No avance a la HU mientras queden preguntas de Negocio sin respuesta y enviadas al Analista.');
      return;
    }
    setIsGeneratingStory(true);

    setTimeout(() => {
      // Los beneficios los propone el agente; solo se cargan si la persona aún no escribió los suyos.
      const beneficioAgente = limpiarLista(agentResponse?.beneficios || []);
      const sinBeneficioEscrito = !plantilla.benefits.some((beneficio) => beneficio.trim());
      if (beneficioAgente.length > 0 && sinBeneficioEscrito) {
        setPlantilla((previo) => ({ ...previo, benefits: beneficioAgente }));
        setBeneficiosPropuestos(true);
      }

      if (historiaOrigen) {
        // Revisión: se parte de la HU vigente para que la persona ajuste solo lo que cambia.
        setUserStory({ asA: '', iWant: '', soThat: '', ...(historiaOrigen.userStory ?? {}) });
        setAcceptanceCriteria(criteriosParaEditar(historiaOrigen.acceptanceCriteria));
      } else {
        // Build generated user story
        setUserStory({
          asA: 'Usuario / Ejecutivo del Sistema',
          iWant: `Gestionar ${requirementName.toLowerCase()} de forma automatizada`,
          soThat: beneficioAgente[0] || 'pueda mantener actualizados los registros de negocio y garantizar la consistencia operativa.'
        });

        // Criterios genéricos de partida (sin datos del requerimiento) hasta que exista el Agente Redactor-Revisor.
        setAcceptanceCriteria(criteriosGenericos());
      }

      // Preguntas que siguen sin respuesta
      setPendingQuestions(
        questions
          .filter((q) => q.status === 'pendiente' || !q.answer.trim())
          .map((q) => q.question)
      );

      setIsGeneratingStory(false);
      setActiveStep(PASO.HISTORIA);
    }, 800);
  };

  // Respuesta de Negocio escrita en una pregunta.
  const handleQuestionAnswerChange = (qId, newAnswer) => {
    setQuestions((prev) =>
      prev.map((q) => {
        if (q.id === qId) {
          return {
            ...q,
            answer: newAnswer,
            status: newAnswer.trim() ? 'respondida' : 'pendiente'
          };
        }
        return q;
      })
    );
  };

  // La persona edita la historia (Como / Quiero / Para).
  const handleUserStoryChange = (field, value) => setUserStory((prev) => ({ ...prev, [field]: value }));

  // Al llegar a la historia se propone el número según el código de HU y las historias ya guardadas.
  useEffect(() => {
    if (activeStep !== PASO.HISTORIA) return;
    setPlantilla((previo) => (previo.number.trim()
      ? previo
      : { ...previo, number: numeroSugerido(codigoHu, getStoredStories()) }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeStep]);

  const handleDownloadWord = async () => {
    setDescargaError('');
    try {
      await descargarWord({ id: '', ...baseStoryData() });
    } catch (error) {
      console.error('No se pudo generar el documento Word:', error);
      setDescargaError('No se pudo generar el documento Word. Intente de nuevo.');
    }
  };

  const handleDownloadPdf = async () => {
    setDescargaError('');
    try {
      await descargarPdf({ id: '', ...baseStoryData() });
    } catch (error) {
      console.error('No se pudo generar el documento PDF:', error);
      setDescargaError('No se pudo generar el documento PDF. Intente de nuevo.');
    }
  };

  const criteriosValidacion = validarCriterios(acceptanceCriteria);
  const storyIsComplete = Boolean(userStory.asA.trim() && userStory.iWant.trim() && userStory.soThat.trim())
    && criteriosValidacion.ok;
  const workflowStory = workflowResponse?.results?.story;
  const workflowStoryEdited = Boolean(workflowStory && (
    userStory.asA !== workflowStory.como
    || userStory.iWant !== workflowStory.quiero
    || userStory.soThat !== workflowStory.para
    || JSON.stringify(acceptanceCriteria.map(({ given, when, then }) => ({ dado: given, cuando: when, entonces: then })))
      !== JSON.stringify(workflowStory.criterios.map((criterio) => ({
        ...criterio, dado: String(criterio.dado ?? '').replace(/^\s*que\s+/i, ''),
      })))
  ));

  const baseStoryData = () => ({
    title: requirementName,
    type: 'Nueva Funcionalidad',
    requirementName,
    infoType,
    requestType,
    system: system.trim(),
    codigoHu: normalizarCodigoHu(codigoHu),
    requester: requester.trim(),
    number: plantilla.number.trim(),
    benefits: limpiarLista(plantilla.benefits),
    signers: plantilla.signers,
    description,
    analysis,
    questions,
    userStory,
    acceptanceCriteria: limpiarCriterios(acceptanceCriteria),
    pendingQuestions,
    // La nota del paso 5 se suma a la bitácora que ya tenga la HU (la que se revisa o se vuelve a analizar).
    bitacora: bitacoraConNota(historiaOrigen ?? (reanalizarId ? getStoryById(reanalizarId) : null), observations, { autor: leerNombreUsuario() || SIN_IDENTIFICAR }),
  });

  // Guardar sin aprobar: queda como borrador del analista
  const handleSaveDraft = () => {
    const unanswered = questions
      .filter((question) => question.status === 'pendiente' || !String(question.answer ?? '').trim())
      .map((question) => question.question);
    const sinAnalizar = activeStep === PASO.REQUERIMIENTO && !agentResponse;
    const datos = {
      ...baseStoryData(),
      pendingQuestions: unanswered,
      status: sinAnalizar ? 'borrador' : (unanswered.length > 0 ? 'pendiente_de_informacion' : 'revisada'),
    };
    // Re-análisis de un borrador existente: se actualiza la misma HU en lugar de crear otra.
    const saved = (reanalizarId && updateStory(reanalizarId, { ...datos, analisisDesactualizado: false, respuestasNuevas: false, criteriosModificados: false })) || addStory(datos);
    borrarBorrador();
    navigate(`/historias/${saved.id}`);
  };

  // El Product Owner aprueba: la HU pasa al Repositorio de HU (memoria de largo plazo)
  const handleApproveStory = async () => {
    setApprovalError('');
    if (!confirmAnonymized) {
      setApprovalError('Confirme que la historia no contiene datos personales reales.');
      return;
    }
    setIsApproving(true);
    const id = historiaOrigen ? historiaOrigen.id : generateStoryId();
    try {
      await repositorioApi.saveStory(buildRepositoryPayload({
        id, code: plantilla.number, title: requirementName, infoType, description, userStory, acceptanceCriteria, questions,
      }));
    } catch (cause) {
      setApprovalError(repositorioErrorMessage(cause));
      setIsApproving(false);
      return;
    }
    const datosAprobados = {
      ...baseStoryData(),
      status: 'aprobada',
      approvedAt: new Date().toISOString(),
      repositorySynced: true,
      analisisDesactualizado: false,
      respuestasNuevas: false,
      criteriosModificados: false,
    };
    // Revisión: la misma HU pasa a la revisión siguiente y la anterior queda en su historial.
    const saved = historiaOrigen
      ? updateStory(historiaOrigen.id, aplicarRevision(historiaOrigen, datosAprobados, prefill?.motivoRevision)) ?? historiaOrigen
      : addStory({ ...datosAprobados, id });
    if (reanalizarId) deleteStory(reanalizarId);
    borrarBorrador();
    navigate(`/historias/${saved.id}`);
  };

  return {
    navigate,
    ubicacion,
    workflowFromChange,
    flujoRetomado,
    prefill,
    reanalizarId,
    revisionDeId,
    historiaOrigen,
    borrador,
    borradorRecuperado,
    setBorradorRecuperado,
    activeStep,
    setActiveStep,
    retomando,
    setRetomando,
    isGeneratingStory,
    setIsGeneratingStory,
    formError,
    setFormError,
    workflowResponse,
    setWorkflowResponse,
    workflowError,
    setWorkflowError,
    workflowErrorStatus,
    setWorkflowErrorStatus,
    workflowBusy,
    setWorkflowBusy,
    workflowOperationRef,
    workflowControllerRef,
    agent,
    afterSuccessStep,
    analyzedSignature,
    setAnalyzedSignature,
    sentAnswers,
    setSentAnswers,
    requirementName,
    setRequirementName,
    infoType,
    setInfoType,
    description,
    setDescription,
    requestType,
    setRequestType,
    system,
    setSystem,
    codigoHu,
    setCodigoHu,
    requester,
    setRequester,
    analysis,
    setAnalysis,
    questions,
    setQuestions,
    userStory,
    setUserStory,
    acceptanceCriteria,
    setAcceptanceCriteria,
    plantilla,
    setPlantilla,
    beneficiosPropuestos,
    setBeneficiosPropuestos,
    actualizarPlantilla,
    descargaError,
    setDescargaError,
    pendingQuestions,
    setPendingQuestions,
    observations,
    setObservations,
    confirmAnonymized,
    setConfirmAnonymized,
    approvalError,
    setApprovalError,
    isApproving,
    setIsApproving,
    legacyAgentResponse,
    agentResponse,
    failedMessage,
    isProcessing,
    unsentQuestions,
    agentError,
    agentReady,
    esperaRespuesta,
    pendingCount,
    workflowSinSiguientePaso,
    guardado,
    sources,
    setWorkflowSnapshot,
    restaurarFormulario,
    formularioActual,
    datosParaRetomar,
    runWorkflowRequest,
    refreshWorkflow,
    startFreshWorkflow,
    guardarRespuestasSinEnviar,
    reintentarFlujo,
    actualizarTrasError,
    resumeWorkflowInterrupt,
    turnId,
    runAgentTurn,
    handleAnalyzeRequirement,
    handleSendAnswers,
    handleRetryAgent,
    handleRestartAnalysis,
    handleGenerateStory,
    handleQuestionAnswerChange,
    handleUserStoryChange,
    handleDownloadWord,
    handleDownloadPdf,
    criteriosValidacion,
    storyIsComplete,
    workflowStory,
    workflowStoryEdited,
    baseStoryData,
    handleSaveDraft,
    handleApproveStory,
  };
}
