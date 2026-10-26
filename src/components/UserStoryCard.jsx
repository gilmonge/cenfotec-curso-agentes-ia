import React from 'react';
import { Eye, Edit3, Calendar, Tag } from 'lucide-react';
import { StatusBadge } from './ui/StatusBadge';
import { Button } from './ui/Button';

export const UserStoryCard = ({ story, onView, onEdit }) => {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#64748b', fontFamily: 'monospace' }}>
            {story.id}
          </span>
          <StatusBadge status={story.status} />
        </div>

        <h3 style={{ fontSize: '1.05rem', fontWeight: '700', color: '#0f172a', marginBottom: '0.5rem', lineHeight: '1.3' }}>
          {story.title}
        </h3>

        {story.description && (
          <p style={{
            fontSize: '0.85rem',
            color: '#475569',
            marginBottom: '1rem',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}>
            {story.description}
          </p>
        )}

        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <Tag size={13} />
            <span>{story.type || 'General'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <Calendar size={13} />
            <span>{story.createdAt}</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', paddingTop: '1rem', borderTop: '1px solid #e2e8f0' }}>
        <Button
          variant="outline"
          size="sm"
          icon={Eye}
          onClick={() => onView(story.id)}
          style={{ flex: 1 }}
        >
          Ver
        </Button>
        <Button
          variant="secondary"
          size="sm"
          icon={Edit3}
          onClick={() => onEdit(story.id)}
          style={{ flex: 1 }}
        >
          Editar
        </Button>
      </div>
    </div>
  );
};
