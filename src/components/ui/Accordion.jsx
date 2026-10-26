import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export const AccordionItem = ({ title, badge, icon: Icon, defaultOpen = false, children }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={`accordion__item ${isOpen ? 'accordion__item--open' : ''}`}>
      <button
        type="button"
        className="accordion__header"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <div className="accordion__title-box">
          {Icon && <Icon size={20} style={{ color: '#2563eb' }} />}
          <span className="accordion__title">{title}</span>
          {badge && <span className="accordion__badge">{badge}</span>}
        </div>
        <div>
          {isOpen ? <ChevronUp size={20} style={{ color: '#64748b' }} /> : <ChevronDown size={20} style={{ color: '#64748b' }} />}
        </div>
      </button>

      {isOpen && <div className="accordion__body">{children}</div>}
    </div>
  );
};

export const Accordion = ({ children }) => {
  return <div className="accordion">{children}</div>;
};
