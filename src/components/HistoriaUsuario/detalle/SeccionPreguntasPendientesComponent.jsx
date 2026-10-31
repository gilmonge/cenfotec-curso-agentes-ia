import React from 'react';
import { HelpCircle } from 'lucide-react';
import { BotonComponent } from '../../Comun/BotonComponent';

export const SeccionPreguntasPendientesComponent = ({ story, onResponder }) => (
  <div style={{ backgroundColor: 'var(--color-warning-light)', border: '1px solid var(--color-warning-border)', borderRadius: '10px', padding: '1.25rem' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-warning-text)', fontWeight: '700', marginBottom: '0.5rem' }}>
      <HelpCircle size={18} />
      <span>Preguntas Pendientes de Negocio ({story.pendingQuestions.length})</span>
    </div>
    <ul style={{ paddingLeft: '1.25rem', color: 'var(--color-warning-text)', fontSize: '0.9rem' }}>
      {story.pendingQuestions.map((pregunta, idx) => (
        <li key={idx} style={{ marginBottom: '0.35rem' }}>{pregunta}</li>
      ))}
    </ul>
    {story.status !== 'aprobada' && (
      <div style={{ marginTop: '0.75rem' }}>
        <BotonComponent variant="primary" size="sm" icon={HelpCircle} onClick={onResponder}>Responder preguntas</BotonComponent>
      </div>
    )}
  </div>
);
