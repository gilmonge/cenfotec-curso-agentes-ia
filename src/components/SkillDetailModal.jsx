import React, { useEffect, useState } from 'react';
import {
  X,
  ShieldAlert,
  Activity,
  CheckCircle2,
  BookOpen,
  FileText,
  AlertCircle,
  ExternalLink,
  CheckSquare,
  HelpCircle,
  Tag
} from 'lucide-react';

export const SkillDetailModal = ({ skill, onClose }) => {
  const [activeTab, setActiveTab] = useState('criteria'); // 'criteria' | 'overview' | 'references'
  const [checkedItems, setCheckedItems] = useState({});

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [onClose]);

  if (!skill) return null;

  const isResilience = skill.categoryTag === 'resilience';

  const toggleCheck = (sectionIdx, itemIdx) => {
    const key = `${sectionIdx}-${itemIdx}`;
    setCheckedItems((prev) => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const totalItemsCount = skill.checklistSections.reduce(
    (acc, sec) => acc + sec.items.length,
    0
  );
  const checkedCount = Object.values(checkedItems).filter(Boolean).length;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-content skill-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="skill-modal-title"
      >
        <div className="skill-modal__header">
          <div className="skill-modal__header-info">
            <div className={`skill-card__icon-box skill-card__icon-box--${skill.categoryTag}`}>
              {isResilience ? <ShieldAlert size={24} /> : <Activity size={24} />}
            </div>
            <div>
              <div className="skill-modal__tags">
                <span className={`skill-card__badge skill-card__badge--${skill.categoryTag}`}>
                  {skill.category}
                </span>
                <span className="skill-modal__path-badge">
                  <Tag size={12} /> {skill.path}
                </span>
              </div>
              <h2 id="skill-modal-title" className="skill-modal__title">
                {skill.title}
              </h2>
            </div>
          </div>
          <button
            type="button"
            className="skill-modal__close-btn"
            onClick={onClose}
            aria-label="Cerrar modal"
          >
            <X size={20} />
          </button>
        </div>

        <div className="skill-modal__tabs">
          <button
            type="button"
            className={`skill-modal__tab ${activeTab === 'criteria' ? 'active' : ''}`}
            onClick={() => setActiveTab('criteria')}
          >
            <CheckSquare size={16} />
            <span>Criterios & Checklist ({totalItemsCount})</span>
          </button>
          <button
            type="button"
            className={`skill-modal__tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <FileText size={16} />
            <span>Propósito y Uso</span>
          </button>
          <button
            type="button"
            className={`skill-modal__tab ${activeTab === 'references' ? 'active' : ''}`}
            onClick={() => setActiveTab('references')}
          >
            <BookOpen size={16} />
            <span>Referencias ({skill.references.length})</span>
          </button>
        </div>

        <div className="skill-modal__body">
          {activeTab === 'criteria' && (
            <div className="skill-modal__section">
              <div className="skill-modal__progress-bar-container">
                <div className="skill-modal__progress-info">
                  <span className="skill-modal__progress-label">
                    Progreso de Verificación (Interactivo)
                  </span>
                  <span className="skill-modal__progress-val">
                    {checkedCount} de {totalItemsCount} criterios marcados
                  </span>
                </div>
                <div className="skill-modal__progress-track">
                  <div
                    className="skill-modal__progress-fill"
                    style={{
                      width: `${totalItemsCount > 0 ? (checkedCount / totalItemsCount) * 100 : 0}%`
                    }}
                  />
                </div>
              </div>

              {skill.checklistSections.map((sec, sIdx) => (
                <div key={sIdx} className="skill-checklist-group">
                  <h4 className="skill-checklist-group__title">
                    <CheckCircle2 size={16} className="skill-checklist-group__icon" />
                    {sec.title}
                  </h4>
                  <div className="skill-checklist-group__items">
                    {sec.items.map((item, iIdx) => {
                      const isChecked = !!checkedItems[`${sIdx}-${iIdx}`];
                      return (
                        <label
                          key={iIdx}
                          className={`skill-checklist-item ${isChecked ? 'skill-checklist-item--checked' : ''}`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleCheck(sIdx, iIdx)}
                            className="skill-checklist-item__checkbox"
                          />
                          <span className="skill-checklist-item__text">{item}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'overview' && (
            <div className="skill-modal__section">
              <div className="skill-overview-box">
                <h4 className="skill-overview-box__heading">
                  <FileText size={18} /> Descripción General
                </h4>
                <p className="skill-overview-box__text">{skill.description}</p>
              </div>

              <div className="skill-overview-box">
                <h4 className="skill-overview-box__heading">
                  <CheckCircle2 size={18} /> Propósito de la Skill
                </h4>
                <p className="skill-overview-box__text">{skill.purpose}</p>
              </div>

              <div className="grid-2" style={{ gap: '1rem', marginTop: '1rem' }}>
                <div className="skill-usage-card skill-usage-card--do">
                  <h5 className="skill-usage-card__title">
                    <CheckCircle2 size={16} /> Cuándo usar (When to Use)
                  </h5>
                  <ul className="skill-usage-card__list">
                    {skill.whenToUse.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div className="skill-usage-card skill-usage-card--dont">
                  <h5 className="skill-usage-card__title">
                    <AlertCircle size={16} /> Cuándo NO usar (When NOT to Use)
                  </h5>
                  <ul className="skill-usage-card__list">
                    {skill.whenNotToUse.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'references' && (
            <div className="skill-modal__section">
              <p className="skill-references__intro">
                Fuentes oficiales, documentación de referencia y mejores prácticas utilizadas por esta skill para evaluar el código:
              </p>
              <div className="skill-references__list">
                {skill.references.map((ref, idx) => (
                  <div key={idx} className="skill-reference-item">
                    <BookOpen size={18} className="skill-reference-item__icon" />
                    <span className="skill-reference-item__text">{ref}</span>
                    <ExternalLink size={14} className="skill-reference-item__link-icon" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="skill-modal__footer">
          <div className="skill-modal__footer-left">
            <span className="skill-modal__code-pill">
              Fichero de Origen: <code>{skill.name}/SKILL.md</code>
            </span>
          </div>
          <button type="button" className="btn btn--primary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
