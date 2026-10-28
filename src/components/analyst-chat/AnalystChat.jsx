import React, { useEffect, useRef } from 'react';
import { AnalystChatLauncher } from './AnalystChatLauncher.jsx';
import { AnalystChatPanel } from './AnalystChatPanel.jsx';
import { useAnalystChat } from '../../hooks/useAnalystChat.js';

export function AnalystChat() {
  const chat = useAnalystChat();
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
      <AnalystChatPanel
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
      <AnalystChatLauncher
        ref={launcherRef}
        isOpen={chat.isOpen}
        onClick={chat.isOpen ? closeChat : chat.openChat}
      />
    </div>
  );
}
