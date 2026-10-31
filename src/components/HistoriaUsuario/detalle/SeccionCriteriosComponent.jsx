import React, { useState } from 'react';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { AlertaComponent } from '../../Comun/AlertaComponent';
import { ETIQUETA_CRITERIO, quitarEtiqueta } from '../../../utils/plantillaHu';
import { resumenCriterio } from '../../../utils/criterios';

const VISTAS = [
  { id: 'list', texto: 'Lista' },
  { id: 'given_when_then', texto: 'Dado/Cuando/Entonces' },
];

const botonVista = (activo) => ({
  padding: '0.25rem 0.6rem',
  fontSize: '0.875rem',
  fontWeight: '600',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  backgroundColor: activo ? 'var(--color-surface)' : 'transparent',
  color: activo ? 'var(--color-secondary-text)' : 'var(--color-text-muted)',
});

export const SeccionCriteriosComponent = ({ story }) => {
  const [vista, setVista] = useState('list');
  const criterios = story.acceptanceCriteria ?? [];
  return (
    <TarjetaComponent
      title={`Criterios de Aceptación (${criterios.length})`}
      subtitle="Condiciones de satisfacción verificables"
      action={
        <div style={{ display: 'flex', gap: '0.25rem', backgroundColor: 'var(--color-surface-hover)', padding: '0.2rem', borderRadius: '6px' }}>
          {VISTAS.map(({ id, texto }) => (
            <button key={id} type="button" onClick={() => setVista(id)} style={botonVista(vista === id)}>{texto}</button>
          ))}
        </div>
      }
    >
      {story.criteriosModificados && story.status !== 'aprobada' && (
        <AlertaComponent type="info" title="Criterios modificados">
          Los criterios se modificaron después de la última revisión. El análisis del requerimiento sigue vigente: solo se vuelve a analizar si cambian el requerimiento o las respuestas.
        </AlertaComponent>
      )}
      {criterios.length === 0 && <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>Sin criterios de aceptación asignados.</p>}
      {criterios.length > 0 && vista === 'list' && (
        <ol style={{ paddingLeft: '1.25rem' }}>
          {criterios.map((ac, idx) => (
            <li key={idx} style={{ marginBottom: '0.6rem', fontSize: '0.95rem', color: 'var(--color-text-secondary)' }}>{resumenCriterio(ac)}</li>
          ))}
        </ol>
      )}
      {criterios.length > 0 && vista === 'given_when_then' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {criterios.map((ac, idx) => (
            <div key={idx} style={{ padding: '0.85rem 1rem', backgroundColor: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: '8px', fontSize: '0.875rem' }}>
              <p style={{ fontWeight: '700', color: 'var(--color-text-secondary)', marginBottom: '0.3rem' }}>Criterio {idx + 1}</p>
              {ac.given && <p style={{ color: 'var(--color-secondary-text)', marginBottom: '0.15rem' }}><strong>DADO QUE:</strong> {quitarEtiqueta(ac.given, ETIQUETA_CRITERIO.given)}</p>}
              {ac.when && <p style={{ color: 'var(--color-secondary-text)', marginBottom: '0.15rem' }}><strong>CUANDO:</strong> {quitarEtiqueta(ac.when, ETIQUETA_CRITERIO.when)}</p>}
              {ac.then && <p style={{ color: 'var(--color-success-text)' }}><strong>ENTONCES:</strong> {quitarEtiqueta(ac.then, ETIQUETA_CRITERIO.then)}</p>}
            </div>
          ))}
        </div>
      )}
    </TarjetaComponent>
  );
};
