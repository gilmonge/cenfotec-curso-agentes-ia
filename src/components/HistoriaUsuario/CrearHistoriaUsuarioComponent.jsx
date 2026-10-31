import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { PasosComponent } from '../Comun/PasosComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { CampoTextoComponent } from '../Comun/CampoTextoComponent';
import { AreaTextoComponent } from '../Comun/AreaTextoComponent';
import { SelectorComponent } from '../Comun/SelectorComponent';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { TarjetaAnalisisComponent } from './TarjetaAnalisisComponent';
import { TarjetaPreguntaComponent } from './TarjetaPreguntaComponent';
import { MarkdownAsistenteComponent } from '../AsistenteAnalista/MarkdownAsistenteComponent';
import { useAsistenteAnalista } from '../../hooks/useAsistenteAnalista';
import { borrarBorrador, borradorTieneContenido, guardarBorrador, leerBorrador } from '../../utils/borradorAsistente';
import { addStory, deleteStory, generateStoryId, getStoredStories, getStoryById, updateStory } from '../../utils/storage';
import { CamposPlantillaComponent } from './CamposPlantillaComponent';
import { descargarWord } from '../../utils/exportarWord';
import { descargarPdf } from '../../utils/exportarPdf';
import { FIRMANTE_VACIO, TIPOS_SOLICITUD, limpiarLista, normalizarCodigoHu, numeroSugerido } from '../../utils/plantillaHu';
import { criteriosGenericos, criteriosParaEditar, limpiarCriterios, validarCriterios } from '../../utils/criterios';
import { aplicarRevision, etiquetaRevision, numeroRevision } from '../../utils/revisiones';
import { bitacoraConNota } from '../../utils/bitacora';
import { SIN_IDENTIFICAR, leerNombreUsuario } from '../../utils/usuarioActual';
import { OPCION_AREA_SOLICITANTE, OPCION_SISTEMA, armarOpcion } from '../../data/catalogos';
import { EditorCriteriosComponent } from './EditorCriteriosComponent';
import { buildRepositoryPayload, repositorioApi, repositorioErrorMessage } from '../../services/repositorioApi';
import {
  MAX_AGENT_MESSAGE_CODEPOINTS,
  buildAnswersMessage,
  buildRequirementMessage,
  codepointLength,
  describeSources,
  latestAssistantResponse,
  latestFailedMessage,
  mapAnalysis,
  mergeQuestions,
  questionsToSend,
  requirementSignature,
} from '../../utils/wizardAgent';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  FileCode,
  ListFilter,
  HelpCircle,
  Save,
  Clock,
  RotateCcw,
  X,
  FileDown
} from 'lucide-react';

const STEPPER_STEPS = [
  { id: 1, label: 'Requerimiento' },
  { id: 2, label: 'Análisis del agente' },
  { id: 3, label: 'Preguntas a Negocio' },
  { id: 4, label: 'Historia (borrador)' },
  { id: 5, label: 'Aprobación del PO' }
];

const INFO_TYPE_OPTIONS = [
  { value: 'Minuta', label: 'Minuta de reunión' },
  { value: 'Correo', label: 'Correo' },
  { value: 'Incidente', label: 'Incidente' },
  { value: 'Solicitud de cambio', label: 'Solicitud de cambio (nueva HU)' },
  { value: 'Descripción libre', label: 'Descripción libre' },
  { value: 'Notas de conversación', label: 'Notas de conversación' },
  { value: 'Otro', label: 'Otro formato' }
];

const CrearHistoriaUsuarioContenido = () => {
  const navigate = useNavigate();
  const ubicacion = useLocation();
  const prefill = ubicacion.state?.prefill;
  const reanalizarId = ubicacion.state?.reanalizarId;
  // Revisión: el cambio de alcance se analiza sobre la misma HU (mismo código), no como una HU nueva.
  const revisionDeId = ubicacion.state?.revisionDeId;
  const [historiaOrigen] = useState(() => (revisionDeId ? getStoryById(revisionDeId) : null));
  // Borrador automático: solo para una historia nueva (no al reanalizar o prellenar).
  const [borrador] = useState(() => (prefill || reanalizarId ? null : leerBorrador()));
  const [borradorRecuperado, setBorradorRecuperado] = useState(Boolean(borrador));
  const [activeStep, setActiveStep] = useState(borrador?.activeStep ?? 1);
  const [isGeneratingStory, setIsGeneratingStory] = useState(false);
  const [formError, setFormError] = useState('');

  // Agente Analista: la conversación vive mientras dura el wizard.
  const agent = useAsistenteAnalista();
  const afterSuccessStep = useRef(null);
  const [analyzedSignature, setAnalyzedSignature] = useState(borrador?.analyzedSignature ?? null);
  const [sentAnswers, setSentAnswers] = useState(borrador?.sentAnswers ?? {});

  // Step 1: Requerimiento state
  const [requirementName, setRequirementName] = useState(borrador?.requirementName ?? prefill?.name ?? '');
  const [infoType, setInfoType] = useState(borrador?.infoType ?? prefill?.infoType ?? 'Minuta');
  const [description, setDescription] = useState(borrador?.description ?? prefill?.description ?? '');
  const [requestType, setRequestType] = useState(borrador?.requestType ?? prefill?.requestType ?? TIPOS_SOLICITUD[0]);
  const [system, setSystem] = useState(borrador?.system ?? prefill?.system ?? '');
  const [codigoHu, setCodigoHu] = useState(borrador?.codigoHu ?? prefill?.codigoHu ?? '');
  const [requester, setRequester] = useState(borrador?.requester ?? prefill?.requester ?? '');

  // Step 2: análisis del agente
  const [analysis, setAnalysis] = useState(borrador?.analysis ?? {
    knownData: [],
    missingData: [],
    assumptions: [],
    ambiguities: []
  });

  // Step 3: preguntas del agente + respuestas de Negocio
  const [questions, setQuestions] = useState(borrador?.questions ?? prefill?.questions ?? []);

  // Step 4: Generated User Story & Criteria state (borrador simulado)
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

  // Step 5: Observations state
  const [observations, setObservations] = useState(borrador?.observations ?? '');
  const [confirmAnonymized, setConfirmAnonymized] = useState(false);
  const [approvalError, setApprovalError] = useState('');
  const [isApproving, setIsApproving] = useState(false);

  // Guarda el avance cada vez que cambia algo (solo en historias nuevas).
  useEffect(() => {
    if (prefill || reanalizarId) return;
    const estado = {
      activeStep, requirementName, infoType, description, requestType, system, codigoHu, requester,
      analyzedSignature, sentAnswers, analysis, questions, userStory, acceptanceCriteria, plantilla,
      pendingQuestions, observations,
    };
    if (borradorTieneContenido(estado)) guardarBorrador(estado);
  }, [activeStep, requirementName, infoType, description, requestType, system, codigoHu, requester,
    analyzedSignature, sentAnswers, analysis, questions, userStory, acceptanceCriteria, plantilla,
    pendingQuestions, observations, prefill, reanalizarId]);

  const agentResponse = useMemo(() => latestAssistantResponse(agent.messages), [agent.messages]);
  const failedMessage = useMemo(() => latestFailedMessage(agent.messages), [agent.messages]);
  const isProcessing = agent.isProcessing || isGeneratingStory;
  const unsentQuestions = questionsToSend(questions, sentAnswers);
  const pendingCount = questions.filter((q) => q.status === 'pendiente').length;
  const agentError = failedMessage?.error || agent.error;
  const agentReady = Boolean(agentResponse?.listo_para_redactor) && unsentQuestions.length === 0;
  const sources = describeSources(agentResponse?.fuentes_consultadas);

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

  // Step 1 handler -> el Agente Analista analiza el requerimiento
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

  // Step 3 handler -> las respuestas de Negocio vuelven al agente
  const handleSendAnswers = async () => {
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
    setFormError('');
    setActiveStep(1);
  };

  // Step 3 -> Step 4: borrador simulado (el Agente Redactor-Revisor aún no existe)
  const handleGenerateStory = () => {
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
      setActiveStep(4);
    }, 800);
  };

  // Question answer handler
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

  // Step 4: la persona edita el borrador (el Agente Redactor-Revisor aún no existe)
  const handleUserStoryChange = (field, value) => setUserStory((prev) => ({ ...prev, [field]: value }));

  // Al llegar al paso 4 se propone el número según el código de HU y las historias ya guardadas.
  useEffect(() => {
    if (activeStep !== 4) return;
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
    const datos = {
      ...baseStoryData(),
      status: pendingQuestions.length > 0 ? 'pendiente_de_informacion' : 'revisada'
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

  return (
    <div>
      <TituloPaginaComponent
        title="Creación de Historia de Usuario"
        description="Flujo asistido por IA para el análisis y estructuración de historias de usuario."
      />

      {historiaOrigen && (
        <AlertaComponent type="info" title={`Revisión de ${historiaOrigen.number || 'la HU'}: pasará de ${etiquetaRevision(historiaOrigen)} a Rev. ${numeroRevision(historiaOrigen) + 1}`}>
          Es la misma historia, con el mismo código. Al aprobarla reemplaza a la versión vigente y la anterior queda en el historial de revisiones. Si sale sin aprobar, la versión vigente no cambia.
        </AlertaComponent>
      )}

      <PasosComponent
        steps={STEPPER_STEPS}
        activeStep={activeStep}
        onStepClick={(step) => setActiveStep(step)}
      />

      {borradorRecuperado && (
        <AlertaComponent type="info" title="Se recuperó su borrador">
          Continúa donde se quedó. Su avance se guarda solo en este navegador mientras escribe.
          <div style={{ marginTop: '0.5rem' }}>
            <BotonComponent
              variant="secondary"
              onClick={() => {
                borrarBorrador();
                setBorradorRecuperado(false);
                navigate('/historias/nueva', { replace: true, state: { reiniciar: Date.now() } });
              }}
            >
              Descartar borrador y empezar de nuevo
            </BotonComponent>
          </div>
        </AlertaComponent>
      )}

      {/* Carga: el Agente Analista (pasos 1-3) o el borrador simulado (paso 4) */}
      {isProcessing && (
        <div className="ai-loader" role="status" aria-live="polite">
          <div className="ai-loader__spinner"></div>
          <p className="ai-loader__text">
            {isGeneratingStory
              ? 'Generando el borrador de la Historia de Usuario...'
              : activeStep === 3
                ? 'El Agente Analista actualiza el análisis con las respuestas...'
                : 'El Agente Analista está analizando el requerimiento...'}
          </p>
          <p className="ai-loader__subtext">
            {isGeneratingStory
              ? 'Borrador simulado: el Agente Redactor-Revisor aún no está implementado.'
              : 'Consulta glosario, HU similares, estándares y checklist. Puede tardar hasta 90 segundos.'}
          </p>
          {agent.isProcessing && (
            <BotonComponent variant="secondary" icon={X} onClick={agent.cancelTurn}>
              Cancelar
            </BotonComponent>
          )}
        </div>
      )}

      {!isProcessing && activeStep <= 3 && agent.backendConnection === 'disconnected' && (
        <AlertaComponent type="danger" title="El agente no responde">
          No se pudo conectar con el backend del Agente Analista. Verifique que FastAPI y OpenCode estén iniciados.
          <div style={{ marginTop: '0.75rem' }}>
            <BotonComponent variant="secondary" icon={RotateCcw} onClick={() => agent.refreshHealth()}>
              Reintentar conexión
            </BotonComponent>
          </div>
        </AlertaComponent>
      )}

      {!isProcessing && activeStep <= 3 && agent.backendConnection !== 'disconnected' && agentError && (
        <AlertaComponent type="danger" title="No se pudo completar el análisis">
          {agentError}
          {failedMessage?.retryAt && (
            <p style={{ marginTop: '0.4rem' }}>Podrá reintentar a partir de {new Date(failedMessage.retryAt).toLocaleString('es-CR')}.</p>
          )}
          {failedMessage && (
            <div style={{ marginTop: '0.75rem' }}>
              <BotonComponent variant="secondary" icon={RotateCcw} onClick={handleRetryAgent}>
                Reintentar
              </BotonComponent>
            </div>
          )}
        </AlertaComponent>
      )}

      {!isProcessing && (
        <>
          {/* STEP 1: Requerimiento */}
          {activeStep === 1 && (
            <TarjetaComponent title="Paso 1 — Definición del Requerimiento" subtitle="Ingrese la minuta, el correo o el incidente recibido de Negocio. El Agente Analista lo clasificará y generará preguntas.">
              <AlertaComponent type="info" title="Antes del grooming">
                Esta etapa corresponde al Agente Analista. No ingrese datos personales reales (nombres de clientes, identificaciones, números de póliza): anonimícelos antes de pegar la información.
              </AlertaComponent>
              <form onSubmit={handleAnalyzeRequirement}>
                <CampoTextoComponent
                  label="Nombre del requerimiento"
                  id="req-name"
                  required
                  placeholder="Ej. Modificación de coberturas en pólizas vigentes"
                  value={requirementName}
                  onChange={(e) => setRequirementName(e.target.value)}
                />

                <SelectorComponent
                  label="Tipo de información"
                  id="info-type"
                  required
                  options={INFO_TYPE_OPTIONS}
                  value={infoType}
                  onChange={(e) => setInfoType(e.target.value)}
                />

                <div className="grid-2">
                  <SelectorComponent
                    label="Tipo de solicitud"
                    id="request-type"
                    required
                    options={TIPOS_SOLICITUD.map((tipo) => ({ value: tipo, label: tipo }))}
                    value={requestType}
                    onChange={(e) => setRequestType(e.target.value)}
                  />
                  <SelectorComponent
                    label="Sistema"
                    id="req-system"
                    required
                    options={armarOpcion(OPCION_SISTEMA, system, 'Seleccione un sistema')}
                    value={system}
                    onChange={(e) => setSystem(e.target.value)}
                  />
                </div>
                <div className="grid-2">
                  <CampoTextoComponent
                    label="Código de HU"
                    id="req-codigo-hu"
                    required
                    placeholder="Ej. POL-OF"
                    value={codigoHu}
                    onChange={(e) => setCodigoHu(e.target.value)}
                    hint="Prefijo del número de la HU; por ejemplo POL-OF genera HU-POL-OF-001."
                  />
                  <SelectorComponent
                    label="Área solicitante"
                    id="req-requester"
                    options={armarOpcion(OPCION_AREA_SOLICITANTE, requester, 'Seleccione un área')}
                    value={requester}
                    onChange={(e) => setRequester(e.target.value)}
                  />
                </div>

                <AreaTextoComponent
                  label="Descripción o información de negocio"
                  id="req-desc"
                  required
                  rows={6}
                  placeholder="Describa el requerimiento tal como lo expresó el cliente o equipo de negocio..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  hint={`Puede copiar y pegar notas desestructuradas, correos o minutas (máximo ${MAX_AGENT_MESSAGE_CODEPOINTS} caracteres en total).`}
                />

                {formError && <AlertaComponent type="danger" title="Revise el formulario">{formError}</AlertaComponent>}

                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', marginTop: '1.5rem', flexWrap: 'wrap' }}>
                  {agentResponse ? (
                    <BotonComponent type="button" variant="secondary" icon={RotateCcw} onClick={handleRestartAnalysis}>
                      Empezar de nuevo
                    </BotonComponent>
                  ) : <span />}
                  <BotonComponent type="submit" variant="primary" icon={Sparkles} size="lg">
                    {agentResponse ? 'Volver a analizar' : 'Analizar Requerimiento'}
                  </BotonComponent>
                </div>
              </form>
            </TarjetaComponent>
          )}

          {/* STEP 2: Análisis */}
          {activeStep === 2 && (
            <div>
              <TarjetaComponent
                title="Paso 2 — Análisis del Agente Analista"
                subtitle="Clasificación de la información en conocida, faltante, supuesta y ambigua."
              >
                <AlertaComponent type="info" title="Análisis completado">
                  El agente analizó <strong>"{requirementName}"</strong>. Es una propuesta: usted decide qué llevar a Negocio.
                </AlertaComponent>

                <TarjetaAnalisisComponent analysis={analysis} />

                {agentResponse?.respuesta_markdown && (
                  <details style={{ marginTop: '1.25rem' }}>
                    <summary style={{ cursor: 'pointer', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                      Ver el resumen completo del agente
                    </summary>
                    <div style={{ marginTop: '0.75rem' }}>
                      <MarkdownAsistenteComponent content={agentResponse.respuesta_markdown} />
                    </div>
                  </details>
                )}

                {sources.length > 0 && (
                  <p style={{ marginTop: '1.25rem', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                    <strong>Fuentes consultadas:</strong>{' '}
                    {sources.map((source) => `${source.label} (${source.count})`).join(' · ')}.
                    {' '}Las fuentes son simuladas o anonimizadas y deben confirmarse con Negocio.
                  </p>
                )}
                {agentResponse?.limitaciones?.length > 0 && (
                  <ul style={{ paddingLeft: '1.2rem', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                    {agentResponse.limitaciones.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
                  <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(1)}>
                    Atrás
                  </BotonComponent>
                  <BotonComponent variant="primary" icon={ArrowRight} onClick={() => setActiveStep(3)}>
                    Preguntas a Negocio ({pendingCount})
                  </BotonComponent>
                </div>
              </TarjetaComponent>
            </div>
          )}

          {/* STEP 3: Preguntas a Negocio */}
          {activeStep === 3 && (
            <div>
              <TarjetaComponent
                title="Paso 3 — Preguntas de Aclaración para Negocio"
                subtitle="Lleve estas preguntas a Negocio, registre sus respuestas y envíelas al agente. Se repite hasta que no queden vacíos."
              >
                {agentReady ? (
                  <AlertaComponent type="success" title="No quedan vacíos relevantes">
                    El agente considera aclarado el requerimiento. Puede generar el borrador de la Historia de Usuario.
                  </AlertaComponent>
                ) : (
                  <AlertaComponent type="warning" title={`Quedan ${pendingCount} preguntas pendientes`}>
                    Registre las respuestas de Negocio y use «Enviar respuestas al agente». El agente actualizará el análisis y puede añadir nuevas preguntas.
                  </AlertaComponent>
                )}

                {questions.length === 0 && (
                  <p style={{ fontStyle: 'italic', color: 'var(--color-text-secondary)' }}>El agente no generó preguntas para este requerimiento.</p>
                )}

                {questions.map((q, idx) => (
                  <TarjetaPreguntaComponent
                    key={q.id}
                    question={q}
                    index={idx}
                    onAnswerChange={handleQuestionAnswerChange}
                  />
                ))}

                {formError && <AlertaComponent type="danger" title="No se pudo enviar">{formError}</AlertaComponent>}

                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
                  <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(2)}>
                    Atrás
                  </BotonComponent>
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <BotonComponent
                      variant={unsentQuestions.length > 0 ? 'primary' : 'secondary'}
                      icon={Sparkles}
                      onClick={handleSendAnswers}
                      disabled={unsentQuestions.length === 0}
                    >
                      Enviar respuestas al agente{unsentQuestions.length > 0 ? ` (${unsentQuestions.length})` : ''}
                    </BotonComponent>
                    <BotonComponent
                      variant={agentReady ? 'primary' : 'secondary'}
                      icon={ArrowRight}
                      onClick={handleGenerateStory}
                      disabled={unsentQuestions.length > 0}
                      title={unsentQuestions.length > 0 ? 'Envíe primero las respuestas al agente' : undefined}
                    >
                      {agentReady ? 'Generar Historia de Usuario' : 'Continuar con preguntas pendientes'}
                    </BotonComponent>
                  </div>
                </div>
              </TarjetaComponent>
            </div>
          )}

          {/* STEP 4: Historia de Usuario */}
          {activeStep === 4 && (
            <div>
              <TarjetaComponent
                title="Paso 4 — Historia de Usuario Generada"
                subtitle="Visualización de la historia en formato estándar y criterios de aceptación."
              >
                <AlertaComponent type="warning" title="Borrador simulado: edítelo antes de continuar">
                  El Agente Redactor-Revisor todavía no está implementado. El texto de abajo es una plantilla genérica: redacte la historia y los criterios con las respuestas de Negocio. Solo se guardará lo que usted deje aquí.
                </AlertaComponent>
                <AreaTextoComponent label="Como" id="story-as-a" required rows={2} value={userStory.asA} onChange={(e) => handleUserStoryChange('asA', e.target.value)} />
                <AreaTextoComponent label="Quiero" id="story-i-want" required rows={2} value={userStory.iWant} onChange={(e) => handleUserStoryChange('iWant', e.target.value)} />
                <AreaTextoComponent label="Para" id="story-so-that" required rows={2} value={userStory.soThat} onChange={(e) => handleUserStoryChange('soThat', e.target.value)} />

                {/* Criterios de aceptación: un solo editor con Dado que, Cuando y Entonces */}
                <div style={{ marginBottom: '1.5rem' }}>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--color-text-primary)', marginBottom: '1rem' }}>
                    Criterios de Aceptación ({acceptanceCriteria.length})
                  </h4>
                  <EditorCriteriosComponent
                    valor={acceptanceCriteria}
                    alCambiar={setAcceptanceCriteria}
                    prefijoId="nuevo-criterio"
                    error={criteriosValidacion.ok ? '' : criteriosValidacion.error}
                  />
                </div>

                {beneficiosPropuestos && (
                  <AlertaComponent type="info" title="Beneficios propuestos por el agente">
                    Se deducen del requerimiento y de las respuestas de Negocio. Edítelos, agregue o quite los que haga falta antes de aprobar.
                  </AlertaComponent>
                )}
                <CamposPlantillaComponent valor={plantilla} alCambiar={actualizarPlantilla} prefijoId="nueva" />

                {/* Section 14: Preguntas Pendientes */}
                {pendingQuestions.length > 0 && (
                  <div style={{ backgroundColor: 'var(--color-warning-light)', border: '1px solid var(--color-warning-border)', borderRadius: '10px', padding: '1.25rem', marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-warning-text)', fontWeight: '700', marginBottom: '0.5rem' }}>
                      <HelpCircle size={18} />
                      <span>Preguntas pendientes por resolver ({pendingQuestions.length})</span>
                    </div>
                    <ul style={{ paddingLeft: '1.25rem', color: 'var(--color-warning-text)', fontSize: '0.9rem' }}>
                      {pendingQuestions.map((pq, idx) => (
                        <li key={idx} style={{ marginBottom: '0.35rem' }}>{pq}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
                  <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(3)}>
                    Atrás
                  </BotonComponent>
                  <BotonComponent variant="primary" icon={ArrowRight} onClick={() => setActiveStep(5)} disabled={!storyIsComplete}>
                    Aprobación del Product Owner
                  </BotonComponent>
                </div>
              </TarjetaComponent>
            </div>
          )}

          {/* STEP 5: Aprobación del Product Owner */}
          {activeStep === 5 && (
            <div>
              <TarjetaComponent
                title="Paso 5 — Aprobación del Product Owner"
                subtitle="Solo una persona aprueba. Al aprobar, la HU se guarda en el Repositorio de HU y queda lista para grooming."
              >
                <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
                  <div style={{ padding: '1rem', backgroundColor: 'var(--color-bg)', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
                    <h5 style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Requerimiento</h5>
                    <p style={{ fontWeight: '700', color: 'var(--color-text-primary)' }}>{requirementName}</p>
                    <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>Tipo: {infoType}</p>
                  </div>

                  <div style={{ padding: '1rem', backgroundColor: 'var(--color-bg)', borderRadius: '10px', border: '1px solid var(--color-border)' }}>
                    <h5 style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Resumen de Elementos</h5>
                    <p style={{ fontSize: '0.9rem', color: 'var(--color-text-primary)' }}>✓ Historia redactada</p>
                    <p style={{ fontSize: '0.9rem', color: 'var(--color-text-primary)' }}>✓ {acceptanceCriteria.length} Criterios de aceptación</p>
                    <p style={{ fontSize: '0.9rem', color: pendingQuestions.length > 0 ? 'var(--color-warning-text)' : 'var(--color-success-text)' }}>
                      {pendingQuestions.length > 0 ? `⚠ ${pendingQuestions.length} Preguntas pendientes` : '✓ Sin preguntas pendientes'}
                    </p>
                  </div>
                </div>

                <div className="story-structure" style={{ marginBottom: '1.5rem' }}>
                  <div className="story-structure__item">
                    <div className="story-structure__label">Como:</div>
                    <div className="story-structure__content">{userStory.asA}</div>
                  </div>
                  <div className="story-structure__item">
                    <div className="story-structure__label">Quiero:</div>
                    <div className="story-structure__content">{userStory.iWant}</div>
                  </div>
                  <div className="story-structure__item">
                    <div className="story-structure__label">Para:</div>
                    <div className="story-structure__content">{userStory.soThat}</div>
                  </div>
                </div>

                <AreaTextoComponent
                  label="Observaciones adicionales"
                  id="observations"
                  rows={3}
                  placeholder="Ingrese notas o consideraciones técnicas para la fase de implementación..."
                  value={observations}
                  onChange={(e) => setObservations(e.target.value)}
                />

                {pendingQuestions.length > 0 ? (
                  <AlertaComponent type="warning" title="No se puede aprobar con preguntas pendientes">
                    Vuelva al paso 3, envíe las respuestas de Negocio al agente y repita hasta que no queden vacíos.{historiaOrigen ? '' : ' Mientras tanto puede guardar la HU como borrador.'}
                  </AlertaComponent>
                ) : (
                  <label style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-start', margin: '1rem 0', fontSize: '0.95rem' }}>
                    <input
                      type="checkbox"
                      checked={confirmAnonymized}
                      onChange={(e) => setConfirmAnonymized(e.target.checked)}
                      style={{ marginTop: '0.2rem' }}
                    />
                    <span>
                      Apruebo esta HU como Product Owner y confirmo que no contiene datos personales reales (clientes, identificaciones, pólizas).
                    </span>
                  </label>
                )}

                {approvalError && <AlertaComponent type="danger" title="No se pudo aprobar">{approvalError}</AlertaComponent>}
                {descargaError && <AlertaComponent type="danger" title="No se pudo descargar">{descargaError}</AlertaComponent>}

                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
                  <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(4)}>
                    Atrás
                  </BotonComponent>
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <BotonComponent variant="secondary" icon={FileDown} onClick={handleDownloadWord}>
                      Descargar Word
                    </BotonComponent>
                    <BotonComponent variant="secondary" icon={FileDown} onClick={handleDownloadPdf}>
                      Descargar PDF
                    </BotonComponent>
                    {!historiaOrigen && (
                      <BotonComponent variant="secondary" icon={Save} onClick={handleSaveDraft}>
                        Guardar borrador
                      </BotonComponent>
                    )}
                    <BotonComponent
                      variant="primary"
                      icon={CheckCircle2}
                      size="lg"
                      onClick={handleApproveStory}
                      disabled={pendingQuestions.length > 0 || !confirmAnonymized || isApproving}
                    >
                      {isApproving ? 'Guardando...' : 'Aprobar y guardar en el Repositorio'}
                    </BotonComponent>
                  </div>
                </div>
              </TarjetaComponent>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// Al descartar el borrador se cambia la clave para que el asistente empiece desde cero.
export const CrearHistoriaUsuarioComponent = () => {
  const ubicacion = useLocation();
  return <CrearHistoriaUsuarioContenido key={ubicacion.state?.reiniciar ?? 'inicio'} />;
};
