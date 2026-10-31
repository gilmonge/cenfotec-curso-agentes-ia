import React from 'react';
import { CheckCircle2, AlertCircle, HelpCircle, FileQuestion } from 'lucide-react';

export const TarjetaAnalisisComponent = ({ analysis }) => {
  const {
    knownData = [],
    missingData = [],
    assumptions = [],
    ambiguities = []
  } = analysis || {};

  const categories = [
    {
      title: 'Datos Conocidos',
      count: knownData.length,
      items: knownData,
      type: 'known',
      icon: CheckCircle2,
      color: 'var(--color-success-text)',
      badgeClass: 'counter-badge--known'
    },
    {
      title: 'Información Faltante',
      count: missingData.length,
      items: missingData,
      type: 'missing',
      icon: AlertCircle,
      color: 'var(--color-danger-text)',
      badgeClass: 'counter-badge--missing'
    },
    {
      title: 'Supuestos',
      count: assumptions.length,
      items: assumptions,
      type: 'assumptions',
      icon: HelpCircle,
      color: 'var(--color-warning-text)',
      badgeClass: 'counter-badge--assumptions'
    },
    {
      title: 'Ambigüedades',
      count: ambiguities.length,
      items: ambiguities,
      type: 'ambiguities',
      icon: FileQuestion,
      color: 'var(--color-secondary-text)',
      badgeClass: 'counter-badge--ambiguities'
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top summary counter badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.5rem' }}>
        {categories.map((cat) => (
          <span key={cat.title} className={`counter-badge ${cat.badgeClass}`}>
            <cat.icon size={15} />
            {cat.count} {cat.title.toLowerCase()}
          </span>
        ))}
      </div>

      <div className="grid-2">
        {categories.map((cat) => (
          <div className="card" key={cat.title} style={{ height: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', borderBottom: '1px solid var(--color-surface-hover)', paddingBottom: '0.75rem' }}>
              <cat.icon size={20} style={{ color: cat.color }} />
              <h4 style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--color-text-primary)' }}>{cat.title}</h4>
              <span className={`counter-badge ${cat.badgeClass}`} style={{ marginLeft: 'auto', padding: '0.15rem 0.5rem', fontSize: '0.875rem' }}>
                {cat.count}
              </span>
            </div>

            {cat.items.length === 0 ? (
              <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                No se detectaron elementos.
              </p>
            ) : (
              <ul style={{ paddingLeft: '1.2rem', margin: 0 }}>
                {cat.items.map((item, idx) => (
                  <li key={idx} style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem', lineHeight: '1.4' }}>
                    {item}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
