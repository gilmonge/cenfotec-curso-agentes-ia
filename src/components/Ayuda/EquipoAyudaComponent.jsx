import React from 'react';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import { EQUIPO } from '../../data/ayudaDocumentacion';

export const EquipoAyudaComponent = () => (
  <TarjetaComponent title="Equipo del proyecto" subtitle="Quienes crearon el sistema, en orden alfabético">
    <ul className="ayuda-item__puntos">
      {EQUIPO.map((nombre) => <li key={nombre}>{nombre}</li>)}
    </ul>
  </TarjetaComponent>
);
