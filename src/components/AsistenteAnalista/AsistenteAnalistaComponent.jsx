import React, { useEffect, useRef } from 'react';
import { LanzadorAsistenteComponent } from './LanzadorAsistenteComponent';
import { PanelAsistenteComponent } from './PanelAsistenteComponent';
import { useAsistenteAnalista } from '../../hooks/useAsistenteAnalista.js';

export function AsistenteAnalistaComponent() {
  const chat = useAsistenteAnalista();
  const launcherRef = useRef(null);
  const closeButtonRef = useRef(null);

  useEffect(() => {
    if (chat.isOpen) {
      closeButtonRef.current?.focus();
    }
  }, [chat.isOpen]);

  useEffect(() => {
    if (!chat.isOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        chat.closeChat();
        launcherRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [chat.isOpen, chat.closeChat]);

  const closeChat = () => {
    chat.closeChat();
    launcherRef.current?.focus();
  };

  return (
    <div className="analyst-chat">
      <PanelAsistenteComponent
        open={chat.isOpen}
        messages={chat.messages}
        onClose={closeChat}
        closeButtonRef={closeButtonRef}
        draft={chat.draft}
        onDraftChange={chat.setDraft}
        onSend={chat.sendMessage}
        onRetry={chat.retryMessage}
        isProcessing={chat.isProcessing}
        onCancel={chat.cancelTurn}
        onReset={chat.resetConversation}
        onDelete={chat.deleteConversation}
        onRefreshHealth={() => chat.refreshHealth()}
        health={chat.health}
        backendConnection={chat.backendConnection}
        generationStatus={chat.generationStatus}
        error={chat.error}
      />
      <LanzadorAsistenteComponent
        ref={launcherRef}
        isOpen={chat.isOpen}
        onClick={chat.isOpen ? closeChat : chat.openChat}
      />
    </div>
  );
}
