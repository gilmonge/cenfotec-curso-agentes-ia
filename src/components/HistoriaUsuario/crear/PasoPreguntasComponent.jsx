import React from 'react';
import { useAsistenteHistoria } from './AsistenteHistoriaContext';
import { AlertaComponent } from '../../Comun/AlertaComponent';
import { ArrowLeft, ArrowRight, Sparkles } from 'lucide-react';
import { BotonComponent } from '../../Comun/BotonComponent';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { TarjetaPreguntaComponent } from '../TarjetaPreguntaComponent';
import { WorkflowInterruptionForm } from '../../Comun/WorkflowInterruptionForm';
import { ImpactoNegocioComponent } from '../../Comun/WorkflowResultsPanel';
import { PASO, ROTULO_ESTADO_WORKFLOW } from './constantesAsistente';

// Vista de un paso del asistente. El estado y las acciones vienen del controlador (useCrearHistoria).
export const PasoPreguntasComponent = () => {
  const {
    agentReady,
    agentResponse,
    formError,
    guardado,
    guardarRespuestasSinEnviar,
    handleGenerateStory,
    handleQuestionAnswerChange,
    handleSaveDraft,
    handleSendAnswers,
    pendingCount,
    questions,
    resumeWorkflowInterrupt,
    setActiveStep,
    unsentQuestions,
    workflowBusy,
    workflowError,
    workflowResponse,
    workflowSinSiguientePaso,
  } = useAsistenteHistoria();

  return (
    <div>
      <TarjetaComponent
        title="Paso 3 — Preguntas para Negocio"
        subtitle="El Analista y el Asesor Técnico prepararon juntos las preguntas: lleve todas a Negocio en una sola ronda, registre las respuestas y envíelas."
      >
        {(workflowResponse?.interrupt?.payload?.impacto_negocio?.length ?? 0) > 0 && (
          <div className="workflow-results__card">
            <h3>Lo que encontró el Asesor Técnico</h3>
            <ImpactoNegocioComponent listaImpacto={workflowResponse.interrupt.payload.impacto_negocio} />
          </div>
        )}
        {workflowSinSiguientePaso ? (
          <AlertaComponent type={workflowResponse.status === 'failed' ? 'danger' : 'info'} title={`Flujo ${ROTULO_ESTADO_WORKFLOW[workflowResponse.status] ?? workflowResponse.status}`}>
            {workflowResponse.results?.completion_reason || workflowError || 'El flujo no espera respuestas de Negocio ni tiene un borrador. Puede consultar el estado o iniciar de nuevo desde el paso 1.'}
          </AlertaComponent>
        ) : agentReady ? (
          <AlertaComponent type="success" title="No quedan vacíos relevantes">
            {workflowResponse
              ? 'El Analista considera aclarado el requerimiento y no quedan decisiones del Asesor. El Redactor-Revisor escribe la historia.'
              : 'El agente considera aclarado el requerimiento. Puede generar el borrador de la Historia de Usuario.'}
            {(agentResponse?.supuesto_validar_po?.length ?? 0) > 0 && (
              <> Quedan {agentResponse.supuesto_validar_po.length} supuestos que validará el Product Owner al aprobar.</>
            )}
          </AlertaComponent>
        ) : (
          <AlertaComponent type="warning" title={pendingCount === 1 ? 'Queda 1 pregunta pendiente' : `Quedan ${pendingCount} preguntas pendientes`}>
            Registre las respuestas y envíelas: las esperan el Analista y el Asesor Técnico. La HU no estará disponible para aprobación mientras quede alguna pregunta pendiente.
          </AlertaComponent>
        )}

        {!workflowResponse && questions.length === 0 && (
          <p style={{ fontStyle: 'italic', color: 'var(--color-text-secondary)' }}>El agente no generó preguntas para este requerimiento.</p>
        )}

        {workflowResponse?.interrupt?.kind === 'business_answers' ? (
          <WorkflowInterruptionForm
            key={workflowResponse.interrupt.interrupt_id}
            interrupt={workflowResponse.interrupt}
            onResume={resumeWorkflowInterrupt}
            busy={workflowBusy}
            error={workflowError}
            borrador={guardado?.borrador_respuestas}
            onSaveDraft={guardado?.persistente ? guardarRespuestasSinEnviar : undefined}
          />
        ) : !workflowResponse && questions.map((q, idx) => (
          <TarjetaPreguntaComponent key={q.id} question={q} index={idx} onAnswerChange={handleQuestionAnswerChange} />
        ))}

        {formError && <AlertaComponent type="danger" title="No se pudo enviar">{formError}</AlertaComponent>}

        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
          <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(PASO.ANALISIS)}>
            Atrás
          </BotonComponent>
          {workflowResponse?.results?.story && (
            <BotonComponent variant="primary" icon={ArrowRight} onClick={() => setActiveStep(PASO.HISTORIA)}>
              Historia de usuario
            </BotonComponent>
          )}
          {!workflowResponse && (
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <BotonComponent variant={unsentQuestions.length > 0 ? 'primary' : 'secondary'} icon={Sparkles} onClick={handleSendAnswers} disabled={unsentQuestions.length === 0}>
                Enviar respuestas al agente{unsentQuestions.length > 0 ? ` (${unsentQuestions.length})` : ''}
              </BotonComponent>
              <BotonComponent variant={agentReady ? 'primary' : 'secondary'} icon={ArrowRight} onClick={handleGenerateStory} disabled={unsentQuestions.length > 0 || pendingCount > 0} title={pendingCount > 0 ? 'Responda y envíe todas las preguntas pendientes' : undefined}>
                Generar Historia de Usuario
              </BotonComponent>
              {pendingCount > 0 && <BotonComponent variant="secondary" onClick={handleSaveDraft}>Guardar borrador pendiente</BotonComponent>}
            </div>
          )}
        </div>
      </TarjetaComponent>
    </div>
  );
};
