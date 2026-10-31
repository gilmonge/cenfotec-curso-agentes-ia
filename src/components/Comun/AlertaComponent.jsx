import React from 'react';
import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';

export const AlertaComponent = ({ type = 'info', title, children, className = '' }) => {
  const icons = {
    info: Info,
    success: CheckCircle,
    warning: AlertTriangle,
    danger: AlertCircle
  };
  
  const IconComponent = icons[type] || Info;

  return (
    <div className={`alert alert--${type} ${className}`}>
      <IconComponent size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
      <div>
        {title && <strong style={{ display: 'block', marginBottom: '0.2rem' }}>{title}</strong>}
        {children}
      </div>
    </div>
  );
};
