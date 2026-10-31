import React from 'react';
import { BotonComponent } from '../Comun/BotonComponent';

export const TarjetaMetricaComponent = ({ icon: Icon, value, label, buttonText, onButtonClick, variant = 'primary' }) => {
  return (
    <div className="metric-card">
      <div>
        <div className="metric-card__header">
          <div className="metric-card__icon-box">
            {Icon && <Icon size={24} />}
          </div>
        </div>
        <div className="metric-card__value">{value}</div>
        <div className="metric-card__label">{label}</div>
      </div>
      {buttonText && onButtonClick && (
        <div className="metric-card__footer">
          <BotonComponent variant={variant} onClick={onButtonClick} style={{ width: '100%' }}>
            {buttonText}
          </BotonComponent>
        </div>
      )}
    </div>
  );
};
