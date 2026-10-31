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
import { construirRevision } from '../../utils/revisiones';
import { rotuloCategoria } from '../../data/rotulosPregunta';
import { SeccionesConPestanasComponent } from '../HistoriaUsuario/detalle/SeccionesConPestanasComponent';

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
  const [sinVacio, setSinVacio] = useState(false);
  const [form, setForm] = useState({ solicitud: '', causa_raiz: 'Reglas de negocio', pregunta_sugerida: '', terminos: '' });

  const loadChanges = useCallback(async () => {
    try {
      setChanges(await repositorioApi.listChanges(story.id));
      setLoadError('');
    } catch (cause) {
      setLoadError(repositorioErrorMessage(cause));
    }
  }, [story.id]);

  useEffect(() => { void loadChanges(); }, [loadChanges]);

  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitError('');
    if (!form.solicitud.trim()) {
      setSubmitError('Describa lo que pide Negocio.');
      return;
    }
    if (!sinVacio && !form.pregunta_sugerida.trim()) {
      setSubmitError('Escriba la pregunta que debió hacerse antes del grooming, o marque que no fue un vacío del análisis.');
      return;
    }
    setIsSending(true);
    try {
      const terminos = form.terminos.split(',').map((term) => term.trim()).filter(Boolean).slice(0, 10);
      const leccion = sinVacio ? {} : { causa_raiz: form.causa_raiz, pregunta_sugerida: form.pregunta_sugerida.trim(), terminos };
      const solicitud = form.solicitud.trim();
      await repositorioApi.registerChange({
        hu_id: story.id,
        solicitud,
        clasificacion: 'cambio_alcance',
        ...leccion,
      });
      // Un cambio de alcance siempre se analiza: se pasa directo al asistente sobre la misma HU.
      analizarCambio(solicitud);
    } catch (cause) {
      setSubmitError(repositorioErrorMessage(cause));
    } finally {
      setIsSending(false);
    }
  };

  const analizarCambio = (solicitud) => {
    navigate('/historias/nueva', { state: { prefill: construirRevision(story, solicitud), revisionDeId: story.id } });
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
                subtitle="Un cambio de alcance siempre se vuelve a analizar: al registrar la solicitud se abre el análisis de la misma HU. Para corregir redacción o datos mal escritos use Editar."
              >
      <form onSubmit={handleSubmit}>
        <AreaTextoComponent
          label="Solicitud de cambio"
          id="change-request"
          required
          rows={3}
          value={form.solicitud}
          onChange={update('solicitud')}
          placeholder="Qué pide Negocio que cambie respecto a la HU aprobada..."
          hint="Anonimice los datos personales antes de escribir."
        />

        <label style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-start', margin: '0.5rem 0 1rem', fontSize: '0.95rem' }}>
          <input id="change-sin-vacio" type="checkbox" checked={sinVacio} onChange={(event) => setSinVacio(event.target.checked)} style={{ marginTop: '0.2rem' }} />
          <span>No fue un vacío del análisis: Negocio cambió de decisión</span>
        </label>

        {!sinVacio && (
          <>
            <div className="grid-2">
              <SelectorComponent
                label="¿Qué no se preguntó a tiempo?"
                id="change-cause"
                required
                options={ROOT_CAUSES}
                value={form.causa_raiz}
                onChange={update('causa_raiz')}
                hint="El tipo de vacío que no se detectó antes de redactar la HU."
              />
              <CampoTextoComponent
                label="Términos clave (opcional, separados por coma)"
                id="change-terms"
                value={form.terminos}
                onChange={update('terminos')}
                placeholder="Ej. endoso, vigencia"
              />
            </div>
            <AreaTextoComponent
              label="Pregunta que debió hacerse antes del grooming"
              id="change-lesson"
              required
              rows={2}
              value={form.pregunta_sugerida}
              onChange={update('pregunta_sugerida')}
              hint="Quedará como lección propuesta; solo entra al checklist si el Product Owner la aprueba en Lecciones."
            />
          </>
        )}

        {submitError && <AlertaComponent type="danger" title="No se pudo registrar">{submitError}</AlertaComponent>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
          <BotonComponent type="submit" variant="primary" icon={Send} disabled={isSending}>
            {isSending ? 'Registrando...' : 'Registrar y analizar cambio'}
          </BotonComponent>
        </div>
      </form>
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
