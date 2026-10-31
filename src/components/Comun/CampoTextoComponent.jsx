import React from 'react';

export const CampoTextoComponent = React.forwardRef(({
  label,
  id,
  required = false,
  hint,
  error,
  className = '',
  ...props
}, ref) => {
  return (
    <div className="form-group">
      {label && (
        <label htmlFor={id}>
          {label}
          {required && <span className="required">*</span>}
        </label>
      )}
      <input id={id} ref={ref} className={`input ${className}`} {...props} />
      {hint && <p className="form-hint">{hint}</p>}
      {error && <p className="form-hint" style={{ color: 'var(--color-danger-text)' }}>{error}</p>}
    </div>
  );
});
CampoTextoComponent.displayName = 'Input';
