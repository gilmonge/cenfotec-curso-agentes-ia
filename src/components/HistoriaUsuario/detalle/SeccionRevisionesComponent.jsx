import React from 'react';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';
import { resumenCriterio } from '../../../utils/criterios';
import { SIN_IDENTIFICAR } from '../../../utils/usuarioActual';

const EdicionesRegistradas = ({ ediciones }) => (
  <TarjetaComponent title="Ediciones registradas" subtitle="Correcciones hechas a esta HU sin cambiar su revisión">
    <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {[...ediciones].reverse().map((edicion, indice) => (
        <li key={indice} style={{ fontSize: '0.9rem' }}>
          <strong>{String(edicion.fecha).slice(0, 10)}</strong> · {edicion.autor || SIN_IDENTIFICAR} — {edicion.campos.join(', ')}
        </li>
      ))}
    </ul>
  </TarjetaComponent>
);

export const SeccionRevisionesComponent = ({ story }) => (
  <>
  {story.revisiones?.length > 0 && <TarjetaComponent title="Historial de revisiones" subtitle="Versiones anteriores de esta misma HU (la vigente es la que se muestra en Historia y Criterios)">
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {[...story.revisiones].reverse().map((rev) => (
        <details key={rev.revision} style={{ padding: '0.75rem 1rem', border: '1px solid var(--color-border)', borderRadius: '8px' }}>
          <summary style={{ cursor: 'pointer', fontWeight: 700 }}>
            Rev. {rev.revision} — {rev.motivo}{rev.approvedAt ? ` (aprobada ${String(rev.approvedAt).slice(0, 10)})` : ''}
          </summary>
          <p style={{ margin: '0.6rem 0 0.4rem', fontSize: '0.9rem' }}>
            <strong>Como</strong> {rev.userStory?.asA} <strong>quiero</strong> {rev.userStory?.iWant} <strong>para</strong> {rev.userStory?.soThat}
          </p>
          <ul style={{ paddingLeft: '1.25rem', fontSize: '0.875rem' }}>
            {(rev.acceptanceCriteria ?? []).map((criterio, indice) => (
              <li key={criterio.id ?? indice}>{resumenCriterio(criterio)}</li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  </TarjetaComponent>}
  {story.ediciones?.length > 0 && <EdicionesRegistradas ediciones={story.ediciones} />}
  </>
);
