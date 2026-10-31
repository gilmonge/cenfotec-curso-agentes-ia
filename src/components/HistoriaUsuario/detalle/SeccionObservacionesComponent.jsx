import React from 'react';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { leerBitacora } from '../../../utils/bitacora';
import { SIN_IDENTIFICAR } from '../../../utils/usuarioActual';

// Bitácora de seguimiento: cada nota con su fecha y autor. En Word y PDF salen solo los textos.
export const SeccionObservacionesComponent = ({ story }) => (
  <TarjetaComponent title="Observaciones y aclaraciones" subtitle="Bitácora de notas para tener en cuenta en el grooming">
    <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {leerBitacora(story).map((nota, indice) => (
        <li key={indice} style={{ borderLeft: '3px solid var(--color-border)', paddingLeft: '0.75rem' }}>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
            {nota.fecha || 'Sin fecha'} · {nota.autor || SIN_IDENTIFICAR}
          </p>
          <p style={{ fontSize: '0.95rem', color: 'var(--color-text-secondary)', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>{nota.texto}</p>
        </li>
      ))}
    </ul>
  </TarjetaComponent>
);
