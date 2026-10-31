import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { SolicitudCambioComponent } from '../SolicitudCambio/SolicitudCambioComponent';
import { EVENTO_SINCRONIZADO, getStoryById } from '../../utils/storage';
import { etiquetaHistoria } from '../../utils/plantillaHu';

// Página propia de la solicitud de cambio: el detalle de la HU queda solo para consultar.
export const SolicitarCambioHistoriaComponent = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [story, setStory] = useState(null);

  useEffect(() => {
    const refrescar = () => setStory(getStoryById(id));
    refrescar();
    window.addEventListener(EVENTO_SINCRONIZADO, refrescar);
    return () => window.removeEventListener(EVENTO_SINCRONIZADO, refrescar);
  }, [id]);

  const volver = (
    <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => navigate('/historias')}>
      Volver
    </BotonComponent>
  );

  if (!story || story.status !== 'aprobada') {
    return (
      <div>
        <AlertaComponent type="warning" title="No se puede solicitar un cambio">
          {story
            ? 'Solo una historia aprobada admite solicitudes de cambio. Antes de aprobarse, use Editar.'
            : `No se encontró ninguna historia de usuario con el identificador ${id}.`}
        </AlertaComponent>
        {volver}
      </div>
    );
  }

  return (
    <div>
      <TituloPaginaComponent
        title={`Solicitar cambio — ${etiquetaHistoria(story)} ${story.title}`}
        description="Cambios de alcance sobre una historia aprobada."
        action={volver}
      />
      <SolicitudCambioComponent story={story} />
    </div>
  );
};
