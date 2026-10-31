import React from 'react';

// Botón solo con ícono. La etiqueta sirve de nombre accesible y de descripción emergente (tooltip),
// que aparece con el mouse y también al enfocar con el teclado.
export const BotonIconoComponent = ({ icon: Icon, etiqueta, variant = 'outline', onClick, className = '', ...props }) => (
  <button
    type="button"
    className={`btn-icono btn-icono--${variant} ${className}`}
    aria-label={etiqueta}
    data-tooltip={etiqueta}
    onClick={onClick}
    {...props}
  >
    <Icon size={16} aria-hidden="true" />
  </button>
);
