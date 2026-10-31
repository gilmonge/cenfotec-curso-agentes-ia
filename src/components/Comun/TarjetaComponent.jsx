import React from 'react';

export const TarjetaComponent = ({ children, className = '', header, title, subtitle, action }) => {
  return (
    <div className={`card ${className}`}>
      {(header || title || action) && (
        <div className="card--header">
          <div>
            {title && <h3 className="card__title">{title}</h3>}
            {subtitle && <p className="card__subtitle">{subtitle}</p>}
            {header}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
};
