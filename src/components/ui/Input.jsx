import React from 'react';

export const Input = ({
  label,
  id,
  required = false,
  hint,
  error,
  className = '',
  ...props
}) => {
  return (
    <div className="form-group">
      {label && (
        <label htmlFor={id}>
          {label}
          {required && <span className="required">*</span>}
        </label>
      )}
      <input id={id} className={`input ${className}`} {...props} />
      {hint && <p className="form-hint">{hint}</p>}
      {error && <p className="form-hint" style={{ color: '#ef4444' }}>{error}</p>}
    </div>
  );
};
