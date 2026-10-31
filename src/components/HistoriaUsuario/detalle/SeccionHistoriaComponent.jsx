import React from 'react';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { AlertaComponent } from '../../Comun/AlertaComponent';
import { etiquetaRevision, numeroRevision } from '../../../utils/revisiones';

export const SeccionHistoriaComponent = ({ story }) => (
  <>
    {numeroRevision(story) > 1 && story.motivoRevision && (
      <AlertaComponent type="info" title={`${etiquetaRevision(story)} vigente`}>
        Motivo del cambio: {story.motivoRevision}
      </AlertaComponent>
    )}
    <TarjetaComponent title="Historia de Usuario" subtitle="Formato estándar ágil de requerimiento">
      <div className="story-structure">
        <div className="story-structure__item">
          <div className="story-structure__label">Como:</div>
          <div className="story-structure__content">{story.userStory?.asA || 'Usuario del sistema'}</div>
        </div>
        <div className="story-structure__item">
          <div className="story-structure__label">Quiero:</div>
          <div className="story-structure__content">{story.userStory?.iWant || 'Ejecutar la acción requerida'}</div>
        </div>
        <div className="story-structure__item">
          <div className="story-structure__label">Para:</div>
          <div className="story-structure__content">{story.userStory?.soThat || 'Obtener el beneficio de negocio esperable'}</div>
        </div>
      </div>
    </TarjetaComponent>
  </>
);
