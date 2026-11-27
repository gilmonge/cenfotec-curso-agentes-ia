import React from 'react';
import { useLocation } from 'react-router-dom';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { PasosComponent } from '../Comun/PasosComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { borrarBorrador } from '../../utils/borradorAsistente';
import { etiquetaRevision, numeroRevision } from '../../utils/revisiones';
import { RotateCcw, X } from 'lucide-react';
import { useCrearHistoria } from './crear/useCrearHistoria';
import { AsistenteHistoriaContext } from './crear/AsistenteHistoriaContext';
import { LISTA_PASO, pasoPorId } from './crear/pasosAsistente';
import { PASO } from './crear/constantesAsistente';
import '../Comun/workflow-panels.scss';

// Asistente para crear una historia (capas):
// - Controlador: crear/useCrearHistoria.js (estado, efectos y acciones del flujo).
// - Vistas: un componente por paso en crear/Paso*Component.jsx, registrados en crear/pasosAsistente.js.
// - Este componente solo arma la página: avisos generales, indicador de pasos y el paso activo.
const CrearHistoriaUsuarioContenido = () => {
  const asistente = useCrearHistoria();
  const {
    activeStep,
    agent,
    agentError,
    borradorRecuperado,
    failedMessage,
    guardado,
    handleRetryAgent,
    historiaOrigen,
    isGeneratingStory,
    isProcessing,
    navigate,
    pendingCount,
    refreshWorkflow,
    reintentarFlujo,
    retomando,
    setActiveStep,
    setBorradorRecuperado,
    setFormError,
    startFreshWorkflow,
    workflowBusy,
    workflowError,
    workflowErrorStatus,
    workflowResponse,
  } = asistente;
  const PasoActivoComponent = pasoPorId(activeStep)?.Componente;

  return (
    <AsistenteHistoriaContext.Provider value={asistente}>
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
          steps={LISTA_PASO.map(({ id, etiqueta }) => ({ id, label: etiqueta }))}
          activeStep={activeStep}
          onStepClick={(step) => {
            if ((workflowResponse?.interrupt?.kind === 'business_answers' || (!workflowResponse && pendingCount > 0)) && step > PASO.PREGUNTAS) {
              setFormError('No avance con preguntas de Negocio pendientes; respóndalas y reanude el flujo.');
              return;
            }
            if (workflowResponse && step >= PASO.HISTORIA && !workflowResponse.results?.story) {
              setFormError('El flujo todavía no ha generado la historia.');
              return;
            }
            setFormError('');
            setActiveStep(step);
          }}
        />

        {workflowResponse && (
          <AlertaComponent type="info" title={guardado?.persistente ? 'El avance se guarda automáticamente' : 'Flujo activo'}>
            {guardado?.persistente
              ? 'Cada vez que el flujo espera una respuesta queda guardado. Puede salir y retomarlo otro día desde Historias de Usuario → En proceso.'
              : 'Este flujo vive mientras el servicio esté activo; si se reinicia, hay que iniciar uno nuevo.'}
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.6rem', flexWrap: 'wrap' }}>
              <BotonComponent variant="secondary" onClick={refreshWorkflow} disabled={workflowBusy}>Consultar estado</BotonComponent>
              {guardado?.reintentable && (
                <BotonComponent variant="primary" icon={RotateCcw} onClick={reintentarFlujo} disabled={workflowBusy}>Reintentar el paso que falló</BotonComponent>
              )}
              <BotonComponent variant="secondary" onClick={startFreshWorkflow} disabled={workflowBusy}>Iniciar un flujo nuevo</BotonComponent>
            </div>
          </AlertaComponent>
        )}
        {workflowError && (
          <AlertaComponent type={workflowErrorStatus === 404 ? 'warning' : 'danger'} title={workflowErrorStatus ? `Workflow: HTTP ${workflowErrorStatus}` : 'Workflow no disponible'}>
            {workflowError}
            {!workflowResponse && <p>Puede seguir con el flujo manual del Analista existente. Una HU manual no se combinará con una aprobación del workflow.</p>}
            {workflowResponse && workflowErrorStatus === 404 && <p>El flujo no se encontró. Inicie uno nuevo para continuar.</p>}
            {workflowResponse && guardado?.reintentable && <p>El avance anterior quedó guardado. Use «Reintentar el paso que falló».</p>}
            {!workflowResponse && (
              <div style={{ marginTop: '0.6rem' }}>
                <BotonComponent variant="secondary" onClick={startFreshWorkflow} disabled={workflowBusy}>Reintentar con un workflow nuevo</BotonComponent>
              </div>
            )}
          </AlertaComponent>
        )}
        {retomando && (
          <AlertaComponent type="info" title="Retomando la HU en proceso">Cargando el avance guardado…</AlertaComponent>
        )}

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

        {/* Carga: el Analista y el Asesor (pasos 1-3), el Redactor-Revisor o el borrador del modo manual */}
        {isProcessing && (
          <div className="ai-loader" role="status" aria-live="polite">
            <div className="ai-loader__spinner"></div>
            <p className="ai-loader__text">
              {isGeneratingStory
                ? 'Generando el borrador de la Historia de Usuario...'
                : activeStep === PASO.PREGUNTAS
                  ? 'El Analista revisa las respuestas; si ya no quedan vacíos, el Redactor-Revisor escribe y revisa la historia...'
                  : activeStep >= PASO.HISTORIA
                    ? 'El flujo continúa con la decisión indicada...'
                    : workflowResponse || activeStep === PASO.REQUERIMIENTO
                      ? 'El Agente Analista analiza el requerimiento y el Asesor Técnico revisa qué otras funciones afecta el cambio...'
                      : 'El Agente Analista está analizando el requerimiento...'}
            </p>
            <p className="ai-loader__subtext">
              {isGeneratingStory
                ? 'Borrador del modo manual (sin el flujo de agentes).'
                : workflowResponse
                  ? 'Puede tardar varios minutos. Si sale de la página, el avance anterior queda guardado.'
                  : 'Consulta glosario, HU similares, estándares y checklist. Puede tardar unos minutos.'}
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
            {PasoActivoComponent && <PasoActivoComponent />}
          </>
        )}
      </div>
    </AsistenteHistoriaContext.Provider>
  );
};

// Al descartar el borrador se cambia la clave para que el asistente empiece desde cero.
export const CrearHistoriaUsuarioComponent = () => {
  const ubicacion = useLocation();
  return <CrearHistoriaUsuarioContenido key={ubicacion.state?.reiniciar ?? 'inicio'} />;
};
