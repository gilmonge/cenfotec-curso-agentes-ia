import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { EVENTO_SINCRONIZADO, getStoryById } from '../../utils/storage';
import { construirReanalisis } from '../../utils/plantillaHu';
import { EncabezadoHistoriaComponent } from './detalle/EncabezadoHistoriaComponent';
import { AvisosHistoriaComponent } from './detalle/AvisosHistoriaComponent';
import { NavegacionSeccionesComponent, idPanel, idPestana } from './detalle/NavegacionSeccionesComponent';
import { SeccionHistoriaComponent } from './detalle/SeccionHistoriaComponent';
import { SeccionCriteriosComponent } from './detalle/SeccionCriteriosComponent';
import { SeccionPreguntasPendientesComponent } from './detalle/SeccionPreguntasPendientesComponent';
import { SeccionObservacionesComponent } from './detalle/SeccionObservacionesComponent';
import { SeccionRevisionesComponent } from './detalle/SeccionRevisionesComponent';
import { SeccionAnalisisComponent } from './detalle/SeccionAnalisisComponent';
import { SeccionPlantillaComponent } from './detalle/SeccionPlantillaComponent';
import { SECCION_INICIAL, construirSecciones, seccionActiva } from './detalle/secciones';

// Contenedor: carga la HU, decide la navegación y delega cada sección en su componente.
// Todas las secciones quedan montadas (solo se oculta la inactiva) para no perder lo escrito al cambiar de pestaña.
export const DetalleHistoriaUsuarioComponent = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [story, setStory] = useState(null);
  const [seccionPedida, setSeccionPedida] = useState(SECCION_INICIAL);

  useEffect(() => {
    const refrescar = () => setStory(getStoryById(id));
    refrescar();
    window.addEventListener(EVENTO_SINCRONIZADO, refrescar);
    return () => window.removeEventListener(EVENTO_SINCRONIZADO, refrescar);
  }, [id]);

  if (!story) {
    return (
      <div>
        <AlertaComponent type="danger" title="Historia no encontrada">
          No se encontró ninguna historia de usuario con el identificador {id}.
        </AlertaComponent>
        <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => navigate('/historias')}>
          Volver al listado
        </BotonComponent>
      </div>
    );
  }

  const secciones = construirSecciones(story);
  const activa = seccionActiva(secciones, seccionPedida);
  const contenido = {
    historia: <SeccionHistoriaComponent story={story} />,
    criterios: <SeccionCriteriosComponent story={story} />,
    preguntas: story.pendingQuestions?.length > 0 && (
      <SeccionPreguntasPendientesComponent
        story={story}
        onResponder={() => navigate(`/historias/${story.id}/editar`, { state: { abrirPreguntas: true } })}
      />
    ),
    observaciones: <SeccionObservacionesComponent story={story} />,
    revisiones: <SeccionRevisionesComponent story={story} />,
    analisis: story.analysis && <SeccionAnalisisComponent story={story} />,
    plantilla: <SeccionPlantillaComponent story={story} />,
  };

  return (
    <div>
      <EncabezadoHistoriaComponent
        story={story}
        onVolver={() => navigate('/historias')}
      />
      <AvisosHistoriaComponent
        story={story}
        onReanalizar={() => navigate('/historias/nueva', { state: { prefill: construirReanalisis(story), reanalizarId: story.id } })}
      />
      <div className="detalle-layout">
        <NavegacionSeccionesComponent secciones={secciones} activa={activa} onSelect={setSeccionPedida} />
        <div className="detalle-contenido">
          {secciones.map((seccion) => (
            <div
              key={seccion.id}
              id={idPanel(seccion.id)}
              role="tabpanel"
              aria-labelledby={idPestana(seccion.id)}
              hidden={seccion.id !== activa}
              className="detalle-panel"
            >
              {contenido[seccion.id]}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
