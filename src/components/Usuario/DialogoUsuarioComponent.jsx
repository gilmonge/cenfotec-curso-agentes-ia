import React, { useEffect, useRef, useState } from 'react';
import { CampoTextoComponent } from '../Comun/CampoTextoComponent';
import { BotonComponent } from '../Comun/BotonComponent';

/** Pide el nombre de la persona para registrar quién crea y modifica las historias. */
export const DialogoUsuarioComponent = ({ nombreActual, alGuardar, alCerrar }) => {
  const [valor, setValor] = useState(nombreActual);
  const campoRef = useRef(null);

  useEffect(() => {
    campoRef.current?.focus();
  }, []);

  useEffect(() => {
    const alTeclear = (evento) => {
      if (evento.key === 'Escape') alCerrar();
    };
    document.addEventListener('keydown', alTeclear);
    return () => document.removeEventListener('keydown', alTeclear);
  }, [alCerrar]);

  const enviar = (evento) => {
    evento.preventDefault();
    alGuardar(valor);
  };

  return (
    <div className="modal-backdrop" onClick={alCerrar}>
      <form
        className="modal-content usuario-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="usuario-dialog-titulo"
        onClick={(evento) => evento.stopPropagation()}
        onSubmit={enviar}
      >
        <h2 id="usuario-dialog-titulo" className="usuario-dialog__title">¿Quién está usando la aplicación?</h2>
        <p className="form-hint">
          Su nombre se guarda solo en este navegador y queda registrado como «Creado por» y «Modificado por» en las historias.
        </p>
        <CampoTextoComponent
          label="Nombre"
          id="usuario-nombre"
          ref={campoRef}
          value={valor}
          maxLength={60}
          placeholder="Ej. Nombre Apellido"
          onChange={(evento) => setValor(evento.target.value)}
        />
        <div className="usuario-dialog__actions">
          <button type="button" className="btn btn--outline btn--md" onClick={alCerrar}>Cancelar</button>
          <BotonComponent type="submit" variant="primary">Guardar nombre</BotonComponent>
        </div>
      </form>
    </div>
  );
};
