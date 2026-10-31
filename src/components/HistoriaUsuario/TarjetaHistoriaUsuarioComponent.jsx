import React from 'react';
import { Calendar, Tag, UserRound } from 'lucide-react';
import { InsigniaEstadoComponent } from '../Comun/InsigniaEstadoComponent';
import { AccionesHistoriaComponent } from './AccionesHistoriaComponent';
import { autorDe } from '../../utils/usuarioActual';
import { etiquetaHistoria } from '../../utils/plantillaHu';

// variante: 'cuadro' (tarjeta) o 'lista' (fila compacta)
export const TarjetaHistoriaUsuarioComponent = ({ story, onView, onEdit, onRequestChange, onDelete, variante = 'cuadro' }) => {
  const acciones = (
    <div className="story-card__actions">
      <AccionesHistoriaComponent
        story={story}
        onVer={() => onView(story.id)}
        onEditar={() => onEdit(story.id)}
        onSolicitarCambio={() => onRequestChange(story.id)}
        onEliminar={onDelete}
      />
    </div>
  );

  const metadatos = (
    <div className="story-card__meta">
      <span className="story-card__meta-item"><Tag size={13} />{story.type || 'General'}</span>
      <span className="story-card__meta-item"><Calendar size={13} />{story.createdAt}</span>
    </div>
  );

  const modificacion = (
    <p className="story-card__modified">
      <UserRound size={13} /> Modificado por {autorDe(story)}{story.updatedAt ? ` · ${story.updatedAt}` : ''}
    </p>
  );

  if (variante === 'lista') {
    return (
      <div className="card story-card story-card--lista">
        <span className="story-card__id">{etiquetaHistoria(story)}</span>
        <div className="story-card__body">
          <h3 className="story-card__title">{story.title}</h3>
          {story.description && <p className="story-card__description">{story.description}</p>}
          {modificacion}
        </div>
        <InsigniaEstadoComponent status={story.status} />
        {metadatos}
        {acciones}
      </div>
    );
  }

  return (
    <div className="card story-card story-card--cuadro">
      <div>
        <div className="story-card__header">
          <span className="story-card__id">{etiquetaHistoria(story)}</span>
          <InsigniaEstadoComponent status={story.status} />
        </div>
        <h3 className="story-card__title">{story.title}</h3>
        {story.description && <p className="story-card__description">{story.description}</p>}
        {metadatos}
        {modificacion}
      </div>
      {acciones}
    </div>
  );
};
