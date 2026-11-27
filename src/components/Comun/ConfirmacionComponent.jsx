import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { BotonComponent } from './BotonComponent';

// Confirmaciones con un modal propio de la aplicación (accesible y con el estilo del sistema),
// en lugar del cuadro nativo del navegador. Uso:
//   const confirmar = useConfirmacion();
//   if (!(await confirmar({ titulo: 'Descartar', mensaje: '¿…?', textoConfirmar: 'Descartar', peligro: true }))) return;
const ConfirmacionContext = createContext(null);

const DialogoConfirmacionComponent = ({ solicitud, onResponder }) => {
  const cancelarRef = useRef(null);

  useEffect(() => {
    cancelarRef.current?.focus();
    const alPresionar = (event) => {
      if (event.key === 'Escape') onResponder(false);
    };
    document.addEventListener('keydown', alPresionar);
    return () => document.removeEventListener('keydown', alPresionar);
  }, [onResponder]);

  return (
    <div className="modal-backdrop" onClick={() => onResponder(false)}>
      <section
        className="modal-content delete-story-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirmacion-titulo"
        aria-describedby="confirmacion-mensaje"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="confirmacion-titulo" className="delete-story-dialog__title">{solicitud.titulo}</h2>
        <div id="confirmacion-mensaje" className="delete-story-dialog__body">
          {String(solicitud.mensaje).split('\n').map((linea) => <p key={linea}>{linea}</p>)}
        </div>
        <div className="delete-story-dialog__actions">
          <button ref={cancelarRef} type="button" className="btn btn--outline btn--md" onClick={() => onResponder(false)}>
            {solicitud.textoCancelar ?? 'Cancelar'}
          </button>
          <BotonComponent
            variant={solicitud.peligro ? 'danger' : 'primary'}
            icon={solicitud.icono}
            onClick={() => onResponder(true)}
          >
            {solicitud.textoConfirmar ?? 'Confirmar'}
          </BotonComponent>
        </div>
      </section>
    </div>
  );
};

export const ConfirmacionProvider = ({ children }) => {
  const [solicitud, setSolicitud] = useState(null);
  const resolverRef = useRef(null);

  const confirmar = useCallback((opcion) => new Promise((resolver) => {
    resolverRef.current = resolver;
    setSolicitud(opcion);
  }), []);

  const responder = useCallback((respuesta) => {
    resolverRef.current?.(respuesta);
    resolverRef.current = null;
    setSolicitud(null);
  }, []);

  return (
    <ConfirmacionContext.Provider value={confirmar}>
      {children}
      {solicitud && <DialogoConfirmacionComponent solicitud={solicitud} onResponder={responder} />}
    </ConfirmacionContext.Provider>
  );
};

// Fuera del proveedor (por ejemplo, en una prueba que monta un componente suelto) confirma sin preguntar
// y lo deja registrado, para no bloquear la acción en silencio.
const confirmarSinProveedor = async (opcion) => {
  console.warn('Confirmación sin ConfirmacionProvider; se acepta por defecto:', opcion?.titulo);
  return true;
};

export const useConfirmacion = () => useContext(ConfirmacionContext) ?? confirmarSinProveedor;
