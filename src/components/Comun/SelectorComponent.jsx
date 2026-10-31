import React from 'react';

export const SelectorComponent = ({
  label,
  id,
  required = false,
  options = [],
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
      <select id={id} className={`select ${className}`} {...props}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {hint && <p className="form-hint">{hint}</p>}
      {error && <p className="form-hint" style={{ color: 'var(--color-danger-text)' }}>{error}</p>}
    </div>
  );
};
