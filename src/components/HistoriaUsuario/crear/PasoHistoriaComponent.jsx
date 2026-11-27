import React from 'react';
import { useAsistenteHistoria } from './AsistenteHistoriaContext';
import { AlertaComponent } from '../../Comun/AlertaComponent';
import { AreaTextoComponent } from '../../Comun/AreaTextoComponent';
import { ArrowLeft, ArrowRight, HelpCircle } from 'lucide-react';
import { BotonComponent } from '../../Comun/BotonComponent';
import { CamposPlantillaComponent } from '../CamposPlantillaComponent';
import { EditorCriteriosComponent } from '../EditorCriteriosComponent';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { WorkflowResultsPanel } from '../../Comun/WorkflowResultsPanel';
import { PASO } from './constantesAsistente';

// Vista de un paso del asistente. El estado y las acciones vienen del controlador (useCrearHistoria).
export const PasoHistoriaComponent = () => {
  const {
    acceptanceCriteria,
    actualizarPlantilla,
    beneficiosPropuestos,
    criteriosValidacion,
    handleUserStoryChange,
    pendingQuestions,
    plantilla,
    refreshWorkflow,
    setAcceptanceCriteria,
    setActiveStep,
    setWorkflowError,
    setWorkflowResponse,
    storyIsComplete,
    userStory,
    workflowBusy,
    workflowResponse,
    workflowStoryEdited,
  } = useAsistenteHistoria();

  return (
    <div>
      <TarjetaComponent
        title="Paso 4 — Historia de Usuario Generada"
        subtitle="Visualización de la historia en formato estándar y criterios de aceptación."
      >
        {workflowResponse
          ? <>
            <WorkflowResultsPanel results={workflowResponse.results} showStory />
            {workflowStoryEdited && <AlertaComponent type="warning" title="El contrato PO actual no incluye ediciones de HU">
              El checkpoint conserva la versión original del Redactor. Para que esta edición sea la que se persista, abandone el checkpoint y continúe por el guardado manual; la decisión del workflow no se enviará.
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                <BotonComponent variant="secondary" onClick={() => { setWorkflowResponse(null); setWorkflowError('Se abandonó el checkpoint. La HU continuará por el flujo manual y no se enviará una aprobación LangGraph.'); }}>
                  Abandonar workflow y continuar en modo manual
                </BotonComponent>
                <BotonComponent variant="secondary" onClick={refreshWorkflow} disabled={workflowBusy}>
                  Restaurar borrador del checkpoint
                </BotonComponent>
              </div>
            </AlertaComponent>}
          </>
          : (
            <AlertaComponent type="warning" title="Borrador simulado: edítelo antes de continuar">
              El servicio de workflow no está disponible. Este borrador sigue el flujo manual existente, con generación simulada; edítelo antes de continuar.
            </AlertaComponent>
          )}
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
          <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(PASO.PREGUNTAS)}>
            Atrás
          </BotonComponent>
          <BotonComponent variant="primary" icon={ArrowRight} onClick={() => setActiveStep(PASO.APROBACION)} disabled={!storyIsComplete}>
            Aprobación del Product Owner
          </BotonComponent>
        </div>
      </TarjetaComponent>
    </div>
  );
};
