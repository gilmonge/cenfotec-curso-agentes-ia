import React, { useState } from 'react';
import { NavegacionSeccionesComponent, idPanel, idPestana } from './NavegacionSeccionesComponent';

// Menú de secciones con sus paneles, igual que el detalle. Todos los paneles quedan montados (solo se oculta el
// inactivo) para no perder lo escrito en un formulario al cambiar de sección.
// secciones: [{ id, titulo, contador?, visible?, contenido }]
export const SeccionesConPestanasComponent = ({ secciones, inicial, etiqueta }) => {
  const visibles = secciones.filter((seccion) => seccion.visible !== false);
  const [pedida, setPedida] = useState(inicial);
  const activa = visibles.find((seccion) => seccion.id === pedida)?.id ?? visibles[0]?.id;

  return (
    <div className="detalle-layout">
      <NavegacionSeccionesComponent
        secciones={visibles.map(({ id, titulo, contador }) => ({ id, titulo, contador: contador ?? null }))}
        activa={activa}
        onSelect={setPedida}
        etiqueta={etiqueta}
      />
      <div className="detalle-contenido">
        {visibles.map((seccion) => (
          <div
            key={seccion.id}
            id={idPanel(seccion.id)}
            role="tabpanel"
            aria-labelledby={idPestana(seccion.id)}
            hidden={seccion.id !== activa}
            className="detalle-panel"
          >
            {seccion.contenido}
          </div>
        ))}
      </div>
    </div>
  );
};
