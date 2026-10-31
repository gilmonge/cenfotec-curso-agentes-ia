import React from 'react';
import { ShieldAlert, Activity, CheckCircle2, BookOpen, ArrowRight, FileCode } from 'lucide-react';

export const TarjetaHabilidadComponent = ({ skill, onOpen }) => {
  const isResilience = skill.categoryTag === 'resilience';

  return (
    <div className="skill-card" onClick={() => onOpen(skill)}>
      <div className="skill-card__header">
        <div className={`skill-card__icon-box skill-card__icon-box--${skill.categoryTag}`}>
          {isResilience ? <ShieldAlert size={22} /> : <Activity size={22} />}
        </div>
        <span className={`skill-card__badge skill-card__badge--${skill.categoryTag}`}>
          {skill.category}
        </span>
      </div>

      <div className="skill-card__body">
        <h3 className="skill-card__title">{skill.title}</h3>
        <code className="skill-card__code-name">
          <FileCode size={13} /> {skill.name}
        </code>
        <p className="skill-card__description">{skill.description}</p>
      </div>

      <div className="skill-card__stats">
        <div className="skill-card__stat">
          <CheckCircle2 size={14} className="skill-card__stat-icon" />
          <span>{skill.checklistSections.length} Secciones de Criterios</span>
        </div>
        <div className="skill-card__stat">
          <BookOpen size={14} className="skill-card__stat-icon" />
          <span>{skill.references.length} Referencias</span>
        </div>
      </div>

      <div className="skill-card__footer">
        <button
          type="button"
          className="btn btn--secondary btn--sm skill-card__btn"
          onClick={(e) => {
            e.stopPropagation();
            onOpen(skill);
          }}
        >
          <span>Ver Criterios y Referencias</span>
          <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
};
