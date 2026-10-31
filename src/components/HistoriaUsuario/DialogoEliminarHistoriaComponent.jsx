import React, { useEffect, useRef } from 'react';
import { Trash2 } from 'lucide-react';
import { BotonComponent } from '../Comun/BotonComponent';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { etiquetaHistoria } from '../../utils/plantillaHu';

/** Confirmación accesible para eliminar una historia (reemplaza a window.confirm). */
export const DialogoEliminarHistoriaComponent = ({ story, isDeleting, error, onCancel, onConfirm }) => {
  const cancelRef = useRef(null);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onCancel]);

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <section
        className="modal-content delete-story-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-story-title"
        aria-describedby="delete-story-description"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="delete-story-title" className="delete-story-dialog__title">
          Eliminar historia {etiquetaHistoria(story)}
        </h2>
        <div id="delete-story-description" className="delete-story-dialog__body">
          <p><strong>{story.title}</strong></p>
          <p>Esta acción no se puede deshacer.</p>
          {story.repositorySynced && (
            <p>
              También se eliminará del Repositorio de HU, junto con sus solicitudes de cambio y lecciones, y el agente
              dejará de usarla como referencia.
            </p>
          )}
          {error && <AlertaComponent type="danger" title="No se pudo eliminar">{error}</AlertaComponent>}
        </div>
        <div className="delete-story-dialog__actions">
          <button ref={cancelRef} type="button" className="btn btn--outline btn--md" onClick={onCancel} disabled={isDeleting}>
            Conservar historia
          </button>
          <BotonComponent variant="danger" icon={Trash2} onClick={onConfirm} disabled={isDeleting}>
            {isDeleting ? 'Eliminando...' : 'Eliminar historia'}
          </BotonComponent>
        </div>
      </section>
    </div>
  );
};
