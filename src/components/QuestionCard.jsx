import React from 'react';
import { StatusBadge } from './ui/StatusBadge';
import { Input } from './ui/Input';
import { HelpCircle } from 'lucide-react';

export const QuestionCard = ({ question, index, onAnswerChange }) => {
  return (
    <div className="card" style={{ marginBottom: '1rem', backgroundColor: question.status === 'respondida' ? '#f8fafc' : '#ffffff' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <HelpCircle size={18} style={{ color: '#4f46e5' }} />
          <span style={{ fontSize: '0.8rem', fontWeight: '700', textTransform: 'uppercase', color: '#4f46e5', letterSpacing: '0.04em' }}>
            {question.category || 'Pregunta de Negocio'}
          </span>
        </div>
        <StatusBadge status={question.status} />
      </div>

      <p style={{ fontSize: '0.95rem', fontWeight: '600', color: '#0f172a', marginBottom: '1rem' }}>
        {index + 1}. {question.question}
      </p>

      <Input
        placeholder="Escriba la respuesta de negocio..."
        value={question.answer || ''}
        onChange={(e) => onAnswerChange && onAnswerChange(question.id, e.target.value)}
        hint={question.status === 'respondida' ? 'Respuesta capturada' : 'Respuesta pendiente por aclaración de Negocio'}
      />
    </div>
  );
};
