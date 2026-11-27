import React from 'react';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { WorkflowInterruptionForm } from '../WorkflowInterruptionForm.jsx';
import { ConfirmacionProvider } from '../ConfirmacionComponent.jsx';

// El formulario confirma con el modal de la aplicación.
const conModal = (elemento) => <ConfirmacionProvider>{elemento}</ConfirmacionProvider>;
const responderModal = async (user, nombre) => {
  const dialogo = await screen.findByRole('alertdialog');
  await user.click(within(dialogo).getByRole('button', { name: nombre }));
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('WorkflowInterruptionForm', () => {
  it('answers only the pending Business questions and sends interrupt_id', async () => {
    const user = userEvent.setup();
    const onResume = vi.fn();
    render(<WorkflowInterruptionForm
      interrupt={{
        interrupt_id: 'business-42',
        kind: 'business_answers',
        payload: { questions: [{ question_id: 'q1', pregunta: '¿Qué vigencia?' }], max_answer_chars: 1000, max_total_chars: 3500 },
      }}
      onResume={onResume}
    />);

    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    expect(onResume).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText(/qué vigencia/i), '12 meses');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    expect(onResume).toHaveBeenCalledWith({
      kind: 'business_answers',
      interrupt_id: 'business-42',
      response: { answers: [{ question_id: 'q1', answer: '12 meses' }] },
    });
  });

  it('requires explicit PO approval confirmation and supports return with a reason', async () => {
    const user = userEvent.setup();
    const onResume = vi.fn();
    render(conModal(<WorkflowInterruptionForm interrupt={{ interrupt_id: 'po-1', kind: 'po_approval', payload: {} }} onResume={onResume} />));
    await user.selectOptions(screen.getByLabelText('Decisión'), 'devolver_redactor');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    expect(onResume).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText(/motivo de devolución/i), 'Aclarar resultado esperado');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    expect(within(screen.getByRole('alertdialog')).getByText(/Devolver a Redactor/)).toBeInTheDocument();
    await responderModal(user, 'Cancelar');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(onResume).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    await responderModal(user, /^Confirmar$/);
    expect(onResume).toHaveBeenCalledWith({
      kind: 'po_approval', interrupt_id: 'po-1',
      response: { decision: 'devolver_redactor', reason: 'Aclarar resultado esperado' },
    });
  });

  it('confirms change rejection and leaves proposed lessons undecided by default', async () => {
    const user = userEvent.setup();
    const onResume = vi.fn();
    render(conModal(<WorkflowInterruptionForm interrupt={{
      interrupt_id: 'change-1', kind: 'change_decision',
      payload: { change_recommendation: { lessons_proposed: [{ category: 'Validaciones', suggested_question: '¿Cuál es el límite?' }] } },
    }} onResume={onResume} />));
    await user.selectOptions(screen.getByLabelText('Decisión'), 'aplicar');
    expect(screen.getByLabelText('Decisión sobre la lección')).toHaveValue('');
    await user.selectOptions(screen.getByLabelText('Decisión'), 'rechazar');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    await responderModal(user, /^Confirmar$/);
    expect(onResume).toHaveBeenCalledWith({
      kind: 'change_decision', interrupt_id: 'change-1', response: { decision: 'rechazar' },
    });
  });

  it('requires confirmation before PO rejection and disables concurrent submission while busy', async () => {
    const user = userEvent.setup();
    const onResume = vi.fn();
    const { rerender } = render(conModal(<WorkflowInterruptionForm interrupt={{ interrupt_id: 'po-reject', kind: 'po_approval', payload: {} }} onResume={onResume} />));
    await user.selectOptions(screen.getByLabelText('Decisión'), 'rechazar');
    await user.click(screen.getByRole('button', { name: /Confirmar y continuar/i }));
    // Rechazar es una acción destructiva: el botón del modal es de peligro.
    expect(within(screen.getByRole('alertdialog')).getByRole('button', { name: /^Confirmar$/ })).toHaveClass('btn--danger');
    await responderModal(user, 'Cancelar');
    expect(onResume).not.toHaveBeenCalled();

    rerender(conModal(<WorkflowInterruptionForm interrupt={{ interrupt_id: 'po-reject', kind: 'po_approval', payload: {} }} onResume={onResume} busy />));
    expect(screen.getByRole('button', { name: /Enviando/i })).toBeDisabled();
  });
});
