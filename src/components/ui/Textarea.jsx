import React from 'react';

export const Textarea = ({
  label,
  id,
  required = false,
  hint,
  error,
  rows = 4,
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
      <textarea id={id} rows={rows} className={`textarea ${className}`} {...props} />
      {hint && <p className="form-hint">{hint}</p>}
      {error && <p className="form-hint" style={{ color: '#ef4444' }}>{error}</p>}
    </div>
  );
};
