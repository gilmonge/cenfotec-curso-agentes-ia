import React from 'react';
import { InsigniaEstadoComponent } from '../Comun/InsigniaEstadoComponent';
import { CampoTextoComponent } from '../Comun/CampoTextoComponent';
import { HelpCircle } from 'lucide-react';
import { ayudaCategoria, rotuloCategoria } from '../../data/rotulosPregunta';

export const TarjetaPreguntaComponent = ({ question, index, onAnswerChange }) => {
  return (
    <div className="card" style={{ marginBottom: '1rem', backgroundColor: question.status === 'respondida' ? 'var(--color-bg)' : 'var(--color-surface)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <HelpCircle size={18} style={{ color: 'var(--color-secondary-text)' }} />
          <span style={{ fontSize: '0.875rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--color-secondary-text)', letterSpacing: '0.04em' }}>
            {rotuloCategoria(question.category) || 'Pregunta de Negocio'}
          </span>
        </div>
        <InsigniaEstadoComponent status={question.status} />
      </div>

      {ayudaCategoria(question.category) && (
        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', margin: '-0.4rem 0 0.6rem' }}>
          {ayudaCategoria(question.category)}
        </p>
      )}

      <p style={{ fontSize: '0.95rem', fontWeight: '600', color: 'var(--color-text-primary)', marginBottom: '1rem' }}>
        {index + 1}. {question.question}
      </p>

      <CampoTextoComponent
        placeholder="Escriba aquí la respuesta de Negocio…"
        value={question.answer || ''}
        onChange={(e) => onAnswerChange && onAnswerChange(question.id, e.target.value)}
        hint={question.status === 'respondida' ? 'Respuesta capturada' : 'Falta la respuesta de Negocio'}
      />
    </div>
  );
};
