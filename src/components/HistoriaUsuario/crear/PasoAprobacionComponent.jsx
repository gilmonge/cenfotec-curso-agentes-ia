import React from 'react';
import { useAsistenteHistoria } from './AsistenteHistoriaContext';
import { AlertaComponent } from '../../Comun/AlertaComponent';
import { AreaTextoComponent } from '../../Comun/AreaTextoComponent';
import { ArrowLeft, CheckCircle2, FileDown, Save } from 'lucide-react';
import { BotonComponent } from '../../Comun/BotonComponent';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { WorkflowInterruptionForm } from '../../Comun/WorkflowInterruptionForm';
import { WorkflowResultsPanel } from '../../Comun/WorkflowResultsPanel';
import { PASO } from './constantesAsistente';

// Vista de un paso del asistente. El estado y las acciones vienen del controlador (useCrearHistoria).
export const PasoAprobacionComponent = () => {
  const {
    acceptanceCriteria,
    approvalError,
    confirmAnonymized,
    descargaError,
    handleApproveStory,
    handleDownloadPdf,
    handleDownloadWord,
    handleSaveDraft,
    historiaOrigen,
    infoType,
    isApproving,
    observations,
    pendingQuestions,
    requirementName,
    resumeWorkflowInterrupt,
    setActiveStep,
    setConfirmAnonymized,
    setObservations,
    userStory,
    workflowBusy,
    workflowError,
    workflowResponse,
    workflowStoryEdited,
  } = useAsistenteHistoria();

  return (
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
          label={workflowResponse ? 'Nota para la bitácora (opcional)' : 'Observaciones adicionales'}
          id="observations"
          rows={3}
          placeholder={workflowResponse
            ? 'Se guarda en la HU como una nota al aprobar. Las decisiones, dependencias y pendientes técnicos se registran solos.'
            : 'Ingrese notas o consideraciones técnicas para la fase de implementación...'}
          maxLength={workflowResponse ? 1000 : undefined}
          value={observations}
          onChange={(e) => setObservations(e.target.value)}
        />

        {pendingQuestions.length > 0 ? (
          <AlertaComponent type="warning" title="No se puede aprobar con preguntas pendientes">
            Vuelva al paso 3, envíe las respuestas de Negocio al agente y repita hasta que no queden vacíos.{historiaOrigen ? '' : ' Mientras tanto puede guardar la HU como borrador.'}
          </AlertaComponent>
        ) : workflowResponse?.interrupt?.kind === 'po_approval' && !workflowStoryEdited ? (
          <>
            <label style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-start', margin: '1rem 0', fontSize: '0.95rem' }}>
              <input type="checkbox" checked={confirmAnonymized} onChange={(e) => setConfirmAnonymized(e.target.checked)} style={{ marginTop: '0.2rem' }} />
              <span>Confirmo que revisé la anonimización y que mi selección de Product Owner es deliberada.</span>
            </label>
            <WorkflowResultsPanel results={workflowResponse.results} />
            <WorkflowInterruptionForm
              interrupt={workflowResponse.interrupt}
              onResume={resumeWorkflowInterrupt}
              busy={workflowBusy}
              error={workflowError}
              canSubmit={confirmAnonymized}
            />
          </>
        ) : workflowResponse?.interrupt?.kind === 'po_approval' && workflowStoryEdited ? (
          <AlertaComponent type="warning" title="La edición no se enviará a la API de aprobación">
            Restaure la versión del checkpoint para aprobarla en LangGraph, o abandone el workflow y use el guardado manual disponible en el paso 5. La edición manual nunca se enviará como aprobación del checkpoint.
          </AlertaComponent>
        ) : workflowResponse?.results?.persistence_result?.status === 'saved' ? (
          <AlertaComponent type="success" title="HU aprobada y guardada por el backend">
            {workflowResponse.results.completion_reason}
          </AlertaComponent>
        ) : workflowResponse ? (
          <AlertaComponent type={workflowResponse.status === 'cancelled' ? 'warning' : 'info'} title="Este workflow no espera una decisión PO ahora">
            {workflowResponse.results?.completion_reason || `Etapa actual: ${workflowResponse.stage}.`}
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
          <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(PASO.HISTORIA)}>
            Atrás
          </BotonComponent>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <BotonComponent variant="secondary" icon={FileDown} onClick={handleDownloadWord}>
              Descargar Word
            </BotonComponent>
            <BotonComponent variant="secondary" icon={FileDown} onClick={handleDownloadPdf}>
              Descargar PDF
            </BotonComponent>
            {!historiaOrigen && !workflowResponse && (
              <BotonComponent variant="secondary" icon={Save} onClick={handleSaveDraft}>
                Guardar borrador
              </BotonComponent>
            )}
            {!workflowResponse && (
              <BotonComponent variant="primary" icon={CheckCircle2} size="lg" onClick={handleApproveStory} disabled={pendingQuestions.length > 0 || !confirmAnonymized || isApproving}>
                {isApproving ? 'Guardando...' : 'Aprobar y guardar en el Repositorio'}
              </BotonComponent>
            )}
          </div>
        </div>
      </TarjetaComponent>
    </div>
  );
};
