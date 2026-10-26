import React from 'react';
import { FolderOpen } from 'lucide-react';
import { Button } from './Button';

export const EmptyState = ({
  icon: Icon = FolderOpen,
  title = 'No hay datos',
  description = 'No se encontraron elementos para mostrar.',
  actionText,
  onAction
}) => {
  return (
    <div className="empty-state">
      <div className="empty-state__icon">
        <Icon size={28} />
      </div>
      <h3 className="empty-state__title">{title}</h3>
      <p className="empty-state__desc">{description}</p>
      {actionText && onAction && (
        <Button onClick={onAction} variant="primary">
          {actionText}
        </Button>
      )}
    </div>
  );
};
