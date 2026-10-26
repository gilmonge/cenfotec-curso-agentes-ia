import React from 'react';

export const PageTitle = ({ title, description, action }) => {
  return (
    <div className="page-title">
      <div className="page-title__header">
        <div>
          <h1 className="page-title__heading">{title}</h1>
          {description && <p className="page-title__description">{description}</p>}
        </div>
        {action && <div>{action}</div>}
      </div>
    </div>
  );
};
