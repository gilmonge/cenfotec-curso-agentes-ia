import React from 'react';

export const idPestana = (id) => `detalle-pestana-${id}`;
export const idPanel = (id) => `detalle-panel-${id}`;

// Menú de secciones: lateral en pantalla ancha y fila de pestañas en celular.
export const NavegacionSeccionesComponent = ({ secciones, activa, onSelect, etiqueta = 'Secciones de la historia' }) => (
  <div className="detalle-nav">
    <div role="tablist" aria-label={etiqueta} aria-orientation="vertical" className="detalle-nav__lista">
      {secciones.map((seccion, indice) => (
        <button
          key={seccion.id}
          id={idPestana(seccion.id)}
          type="button"
          role="tab"
          aria-selected={seccion.id === activa}
          aria-controls={idPanel(seccion.id)}
          className={`detalle-nav__item${seccion.id === activa ? ' detalle-nav__item--activa' : ''}`}
          onClick={() => onSelect(seccion.id)}
        >
          <span>{indice + 1}. {seccion.titulo}</span>
          {seccion.contador !== null && <span className="detalle-nav__contador">{seccion.contador}</span>}
        </button>
      ))}
    </div>
  </div>
);
