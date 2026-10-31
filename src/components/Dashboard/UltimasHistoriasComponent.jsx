import React from 'react';
import { BotonComponent } from '../Comun/BotonComponent';
import { InsigniaEstadoComponent } from '../Comun/InsigniaEstadoComponent';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import { etiquetaHistoria } from '../../utils/plantillaHu';
import { etiquetaRevision, numeroRevision } from '../../utils/revisiones';
import { SIN_IDENTIFICAR } from '../../utils/usuarioActual';

const CANTIDAD = 5;

const fechaDe = (story) => String(story.updatedAt ?? story.createdAt ?? '');

// Las más recientes primero, según su última actualización.
export const ultimasHistorias = (stories, cantidad = CANTIDAD) => (
  [...stories].sort((a, b) => fechaDe(b).localeCompare(fechaDe(a))).slice(0, cantidad)
);

export const UltimasHistoriasComponent = ({ stories, onVer, onVerTodas }) => {
  const lista = ultimasHistorias(stories);
  return (
    <TarjetaComponent
      title="Últimas historias"
      action={<BotonComponent variant="secondary" size="sm" onClick={onVerTodas}>Ver listado completo de historias</BotonComponent>}
    >
      {lista.length === 0 && (
        <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>Todavía no hay historias. Use Crear para empezar con la primera.</p>
      )}
      <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column' }}>
        {lista.map((story) => (
          <li
            key={story.id}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', padding: '0.75rem 0', borderTop: '1px solid var(--color-border)' }}
          >
            <div style={{ minWidth: 0 }}>
              <p style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>{etiquetaHistoria(story)} — {story.title}</p>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                <InsigniaEstadoComponent status={story.status} />
                {numeroRevision(story) > 1 && <span>{etiquetaRevision(story)}</span>}
                <span>{story.updatedBy || story.createdBy || SIN_IDENTIFICAR} · {fechaDe(story)}</span>
              </p>
            </div>
            <BotonComponent variant="secondary" size="sm" onClick={() => onVer(story.id)}>Ver</BotonComponent>
          </li>
        ))}
      </ul>
    </TarjetaComponent>
  );
};
