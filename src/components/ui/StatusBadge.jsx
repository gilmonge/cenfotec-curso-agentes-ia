import React from 'react';

const STATUS_MAP = {
  borrador: { label: 'Borrador', classSuffix: 'borrador' },
  en_analisis: { label: 'En análisis', classSuffix: 'en_analisis' },
  pendiente_de_informacion: { label: 'Pendiente de información', classSuffix: 'pendiente_de_informacion' },
  pendiente: { label: 'Pendiente', classSuffix: 'pendiente' },
  generada: { label: 'Generada', classSuffix: 'generada' },
  revisada: { label: 'Revisada', classSuffix: 'revisada' },
  respondida: { label: 'Respondida', classSuffix: 'respondida' }
};

export const StatusBadge = ({ status }) => {
  const current = STATUS_MAP[status] || { label: status, classSuffix: 'borrador' };
  return (
    <span className={`badge badge--${current.classSuffix}`}>
      • {current.label}
    </span>
  );
};

export const Badge = ({ children, variant = 'borrador', className = '' }) => {
  return (
    <span className={`badge badge--${variant} ${className}`}>
      {children}
    </span>
  );
};
