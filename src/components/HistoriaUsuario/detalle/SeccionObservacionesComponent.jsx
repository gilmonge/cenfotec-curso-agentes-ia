import React from 'react';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { BitacoraComponent } from './BitacoraComponent';

// Bitácora de seguimiento: decisiones, dependencias, pendientes técnicos, supuestos, devoluciones y notas.
// Solo se puede cambiar el estado de las dependencias y los pendientes técnicos.
export const SeccionObservacionesComponent = ({ story, onCambiarEstado }) => (
  <TarjetaComponent title="Observaciones y aclaraciones" subtitle="Bitácora de seguimiento para el grooming">
    <BitacoraComponent story={story} onCambiarEstado={onCambiarEstado} />
  </TarjetaComponent>
);
