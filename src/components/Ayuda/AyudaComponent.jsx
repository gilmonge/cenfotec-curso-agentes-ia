import React from 'react';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { SeccionesConPestanasComponent } from '../HistoriaUsuario/detalle/SeccionesConPestanasComponent';
import { TarjetaItemsAyudaComponent } from './TarjetaItemsAyudaComponent';
import { AgenteAyudaComponent } from './AgenteAyudaComponent';
import { EjemploHuAyudaComponent } from './EjemploHuAyudaComponent';
import { EquipoAyudaComponent } from './EquipoAyudaComponent';
import {
  ACCIONES_HISTORIA, NAVEGACION_ASISTENTE, PASOS_ASISTENTE, PENDIENTES, TECNOLOGIAS,
} from '../../data/ayudaDocumentacion';

const SECCIONES = [
  {
    id: 'asistente',
    titulo: 'Pasos del asistente',
    contenido: (
      <TarjetaItemsAyudaComponent
        title="¿Cómo funciona el Asistente IA?"
        subtitle="Flujo principal de 5 pasos"
        items={PASOS_ASISTENTE}
      >
        <h5 className="ayuda-item__titulo ayuda-item__titulo--aparte">Cómo moverse entre pasos</h5>
        <ul className="ayuda-item__puntos">
          {NAVEGACION_ASISTENTE.map((texto) => <li key={texto}>{texto}</li>)}
        </ul>
      </TarjetaItemsAyudaComponent>
    ),
  },
  {
    id: 'acciones',
    titulo: 'Acciones sobre una HU',
    contenido: (
      <TarjetaItemsAyudaComponent
        title="Qué hace cada acción"
        subtitle="Íconos en el listado de historias (con una breve descripción al pasar el cursor)"
        items={ACCIONES_HISTORIA}
      />
    ),
  },
  { id: 'agente', titulo: 'El agente Analista', contenido: <AgenteAyudaComponent /> },
  { id: 'ejemplo', titulo: 'Ejemplo de HU generada', contenido: <EjemploHuAyudaComponent /> },
  {
    id: 'tecnologias',
    titulo: 'Tecnologías',
    contenido: <TarjetaItemsAyudaComponent title="Con qué está hecha la aplicación" items={TECNOLOGIAS} />,
  },
  {
    id: 'pendientes',
    titulo: 'Por definir',
    contenido: (
      <TarjetaItemsAyudaComponent
        title="Lo que falta definir"
        subtitle="Propuestas y decisiones pendientes: aprobación, roles y usuarios, entre otras"
        items={PENDIENTES}
      />
    ),
  },
  { id: 'equipo', titulo: 'Equipo', contenido: <EquipoAyudaComponent /> },
];

export const AyudaComponent = () => (
  <div>
    <TituloPaginaComponent
      title="Centro de Ayuda y Documentación"
      description="Cómo funciona el sistema de Historias de Usuario. Para dudas puntuales, use el chat de ayuda (botón naranja, abajo a la derecha)."
    />
    <SeccionesConPestanasComponent etiqueta="Secciones de la ayuda" inicial="asistente" secciones={SECCIONES} />
  </div>
);
