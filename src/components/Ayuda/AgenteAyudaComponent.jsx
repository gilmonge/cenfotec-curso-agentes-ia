import React from 'react';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import { AGENTE_ANALISTA } from '../../data/ayudaDocumentacion';

const Lista = ({ titulo, elementos }) => (
  <div className="ayuda-item">
    <h5 className="ayuda-item__titulo">{titulo}</h5>
    <ul className="ayuda-item__puntos">
      {elementos.map((elemento) => <li key={elemento}>{elemento}</li>)}
    </ul>
  </div>
);

export const AgenteAyudaComponent = () => (
  <TarjetaComponent title="El agente que trabaja en el sistema" subtitle="Agente Analista de Requerimientos">
    <p className="ayuda-item__texto">{AGENTE_ANALISTA.rol}</p>
    <div className="ayuda-lista">
      <Lista titulo="Qué hace" elementos={AGENTE_ANALISTA.hace} />
      <Lista titulo="Con qué fuentes trabaja" elementos={AGENTE_ANALISTA.herramientas} />
      <Lista titulo="Qué no hace" elementos={AGENTE_ANALISTA.noHace} />
      <div className="ayuda-item">
        <h5 className="ayuda-item__titulo">Qué aprende</h5>
        <p className="ayuda-item__texto">{AGENTE_ANALISTA.memoria}</p>
      </div>
      <div className="ayuda-item">
        <h5 className="ayuda-item__titulo">Lo que falta</h5>
        <p className="ayuda-item__texto">{AGENTE_ANALISTA.pendientes}</p>
      </div>
    </div>
  </TarjetaComponent>
);
