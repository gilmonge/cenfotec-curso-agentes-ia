import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import { SeccionesConPestanasComponent } from './detalle/SeccionesConPestanasComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { CampoTextoComponent } from '../Comun/CampoTextoComponent';
import { AreaTextoComponent } from '../Comun/AreaTextoComponent';
import { SelectorComponent } from '../Comun/SelectorComponent';
import { InsigniaEstadoComponent } from '../Comun/InsigniaEstadoComponent';
import { EVENTO_SINCRONIZADO, getStoryById, updateStory } from '../../utils/storage';
import { buildRepositoryPayload, repositorioApi, repositorioErrorMessage } from '../../services/repositorioApi';
import { bitacoraConNota, leerBitacora } from '../../utils/bitacora';
import { camposEditados, registrarEdicion } from '../../utils/ediciones';
import { SIN_IDENTIFICAR, leerNombreUsuario } from '../../utils/usuarioActual';
import { CamposPlantillaComponent } from './CamposPlantillaComponent';
import { FIRMANTE_VACIO, etiquetaHistoria, limpiarLista, normalizarCodigoHu, requerimientoCambio } from '../../utils/plantillaHu';
import { criteriosCambiaron, criteriosParaEditar, limpiarCriterios, validarCriterios } from '../../utils/criterios';
import { OPCION_AREA_SOLICITANTE, OPCION_SISTEMA, armarOpcion } from '../../data/catalogos';
import { EditorCriteriosComponent } from './EditorCriteriosComponent';
import { rotuloCategoria } from '../../data/rotulosPregunta';
import { aplicarRespuestas, respuestasCambiaron, respuestasDePreguntas, textoPendiente } from '../../utils/preguntas';
import { Save, ArrowLeft } from 'lucide-react';
import { AlertaComponent } from '../Comun/AlertaComponent';

export const EditarHistoriaUsuarioComponent = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const ubicacion = useLocation();
  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);

  // Form states matching Accordion sections
  const [title, setTitle] = useState('');
  const [status, setStatus] = useState('revisada');
  const [infoType, setInfoType] = useState('Minuta');
  const [description, setDescription] = useState('');

  const [asA, setAsA] = useState('');
  const [iWant, setIWant] = useState('');
  const [soThat, setSoThat] = useState('');

  const [notaNueva, setNotaNueva] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [errorGuardado, setErrorGuardado] = useState('');
  const [system, setSystem] = useState('');
  const [codigoHu, setCodigoHu] = useState('');
  const [requester, setRequester] = useState('');
  const [acceptanceCriteria, setAcceptanceCriteria] = useState([]);
  const [criteriosError, setCriteriosError] = useState('');
  const [listaRespuesta, setListaRespuesta] = useState([]);
  const [plantilla, setPlantilla] = useState({ number: '', benefits: [''], signers: { ...FIRMANTE_VACIO } });

  useEffect(() => {
    let cargada = false;
    const cargar = () => {
    const data = getStoryById(id);
    if (data) {
      cargada = true;
      setStory(data);
      setTitle(data.title || '');
      setStatus(data.status || 'revisada');
      setInfoType(data.infoType || 'Minuta');
      setDescription(data.description || '');

      if (data.userStory) {
        setAsA(data.userStory.asA || '');
        setIWant(data.userStory.iWant || '');
        setSoThat(data.userStory.soThat || '');
      }

      setListaRespuesta(respuestasDePreguntas(data.questions));
      setSystem(data.system || '');
      setCodigoHu(data.codigoHu || data.area || '');
      setRequester(data.requester || '');
      setAcceptanceCriteria(criteriosParaEditar(data.acceptanceCriteria));
      setPlantilla({
        number: data.number || '',
        benefits: data.benefits?.length ? data.benefits : [''],
        signers: { ...FIRMANTE_VACIO, ...(data.signers || {}) },
      });
    }
    setLoading(false);
    };
    cargar();
    // Si se abrió desde otro dispositivo, la historia llega con la sincronización; nunca se pisan cambios en curso.
    const alSincronizar = () => { if (!cargada) cargar(); };
    window.addEventListener(EVENTO_SINCRONIZADO, alSincronizar);
    return () => window.removeEventListener(EVENTO_SINCRONIZADO, alSincronizar);
  }, [id]);

  if (loading) {
    return (
      <div style={{ padding: '3rem', textCenter: 'center' }}>
        Cargando historia de usuario...
      </div>
    );
  }

  if (!story) {
    return (
      <div>
        <AlertaComponent type="danger" title="Historia no encontrada">
          No se encontró la historia con ID {id}.
        </AlertaComponent>
        <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => navigate('/historias')}>
          Volver a historias
        </BotonComponent>
      </div>
    );
  }

  const esAprobada = story.status === 'aprobada';
  const autor = leerNombreUsuario() || SIN_IDENTIFICAR;

  const datosEditados = () => ({
    acceptanceCriteria: limpiarCriterios(acceptanceCriteria),
    title,
    userStory: { asA, iWant, soThat },
    system: system.trim(),
    codigoHu: normalizarCodigoHu(codigoHu),
    requester: requester.trim(),
    number: plantilla.number.trim(),
    benefits: limpiarLista(plantilla.benefits),
    signers: plantilla.signers,
    // La bitácora conserva las notas anteriores y agrega la nueva con fecha y autor.
    bitacora: bitacoraConNota(story, notaNueva, { autor }),
  });

  // HU aprobada: se corrige en el lugar. No pasa por el agente ni sube la revisión; queda el registro de la edición
  // y el Repositorio de HU (la memoria del agente) se actualiza con el texto corregido.
  const guardarAprobada = async () => {
    const datos = datosEditados();
    const campos = camposEditados(story, { ...datos, notaNueva });
    if (campos.length === 0) {
      navigate(`/historias/${id}`);
      return;
    }
    setGuardando(true);
    try {
      await repositorioApi.saveStory(buildRepositoryPayload({
        id: story.id,
        code: datos.number,
        title: datos.title,
        infoType: story.infoType ?? 'Minuta',
        description: story.description ?? '',
        userStory: datos.userStory,
        acceptanceCriteria: datos.acceptanceCriteria,
        questions: story.questions ?? [],
      }));
    } catch (cause) {
      setErrorGuardado(repositorioErrorMessage(cause));
      setGuardando(false);
      return;
    }
    updateStory(id, { ...datos, ediciones: registrarEdicion(story, campos, { autor }) });
    navigate(`/historias/${id}`);
  };

  const handleSave = (e) => {
    e.preventDefault();
    setErrorGuardado('');
    const validacion = validarCriterios(acceptanceCriteria);
    if (!validacion.ok) {
      setCriteriosError(validacion.error);
      return;
    }
    setCriteriosError('');
    if (esAprobada) {
      void guardarAprobada();
      return;
    }
    const criteriosEditados = criteriosCambiaron(story.acceptanceCriteria, acceptanceCriteria);
    const requerimientoEditado = requerimientoCambio(story, { title, infoType, description });
    const respuestasEditadas = respuestasCambiaron(story.questions, listaRespuesta);
    const preguntaActualizada = aplicarRespuestas(story.questions, listaRespuesta);
    const updated = updateStory(id, {
      // Cambiar el requerimiento o agregar/cambiar respuestas de Negocio obliga a analizar de nuevo.
      ...(requerimientoEditado || respuestasEditadas ? { analisisDesactualizado: true } : {}),
      ...(respuestasEditadas ? { respuestasNuevas: true } : {}),
      ...(story.questions?.length ? { questions: preguntaActualizada, pendingQuestions: textoPendiente(preguntaActualizada) } : {}),
      // Cambiar criterios no obliga a analizar de nuevo: solo se avisa que cambiaron desde la última revisión.
      ...(criteriosEditados ? { criteriosModificados: true } : {}),
      ...datosEditados(),
      status,
      infoType,
      description,
    });

    if (updated) {
      navigate(`/historias/${id}`);
    }
  };

  return (
    <div>
      <TituloPaginaComponent
        title={`Editar Historia ${etiquetaHistoria(story)}`}
        description="Use el menú de secciones para modificar los bloques de la historia de usuario."
        action={
          <div className="page-title__actions">
            <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => navigate('/historias')}>
              Volver
            </BotonComponent>
          </div>
        }
      />

      <form onSubmit={handleSave}>
        {esAprobada && (
          <AlertaComponent type="info" title="Historia aprobada">
            Edite para corregir redacción o datos mal escritos: se guarda en el lugar y queda registrado quién y cuándo.
            Si cambia lo que se pide, use Solicitar cambio para que se vuelva a analizar.
          </AlertaComponent>
        )}
        {errorGuardado && <AlertaComponent type="danger" title="No se pudo guardar">{errorGuardado}</AlertaComponent>}
        {criteriosError && (
          <AlertaComponent type="danger" title="Revise los criterios de aceptación">
            {criteriosError} Están en la sección 5.
          </AlertaComponent>
        )}
        <SeccionesConPestanasComponent
          etiqueta="Secciones de la edición"
          inicial={!esAprobada && ubicacion.state?.abrirPreguntas ? 'preguntas' : 'requerimiento'}
          secciones={[
          {
      id: 'requerimiento',
      titulo: 'Requerimiento inicial',
      contenido: (
        <TarjetaComponent title="Requerimiento inicial">
            <CampoTextoComponent
              label="Título del Requerimiento / Historia"
              id="title"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />

            {!esAprobada && (<>
            <div className="grid-2">
              <SelectorComponent
                label="Estado de la Historia"
                id="status"
                options={[
                  { value: 'borrador', label: 'Borrador' },
                  { value: 'en_analisis', label: 'En análisis' },
                  { value: 'pendiente_de_informacion', label: 'Pendiente de información' },
                  { value: 'generada', label: 'Generada' },
                  { value: 'revisada', label: 'Revisada' }
                ]}
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                hint={status === 'pendiente_de_informacion' && story.questions?.length > 0 && textoPendiente(aplicarRespuestas(story.questions, listaRespuesta)).length === 0
                  ? 'Ya no quedan preguntas pendientes: puede cambiar el estado a "Revisada".'
                  : undefined}
              />

              <SelectorComponent
                label="Tipo de información recibida"
                id="infoType"
                options={[
                  { value: 'Descripción libre', label: 'Descripción libre' },
                  { value: 'Minuta', label: 'Minuta de reunión' },
                  { value: 'Notas de conversación', label: 'Notas de conversación' },
                  { value: 'Otro', label: 'Otro' }
                ]}
                value={infoType}
                onChange={(e) => setInfoType(e.target.value)}
              />
            </div>

            <AreaTextoComponent
              label="Descripción de negocio"
              id="description"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            </>)}
        </TarjetaComponent>
      ),
    },
          {
      id: 'analisis',
      titulo: 'Análisis del requerimiento',
      visible: !esAprobada,
      contenido: (
        <TarjetaComponent title="Análisis del requerimiento">
            <div className="grid-2">
              <div>
                <h5 style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--color-success-text)', marginBottom: '0.5rem' }}>
                  Datos conocidos ({story.analysis?.knownData?.length || 0})
                </h5>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                  {story.analysis?.knownData?.map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '0.35rem' }}>{item}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h5 style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--color-danger-text)', marginBottom: '0.5rem' }}>
                  Información faltante ({story.analysis?.missingData?.length || 0})
                </h5>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                  {story.analysis?.missingData?.map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '0.35rem' }}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
        </TarjetaComponent>
      ),
    },
          {
      id: 'preguntas',
      titulo: 'Preguntas para Negocio',
      contador: story.questions?.length || 0,
      visible: !esAprobada,
      contenido: (
        <TarjetaComponent title="Preguntas para Negocio">
            {story.questions && story.questions.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {story.questions.map((q, idx) => (
                  <div key={idx} style={{ padding: '0.85rem', backgroundColor: 'var(--color-surface)', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                      <strong style={{ fontSize: '0.875rem', color: 'var(--color-secondary-text)' }}>{rotuloCategoria(q.category)}</strong>
                      <InsigniaEstadoComponent status={(listaRespuesta[idx] ?? '').trim() ? 'respondida' : 'pendiente'} />
                    </div>
                    <p style={{ fontSize: '0.9rem', fontWeight: '600', color: 'var(--color-text-primary)' }}>{q.question}</p>
                    <AreaTextoComponent
                      label="Respuesta de Negocio"
                      id={`respuesta-${idx}`}
                      rows={2}
                      value={listaRespuesta[idx] ?? ''}
                      placeholder="Escriba la respuesta de Negocio…"
                      onChange={(e) => setListaRespuesta((previa) => previa.map((valor, i) => (i === idx ? e.target.value : valor)))}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>No hay preguntas registradas.</p>
            )}
        </TarjetaComponent>
      ),
    },
          {
      id: 'historia',
      titulo: 'Historia de usuario',
      contenido: (
        <TarjetaComponent title="Historia de usuario">
            <CampoTextoComponent
              label="Como (Rol / Actor)"
              id="asA"
              value={asA}
              onChange={(e) => setAsA(e.target.value)}
              placeholder="Ej. Usuario del sistema"
            />

            <CampoTextoComponent
              label="Quiero (Acción / Necesidad)"
              id="iWant"
              value={iWant}
              onChange={(e) => setIWant(e.target.value)}
              placeholder="Ej. Modificar una cobertura asociada a una póliza"
            />

            <CampoTextoComponent
              label="Para (Beneficio / Valor)"
              id="soThat"
              value={soThat}
              onChange={(e) => setSoThat(e.target.value)}
              placeholder="Ej. Mantener actualizada la información contractual"
            />
        </TarjetaComponent>
      ),
    },
          {
      id: 'criterios',
      titulo: 'Criterios de aceptación',
      contador: acceptanceCriteria.length,
      contenido: (
        <TarjetaComponent title="Criterios de aceptación">
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '0.75rem' }}>
              Cambiar los criterios no exige un nuevo análisis: solo se vuelve a analizar si cambian el requerimiento o las respuestas.
            </p>
            <EditorCriteriosComponent
              valor={acceptanceCriteria}
              alCambiar={setAcceptanceCriteria}
              prefijoId="edit-criterio"
              error={criteriosError}
            />
        </TarjetaComponent>
      ),
    },
          {
      id: 'plantilla',
      titulo: 'Datos de la plantilla',
      contenido: (
        <TarjetaComponent title="Datos de la plantilla">
            <SelectorComponent label="Sistema" id="system-edit" options={armarOpcion(OPCION_SISTEMA, system, 'Seleccione un sistema')} value={system} onChange={(e) => setSystem(e.target.value)} />
            <CampoTextoComponent label="Código de HU" id="codigo-hu-edit" value={codigoHu} onChange={(e) => setCodigoHu(e.target.value)} />
            <SelectorComponent label="Área solicitante" id="requester-edit" options={armarOpcion(OPCION_AREA_SOLICITANTE, requester, 'Seleccione un área')} value={requester} onChange={(e) => setRequester(e.target.value)} />
            <CamposPlantillaComponent valor={plantilla} alCambiar={(cambio) => setPlantilla((previo) => ({ ...previo, ...cambio }))} prefijoId="edit" />
        </TarjetaComponent>
      ),
    },
          {
      id: 'observaciones',
      titulo: 'Observaciones y notas',
      contenido: (
        <TarjetaComponent title="Observaciones y notas">
            {leerBitacora(story).length > 0 && (
              <ul style={{ margin: '0 0 1rem', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {leerBitacora(story).map((nota, indice) => (
                  <li key={indice} style={{ borderLeft: '3px solid var(--color-border)', paddingLeft: '0.75rem', fontSize: '0.9rem' }}>
                    <span style={{ display: 'block', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                      {nota.fecha || 'Sin fecha'} · {nota.autor || SIN_IDENTIFICAR}
                    </span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{nota.texto}</span>
                  </li>
                ))}
              </ul>
            )}
            <AreaTextoComponent
              label="Agregar nota"
              id="observations-edit"
              rows={3}
              value={notaNueva}
              onChange={(e) => setNotaNueva(e.target.value)}
              placeholder="Notas para el equipo de desarrollo, arquitectura o QA. Se guarda con su fecha y autor..."
            />
        </TarjetaComponent>
      ),
    },
          ]}
        />

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2rem', gap: '1rem' }}>
          <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => navigate('/historias')}>
            Cancelar
          </BotonComponent>
          <BotonComponent type="submit" variant="primary" icon={Save} size="lg" disabled={guardando}>
            Guardar Todos los Cambios
          </BotonComponent>
        </div>
      </form>
    </div>
  );
};
