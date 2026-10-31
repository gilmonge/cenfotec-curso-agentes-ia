import React from 'react';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';

export const SeccionPlantillaComponent = ({ story }) => (
  <TarjetaComponent title="Datos de la plantilla" subtitle={story.number || 'Sin número asignado'}>
    <p style={{ fontSize: '0.95rem', color: 'var(--color-text-secondary)' }}>
      Sistema: {story.system || '—'} · Código de HU: {story.codigoHu || story.area || '—'} · Solicitante: {story.requester || '—'}
    </p>
    {story.benefits?.length > 0 && (
      <ul style={{ paddingLeft: '1.25rem', marginTop: '0.5rem' }}>
        {story.benefits.map((beneficio, indice) => <li key={indice}>{beneficio}</li>)}
      </ul>
    )}
  </TarjetaComponent>
);
