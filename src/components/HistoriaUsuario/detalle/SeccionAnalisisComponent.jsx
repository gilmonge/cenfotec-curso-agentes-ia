import React from 'react';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { TarjetaAnalisisComponent } from '../TarjetaAnalisisComponent';

export const SeccionAnalisisComponent = ({ story }) => (
  <TarjetaComponent title="Análisis del Requerimiento Original" subtitle="Diagnóstico de datos y supuestos">
    <TarjetaAnalisisComponent analysis={story.analysis} />
  </TarjetaComponent>
);
