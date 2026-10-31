import React, { useEffect, useRef } from 'react';

export function DialogoEliminarConversacionComponent({ onCancel, onConfirm }) {
  const cancelRef = useRef(null);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  return (
    <div className="analyst-chat-delete-overlay">
      <section
        className="analyst-chat-delete-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="analyst-delete-title"
        aria-describedby="analyst-delete-description"
      >
        <h3 id="analyst-delete-title">Eliminar conversación</h3>
        <p id="analyst-delete-description">Se borrarán la conversación y su contexto en este servicio.</p>
        <div className="analyst-chat-delete-dialog__actions">
          <button ref={cancelRef} type="button" onClick={onCancel}>Conservar conversación</button>
          <button type="button" onClick={onConfirm}>Eliminar</button>
        </div>
      </section>
    </div>
  );
}
