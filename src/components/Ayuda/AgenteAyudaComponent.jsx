import React from 'react';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import { AGENTES, LIMITE_AGENTE, MEMORIA_AGENTE, PROPIEDAD_AGENTE } from '../../data/ayudaDocumentacion';

const Lista = ({ titulo, elementos }) => (
  <div className="ayuda-item">
    <h5 className="ayuda-item__titulo">{titulo}</h5>
    <ul className="ayuda-item__puntos">
      {elementos.map((elemento) => <li key={elemento}>{elemento}</li>)}
    </ul>
  </div>
);

export const AgenteAyudaComponent = () => (
  <>
    <TarjetaComponent title="Los agentes del sistema" subtitle="Cuatro agentes, cada uno con su rol, sus herramientas y su memoria">
      <p className="ayuda-item__texto">
        El Analista y el Asesor Técnico trabajan en equipo: después del primer análisis, el Asesor revisa qué otras
        funciones afecta el cambio y las preguntas de los dos llegan a Negocio en una sola ronda. Luego el
        Redactor-Revisor escribe la historia y el Product Owner la aprueba. El Gestor de Cambios entra después,
        cuando llega una solicitud de cambio sobre una HU aprobada.
      </p>
      <div className="ayuda-lista">
        {AGENTES.map((agente) => (
          <div className="ayuda-item" key={agente.nombre}>
            <h5 className="ayuda-item__titulo">{agente.nombre}</h5>
            <p className="ayuda-item__texto">{agente.rol}</p>
            <ul className="ayuda-item__puntos">
              {agente.hace.map((texto) => <li key={texto}>{texto}</li>)}
            </ul>
            <p className="ayuda-item__texto"><strong>Fuentes:</strong> {agente.fuentes}</p>
          </div>
        ))}
      </div>
    </TarjetaComponent>

    <TarjetaComponent title="Por qué son agentes" subtitle="Las cuatro propiedades que cumplen todos">
      <div className="ayuda-lista">
        {PROPIEDAD_AGENTE.map((propiedad) => (
          <div className="ayuda-item" key={propiedad.titulo}>
            <h5 className="ayuda-item__titulo">{propiedad.titulo}</h5>
            <p className="ayuda-item__texto">{propiedad.texto}</p>
          </div>
        ))}
        <Lista titulo="Qué no hacen" elementos={LIMITE_AGENTE} />
        <div className="ayuda-item">
          <h5 className="ayuda-item__titulo">Qué aprenden</h5>
          <p className="ayuda-item__texto">{MEMORIA_AGENTE}</p>
        </div>
      </div>
    </TarjetaComponent>
  </>
);
