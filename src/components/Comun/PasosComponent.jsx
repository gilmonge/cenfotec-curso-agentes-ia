import React from 'react';
import { Check } from 'lucide-react';

export const PasosComponent = ({ steps = [], activeStep = 1, onStepClick }) => {
  return (
    <div
      className="stepper"
      data-paso={activeStep}
      data-total={steps.length}
      data-etiqueta={steps[activeStep - 1]?.label || ''}
    >
      {steps.map((step, index) => {
        const stepNum = index + 1;
        const isActive = activeStep === stepNum;
        const isCompleted = activeStep > stepNum;

        let itemClass = 'stepper__item';
        if (isActive) itemClass += ' stepper__item--active';
        if (isCompleted) itemClass += ' stepper__item--completed';

        return (
          <React.Fragment key={step.id || stepNum}>
            <div
              className={itemClass}
              onClick={() => isCompleted && onStepClick && onStepClick(stepNum)}
              title={isCompleted ? `Ir al paso ${stepNum}` : ''}
              style={{ cursor: isCompleted ? 'pointer' : 'default' }}
            >
              <div className="stepper__number">
                {isCompleted ? <Check size={16} /> : stepNum}
              </div>
              <span className="stepper__label">{step.label}</span>
            </div>

            {index < steps.length - 1 && (
              <div
                className={`stepper__divider ${
                  activeStep > stepNum ? 'stepper__divider--active' : ''
                }`}
              />
            )}
          </React.Fragment>
        );
      })}

    </div>
  );
};
