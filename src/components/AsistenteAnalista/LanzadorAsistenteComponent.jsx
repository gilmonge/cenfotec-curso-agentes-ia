import React from 'react';
import { MessageCircle } from 'lucide-react';

export const LanzadorAsistenteComponent = React.forwardRef(function LanzadorAsistente(
  { onClick, isOpen },
  ref,
) {
  return (
    <button
      ref={ref}
      className="analyst-chat-launcher"
      type="button"
      onClick={onClick}
      aria-label={isOpen ? 'Chat del Agente Analista abierto' : 'Abrir chat del Agente Analista'}
      aria-expanded={isOpen}
      aria-controls="analyst-chat-panel"
      title="Agente Analista"
    >
      <MessageCircle aria-hidden="true" size={22} />
      <span>Analista</span>
    </button>
  );
});
