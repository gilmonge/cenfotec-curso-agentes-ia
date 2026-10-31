import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { AreaTextoComponent } from '../Comun/AreaTextoComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { criterioNuevo } from '../../utils/criterios';

// Editor único de criterios de aceptación: cada criterio tiene Dado que, Cuando y Entonces.
export const EditorCriteriosComponent = ({ valor, alCambiar, prefijoId = 'criterio', error = '' }) => {
  const cambiarCampo = (indice, campo, texto) => {
    alCambiar(valor.map((criterio, i) => (i === indice ? { ...criterio, [campo]: texto } : criterio)));
  };
  const quitar = (indice) => alCambiar(valor.filter((_, i) => i !== indice));

  return (
    <div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {valor.map((criterio, indice) => (
          <div
            key={criterio.id || indice}
            style={{ padding: '0.85rem 1rem', backgroundColor: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: '8px' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <p style={{ fontWeight: 700, color: 'var(--color-text-secondary)' }}>Criterio {indice + 1}</p>
              <BotonComponent
                variant="outline"
                size="sm"
                icon={Trash2}
                aria-label={`Quitar criterio ${indice + 1}`}
                onClick={() => quitar(indice)}
              >
                Quitar
              </BotonComponent>
            </div>
            <AreaTextoComponent
              label="Dado que"
              id={`${prefijoId}-${indice}-given`}
              rows={2}
              value={criterio.given}
              onChange={(e) => cambiarCampo(indice, 'given', e.target.value)}
            />
            <AreaTextoComponent
              label="Cuando"
              id={`${prefijoId}-${indice}-when`}
              rows={2}
              value={criterio.when}
              onChange={(e) => cambiarCampo(indice, 'when', e.target.value)}
            />
            <AreaTextoComponent
              label="Entonces"
              id={`${prefijoId}-${indice}-then`}
              rows={2}
              value={criterio.then}
              onChange={(e) => cambiarCampo(indice, 'then', e.target.value)}
            />
          </div>
        ))}
      </div>
      {error && <p className="form-hint" role="alert" style={{ color: 'var(--color-danger-text)', marginTop: '0.5rem' }}>{error}</p>}
      <div style={{ marginTop: '0.75rem' }}>
        <BotonComponent variant="secondary" size="sm" icon={Plus} onClick={() => alCambiar([...valor, criterioNuevo()])}>
          Agregar criterio
        </BotonComponent>
      </div>
    </div>
  );
};
