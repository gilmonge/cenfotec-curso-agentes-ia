import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Send } from 'lucide-react';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import { CampoTextoComponent } from '../Comun/CampoTextoComponent';
import { SelectorComponent } from '../Comun/SelectorComponent';
import { AreaTextoComponent } from '../Comun/AreaTextoComponent';
import { repositorioApi, repositorioErrorMessage } from '../../services/repositorioApi';
import { getWorkflow, resumeWorkflow, startWorkflow, WorkflowApiError } from '../../services/workflowApi';
import { construirRevision } from '../../utils/revisiones';
import { rotuloCategoria } from '../../data/rotulosPregunta';
import { SeccionesConPestanasComponent } from '../HistoriaUsuario/detalle/SeccionesConPestanasComponent';
import { WorkflowInterruptionForm } from '../Comun/WorkflowInterruptionForm';
import { WorkflowResultsPanel } from '../Comun/WorkflowResultsPanel';
import '../Comun/workflow-panels.scss';

// El valor interno no cambia (lo usa el checklist); la persona ve el rótulo en lenguaje natural.
export const ROOT_CAUSES = [
  'Reglas de negocio', 'Datos requeridos', 'Validaciones', 'Excepciones', 'Comportamiento esperado',
].map((value) => ({ value, label: rotuloCategoria(value) }));

// Las aclaraciones y correcciones ya no se solicitan: se hacen con Editar. Esas etiquetas quedan
// solo para leer solicitudes registradas antes.
const CLASIFICACION_ANTERIOR = { aclaracion: 'Aclaración', correccion: 'Corrección de error' };
const LESSON_LABEL = { propuesta: 'Lección propuesta', aprobada: 'Lección aprobada', rechazada: 'Lección rechazada' };

const yaAplicada = (story, solicitud) => story.motivoRevision === solicitud
  || (story.revisiones ?? []).some((revision) => revision.motivo === solicitud);

export const SolicitudCambioComponent = ({ story }) => {
  const navigate = useNavigate();
  const [changes, setChanges] = useState([]);
  const [loadError, setLoadError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [workflowSnapshot, setWorkflowSnapshot] = useState(null);
  const [workflowError, setWorkflowError] = useState('');
  const [workflowErrorStatus, setWorkflowErrorStatus] = useState(null);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [manualFallback, setManualFallback] = useState(false);
  const [approvedHu, setApprovedHu] = useState(null);
  const workflowOperationRef = React.useRef(false);
  const workflowControllerRef = React.useRef(null);
  const submissionRef = React.useRef(false);
  const [sinVacio, setSinVacio] = useState(false);
  const [form, setForm] = useState({ solicitud: '', clasificacion: 'aclaracion', causa_raiz: 'Reglas de negocio', pregunta_sugerida: '', terminos: '' });

  const loadChanges = useCallback(async () => {
    try {
      setChanges(await repositorioApi.listChanges(story.id));
      setLoadError('');
    } catch (cause) {
      setLoadError(repositorioErrorMessage(cause));
    }
  }, [story.id]);

  useEffect(() => { void loadChanges(); }, [loadChanges]);
  useEffect(() => () => workflowControllerRef.current?.abort(), []);

  const callWorkflow = async (operation) => {
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
      setWorkflowError(cause instanceof WorkflowApiError ? cause.message : 'No se pudo comunicar con el workflow.');
      setWorkflowErrorStatus(cause?.status || null);
      return null;
    } finally {
      workflowOperationRef.current = false;
      workflowControllerRef.current = null;
      setWorkflowBusy(false);
    }
  };

  const refreshWorkflow = async () => {
    if (!workflowSnapshot?.workflow_id) return;
    const result = await callWorkflow((signal) => getWorkflow(workflowSnapshot.workflow_id, { signal }));
    if (result) setWorkflowSnapshot(result);
  };

  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitError('');
    if (!form.solicitud.trim()) {
      setSubmitError('Describa lo que pide Negocio.');
      return;
    }
    if (submissionRef.current) return;
    submissionRef.current = true;
    setIsSending(true);
    setSubmitError('');
    setWorkflowError('');
    setWorkflowErrorStatus(null);
    try {
      if (!manualFallback) {
        const approvedStories = await repositorioApi.listStories();
        const realHu = approvedStories.find((item) => String(item.id) === String(story.id) && item.aprobada_en);
        if (!realHu) {
          setWorkflowError('La HU no aparece como aprobada en el Repositorio real. Compruebe que la HU aprobada esté sincronizada y vuelva a intentarlo.');
          return;
        }
        setApprovedHu(realHu);
        const snapshot = await callWorkflow((signal) => startWorkflow({
          mode: 'post_grooming',
          approved_story_id: realHu.id,
          change_request: form.solicitud.trim(),
        }, { signal }));
        if (snapshot) {
          setWorkflowSnapshot(snapshot);
          return;
        }
        return;
      }

      const terminos = form.terminos.split(',').map((term) => term.trim()).filter(Boolean).slice(0, 10);
      const needsLesson = form.clasificacion === 'cambio_alcance' && !sinVacio;
      if (needsLesson && !form.pregunta_sugerida.trim()) {
        setSubmitError('Escriba la pregunta que debió hacerse, o marque que no fue un vacío del análisis.');
        return;
      }
      const leccion = needsLesson
        ? { causa_raiz: form.causa_raiz, pregunta_sugerida: form.pregunta_sugerida.trim(), terminos }
        : {};
      const solicitud = form.solicitud.trim();
      await repositorioApi.registerChange({ hu_id: story.id, solicitud, clasificacion: form.clasificacion, ...leccion });
      if (form.clasificacion === 'cambio_alcance') analizarCambio(solicitud);
      else {
        setWorkflowError('La aclaración quedó registrada en el modo manual; no se abrió un análisis de alcance.');
        await loadChanges();
      }
    } catch (cause) {
      if (manualFallback) setSubmitError(repositorioErrorMessage(cause));
      else setWorkflowError(repositorioErrorMessage(cause));
    } finally {
      submissionRef.current = false;
      setIsSending(false);
    }
  };

  const analizarCambio = (solicitud) => {
    navigate('/historias/nueva', { state: { prefill: construirRevision(story, solicitud), revisionDeId: story.id } });
  };

  const handleWorkflowResume = async (body) => {
    if (!workflowSnapshot?.workflow_id || !body?.interrupt_id) return;
    const updated = await callWorkflow((signal) => resumeWorkflow(workflowSnapshot.workflow_id, body, { signal }));
    if (!updated) return;
    const classification = workflowSnapshot.results?.change_recommendation?.recommendation;
    setWorkflowSnapshot(updated);
    if (body.kind === 'change_decision' && body.response?.decision === 'aplicar'
      && classification === 'cambio_alcance'
      && ['business_answers', 'po_approval'].includes(updated.interrupt?.kind)) {
      navigate('/historias/nueva', {
        state: {
          workflowSnapshot: updated,
          prefill: construirRevision(story, form.solicitud.trim()),
          revisionDeId: story.id,
        },
      });
    } else if (body.kind === 'change_decision') {
      await loadChanges();
    }
  };

  return (
    <div id="solicitud-cambio">
      <SeccionesConPestanasComponent
        etiqueta="Secciones de la solicitud"
        inicial="nueva"
        secciones={[
          {
            id: 'nueva',
            titulo: 'Nueva solicitud',
            contenido: (
              <TarjetaComponent
                title="Después del grooming — Solicitudes de cambio"
                subtitle="El Gestor de Cambios clasifica la solicitud con base en la HU aprobada real. Una decisión humana acepta, rechaza o devuelve la recomendación."
              >
                {workflowSnapshot ? (
                  <div>
                    <AlertaComponent type="info" title="Workflow de cambio activo en memoria">
                      El workflow usa un checkpoint temporal del backend. Si se reinicia el proceso, el checkpoint se pierde; consulte el estado o inicie otro flujo. No se guarda el identificador en localStorage.
                      {approvedHu && <p>HU aprobada del Repositorio: <strong>{approvedHu.titulo}</strong> ({approvedHu.id})</p>}
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.6rem', flexWrap: 'wrap' }}>
                        <BotonComponent variant="secondary" onClick={refreshWorkflow} disabled={workflowBusy}>Consultar estado</BotonComponent>
                        <BotonComponent variant="secondary" onClick={() => setWorkflowSnapshot(null)} disabled={workflowBusy}>Iniciar solicitud nueva</BotonComponent>
                      </div>
                    </AlertaComponent>

                    {workflowError && <AlertaComponent type={workflowErrorStatus === 404 ? 'warning' : 'danger'} title={workflowErrorStatus ? `Workflow: HTTP ${workflowErrorStatus}` : 'Workflow no disponible'}>{workflowError}{workflowErrorStatus === 404 && <p>El checkpoint no se recuperó; inicie un flujo nuevo.</p>}</AlertaComponent>}
                    {workflowSnapshot.results?.change_recommendation && (
                      <div className="workflow-results__card">
                        <h3>Recomendación del Gestor de Cambios: {workflowSnapshot.results.change_recommendation.recommendation}</h3>
                        <p><strong>Justificación:</strong> {workflowSnapshot.results.change_recommendation.rationale}</p>
                        <h4>Comparación con la HU aprobada</h4>
                        <ul>{workflowSnapshot.results.change_recommendation.comparison.map((item, index) => (
                          <li key={`${item.approved_excerpt}-${index}`}><strong>HU:</strong> {item.approved_excerpt} · <strong>Solicitud:</strong> {item.request_excerpt} · {item.explanation}</li>
                        ))}</ul>
                        <h4>Impacto</h4>
                        <ul>{workflowSnapshot.results.change_recommendation.impact.map((item) => <li key={item}>{item}</li>)}</ul>
                        {!!workflowSnapshot.results.change_recommendation.uncertainties?.length && <><h4>Incertidumbres</h4><ul>{workflowSnapshot.results.change_recommendation.uncertainties.map((item) => <li key={item}>{item}</li>)}</ul></>}
                        {!!workflowSnapshot.results.change_recommendation.lessons_proposed?.length && <><h4>Lecciones propuestas (no aprobadas)</h4><ul>{workflowSnapshot.results.change_recommendation.lessons_proposed.map((item, index) => <li key={`${item.suggested_question}-${index}`}>{item.suggested_question}</li>)}</ul></>}
                      </div>
                    )}
                    <WorkflowResultsPanel results={workflowSnapshot.results} showStory={false} />
                    {workflowSnapshot.interrupt?.kind === 'change_decision' ? (
                      <WorkflowInterruptionForm interrupt={workflowSnapshot.interrupt} onResume={handleWorkflowResume} busy={workflowBusy} error={workflowError} />
                    ) : workflowSnapshot.results?.change_persistence_result ? (
                      <AlertaComponent type={workflowSnapshot.results.change_persistence_result.status === 'recorded' ? 'success' : 'warning'} title="Decisión registrada">
                        {workflowSnapshot.results.completion_reason || workflowSnapshot.results.change_persistence_result.status}
                      </AlertaComponent>
                    ) : <AlertaComponent type="info" title="Workflow en ejecución">{workflowSnapshot.results?.completion_reason || `Etapa: ${workflowSnapshot.stage}.`}</AlertaComponent>}
                  </div>
                ) : (
                  <form onSubmit={handleSubmit}>
                    <AlertaComponent type="info" title="Los workflows no se recuperan automáticamente">
                      El identificador no se guarda en localStorage y el checkpoint vive en memoria del backend. Si perdió el estado, inicie una solicitud nueva; la interfaz no recupera checkpoints después de un reinicio.
                    </AlertaComponent>
                    {workflowError && <AlertaComponent type={workflowErrorStatus === 404 ? 'warning' : 'danger'} title={workflowErrorStatus ? `Workflow: HTTP ${workflowErrorStatus}` : 'Workflow no disponible'}>
                      {workflowError}
                      {!manualFallback && <div style={{ marginTop: '0.6rem' }}><BotonComponent type="button" variant="secondary" onClick={() => setManualFallback(true)}>Continuar en modo manual</BotonComponent></div>}
                    </AlertaComponent>}
                    {manualFallback && <AlertaComponent type="warning" title="Modo manual alternativo">
                      La recomendación automática no se pudo obtener. Elija la clasificación según la solicitud. Las aclaraciones no requieren cambio de alcance; el análisis de revisión se abre solo para cambio_alcance.
                    </AlertaComponent>}
                    <AreaTextoComponent label="Solicitud de cambio" id="change-request" required rows={3} value={form.solicitud} onChange={update('solicitud')} placeholder="Qué pide Negocio que cambie respecto a la HU aprobada..." hint="Anonimice los datos personales antes de escribir." />

                    {manualFallback && <>
                      <SelectorComponent
                        label="Clasificación manual"
                        id="change-classification"
                        options={[{ value: 'aclaracion', label: 'Aclaración' }, { value: 'cambio_alcance', label: 'Cambio de alcance' }]}
                        value={form.clasificacion}
                        onChange={update('clasificacion')}
                      />
                      {form.clasificacion === 'cambio_alcance' && <>
                        <label style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-start', margin: '0.5rem 0 1rem', fontSize: '0.95rem' }}>
                          <input id="change-sin-vacio" type="checkbox" checked={sinVacio} onChange={(event) => setSinVacio(event.target.checked)} style={{ marginTop: '0.2rem' }} />
                          <span>No fue un vacío del análisis: Negocio cambió de decisión</span>
                        </label>
                        {!sinVacio && <div className="grid-2">
                          <SelectorComponent label="¿Qué no se preguntó a tiempo?" id="change-cause" required options={ROOT_CAUSES} value={form.causa_raiz} onChange={update('causa_raiz')} />
                          <CampoTextoComponent label="Términos clave (opcional, separados por coma)" id="change-terms" value={form.terminos} onChange={update('terminos')} placeholder="Ej. endoso, vigencia" />
                        </div>}
                        {!sinVacio && <AreaTextoComponent label="Pregunta que debió hacerse antes del grooming" id="change-lesson" required rows={2} value={form.pregunta_sugerida} onChange={update('pregunta_sugerida')} hint="Quedará propuesta; no se aprueba automáticamente." />}
                      </>}
                    </>}

                    {submitError && <AlertaComponent type="danger" title="No se pudo registrar">{submitError}</AlertaComponent>}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
                      <BotonComponent type="submit" variant="primary" icon={Send} disabled={isSending || workflowBusy}>
                        {isSending || workflowBusy ? 'Iniciando...' : manualFallback ? 'Registrar decisión manual' : 'Analizar con Gestor de Cambios'}
                      </BotonComponent>
                    </div>
                  </form>
                )}
              </TarjetaComponent>
            ),
          },
          {
            id: 'historial',
            titulo: 'Historial de solicitudes',
            contador: changes.length,
            contenido: (
              <TarjetaComponent title="Historial de solicitudes">
      {loadError && <AlertaComponent type="warning" title="No se pudo cargar el historial">{loadError}</AlertaComponent>}
      {!loadError && changes.length === 0 && <p style={{ fontStyle: 'italic', color: 'var(--color-text-secondary)' }}>Aún no hay solicitudes de cambio para esta HU.</p>}
      <ul style={{ padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {changes.map((change) => (
          <li key={change.id} style={{ listStyle: 'none', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '0.7rem 0.9rem' }}>
            <p style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{change.solicitud}</p>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
              {CLASIFICACION_ANTERIOR[change.clasificacion] ? `${CLASIFICACION_ANTERIOR[change.clasificacion]} · ` : ''}
              {change.causa_raiz ? `Falta de pregunta sobre: ${rotuloCategoria(change.causa_raiz)} · ` : ''}
              {LESSON_LABEL[change.leccion_estado] ?? 'Sin lección'}
            </p>
            {change.clasificacion === 'cambio_alcance' && (
              yaAplicada(story, change.solicitud)
                ? <p style={{ fontSize: '0.85rem', marginTop: '0.4rem' }}>Aplicada en la HU (ver el historial).</p>
                : (
                  <div style={{ marginTop: '0.6rem' }}>
                    <BotonComponent variant="primary" icon={ArrowRight} onClick={() => analizarCambio(change.solicitud)}>
                      Analizar el cambio con el agente
                    </BotonComponent>
                  </div>
                )
            )}
          </li>
        ))}
      </ul>
              </TarjetaComponent>
            ),
          },
        ]}
      />
    </div>
  );
};
