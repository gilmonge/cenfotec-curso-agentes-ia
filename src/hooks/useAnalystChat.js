import { useCallback, useEffect, useRef, useState } from 'react';
import { analystApi } from '../services/analystApi.js';
import { analystErrorMessage } from '../utils/analystErrors.js';
import { validateAnalystResponse } from '../utils/analystResponse.js';

const MAX_MESSAGE_CODEPOINTS = 4000;

function createRequestId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = Math.random() * 16 | 0;
    return (char === 'x' ? random : (random & 3) | 8).toString(16);
  });
}

function generationStateForError(cause) {
  if (cause?.code === 'OPENCODE_RATE_LIMITED') return 'quota-exhausted';
  if (cause?.code === 'MODEL_UNAVAILABLE') return 'model-unavailable';
  if (cause?.code === 'TURN_TIMEOUT') return 'timeout';
  return null;
}

export function useAnalystChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);
  const [backendConnection, setBackendConnection] = useState('checking');
  const [generationStatus, setGenerationStatus] = useState('unverified');
  const requestLock = useRef(false);
  const requestEpoch = useRef(0);
  const activeRequest = useRef(null);

  const refreshHealth = useCallback(async (signal) => {
    try {
      const next = await analystApi.getHealth({ signal });
      setHealth(next);
      setBackendConnection('connected');
      return next;
    } catch (cause) {
      if (cause?.name !== 'AbortError') {
        setHealth(null);
        setBackendConnection('disconnected');
      }
      return null;
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refreshHealth(controller.signal);
    return () => controller.abort();
  }, [refreshHealth]);

  useEffect(() => {
    const cancelOnPageHide = () => {
      const active = activeRequest.current;
      if (active?.conversationId) {
        requestEpoch.current += 1;
        void analystApi.cancelTurn(active.conversationId, active.requestId, { keepalive: true }).catch(() => {});
        active.controller?.abort();
      }
    };
    window.addEventListener('pagehide', cancelOnPageHide);
    return () => {
      window.removeEventListener('pagehide', cancelOnPageHide);
      const active = activeRequest.current;
      if (active?.conversationId) {
        requestEpoch.current += 1;
        void analystApi.cancelTurn(active.conversationId, active.requestId, { keepalive: true }).catch(() => {});
        active.controller?.abort();
      }
    };
  }, []);

  const openChat = useCallback(() => setIsOpen(true), []);
  const closeChat = useCallback(() => setIsOpen(false), []);

  const runTurn = useCallback(async ({ message, messageId, requestId }) => {
    if (requestLock.current) return false;
    requestLock.current = true;
    setIsProcessing(true);
    setError(null);
    setMessages((current) => current.map((item) => item.id === messageId
      ? { ...item, status: 'processing', error: null, retryAt: null, retryRequestId: null }
      : item));

    let currentConversationId = conversationId;
    const controller = new AbortController();
    const epoch = ++requestEpoch.current;
    const turnTimeoutMs = Math.max(1, Number(health?.timeout_seconds) || 90) * 1000;
    const timeoutMessage = `El análisis tardó demasiado y superó el límite de ${Math.round(turnTimeoutMs / 1000)} segundos. Puedes reintentarlo.`;
    const isCurrentRequest = () => requestEpoch.current === epoch
      && activeRequest.current?.requestId === requestId
      && activeRequest.current?.epoch === epoch;
    activeRequest.current = { requestId, epoch, conversationId: currentConversationId, message, messageId, controller };
    const timeoutHandle = window.setTimeout(() => {
      if (!isCurrentRequest()) return;
      const active = activeRequest.current;
      requestEpoch.current += 1;
      activeRequest.current = null;
      requestLock.current = false;
      controller.abort();
      setIsProcessing(false);
      const timeoutError = { code: 'TURN_TIMEOUT' };
      const messageError = timeoutMessage;
      setError(messageError);
      setGenerationStatus('timeout');
      setMessages((current) => current.map((item) => item.id === messageId
        ? { ...item, status: 'failed', error: messageError, errorCode: timeoutError.code, retryRequestId: null }
        : item));
      if (active?.conversationId) {
        void analystApi.cancelTurn(active.conversationId, requestId, { keepalive: true }).catch(() => {});
      }
    }, turnTimeoutMs);

    try {
      if (!currentConversationId) {
        const created = await analystApi.createConversation({ signal: controller.signal });
        currentConversationId = created.conversation_id;
        if (!isCurrentRequest()) {
          void analystApi.deleteConversation(currentConversationId).catch(() => {});
          return false;
        }
        setConversationId(currentConversationId);
      }
      activeRequest.current = { requestId, epoch, conversationId: currentConversationId, message, messageId, controller };
      const rawResult = await analystApi.sendMessage(
        currentConversationId,
        { request_id: requestId, message },
        { signal: controller.signal },
      );
      if (!isCurrentRequest()) return false;
      const result = validateAnalystResponse(rawResult);
      setMessages((current) => [
        ...current.map((item) => item.id === messageId
          ? { ...item, status: 'completed', error: null, errorCode: null, retryAt: null, retryRequestId: null }
          : item),
        {
          id: result.turn_id || createRequestId(),
          role: 'assistant',
          response: result,
          text: result.respuesta_markdown,
        },
      ]);
      setGenerationStatus('available');
      void refreshHealth();
      return true;
    } catch (cause) {
      if (!isCurrentRequest()) return false;
      const messageError = cause?.code === 'TURN_TIMEOUT' ? timeoutMessage : analystErrorMessage(cause);
      setError(cause?.code === 'OPENCODE_RATE_LIMITED' ? null : messageError);
      const generationError = generationStateForError(cause);
      if (generationError) setGenerationStatus(generationError);
      const retryRequestId = ['NETWORK_ERROR', 'TURN_IN_PROGRESS'].includes(cause?.code) ? requestId : null;
      setMessages((current) => current.map((item) => item.id === messageId
        ? {
          ...item,
          status: 'failed',
          error: messageError,
          errorCode: cause?.code,
          retryAt: cause?.code === 'OPENCODE_RATE_LIMITED' ? cause.retryAt : null,
          retryRequestId,
        }
        : item));
      if (cause?.code !== 'TURN_CANCELLED' && cause?.code !== 'TURN_INVALIDATED') {
        void refreshHealth();
      }
      return false;
    } finally {
      window.clearTimeout(timeoutHandle);
      if (isCurrentRequest()) {
        activeRequest.current = null;
        requestLock.current = false;
        setIsProcessing(false);
      }
    }
  }, [conversationId, health, refreshHealth]);

  const sendMessage = useCallback(async (value) => {
    const message = String(value ?? '').trim();
    const size = Array.from(message).length;
    if (!message || size > MAX_MESSAGE_CODEPOINTS || requestLock.current) return false;
    if (!health || health.status === 'unavailable' || backendConnection !== 'connected') {
      setError(backendConnection === 'disconnected'
        ? analystErrorMessage({ code: 'NETWORK_ERROR' })
        : 'El servicio del agente no está listo. Revisa sus estados e inténtalo de nuevo.');
      return false;
    }

    const messageId = createRequestId();
    const requestId = createRequestId();
    setDraft('');
    setMessages((current) => [...current, {
      id: messageId,
      role: 'user',
      text: message,
      status: 'processing',
      error: null,
      errorCode: null,
      retryAt: null,
      retryRequestId: null,
    }]);
    return runTurn({ message, messageId, requestId });
  }, [backendConnection, health, runTurn]);

  const retryMessage = useCallback(async (messageId) => {
    if (requestLock.current) return false;
    const failedMessage = messages.find((item) => item.id === messageId && item.role === 'user' && item.status === 'failed');
    if (!failedMessage) return false;
    setDraft('');
    setError(null);
    // Keep the ID for uncertain network requests and conflict responses that did
    // not enter the backend idempotency cache; confirmed API errors are
    // terminal in the backend idempotency cache, so a user retry needs a fresh ID.
    const requestId = failedMessage.retryRequestId || createRequestId();
    return runTurn({ message: failedMessage.text, messageId, requestId });
  }, [messages, runTurn]);

  const cancelTurn = useCallback(async () => {
    const active = activeRequest.current;
    if (!active) return false;
    if (!active.conversationId) {
      requestEpoch.current += 1;
      activeRequest.current = null;
      requestLock.current = false;
      setMessages((current) => current.map((item) => item.id === active.messageId
        ? { ...item, status: 'cancelled' }
        : item));
      setDraft(active.message);
      setIsProcessing(false);
      return true;
    }
    try {
      const result = await analystApi.cancelTurn(active.conversationId, active.requestId);
      if (result.canceled) {
        requestEpoch.current += 1;
        activeRequest.current = null;
        active.controller?.abort();
        requestLock.current = false;
        setMessages((current) => current.map((item) => item.id === active.messageId
          ? { ...item, status: 'cancelled' }
          : item));
        setDraft(active.message);
        setIsProcessing(false);
        setError(null);
      }
      return result.canceled;
    } catch (cause) {
      setError(analystErrorMessage(cause));
      return false;
    }
  }, []);

  const resetConversation = useCallback(async () => {
    const active = activeRequest.current;
    const resetEpoch = ++requestEpoch.current;
    const previousConversationId = conversationId;
    setError(null);
    activeRequest.current = null;
    requestLock.current = false;
    setIsProcessing(false);
    setMessages([]);
    setDraft('');
    setConversationId(null);
    if (!previousConversationId) {
      active?.controller?.abort();
      return true;
    }
    try {
      const replacement = await analystApi.resetConversation(previousConversationId);
      if (active?.conversationId) active.controller?.abort();
      if (requestEpoch.current !== resetEpoch) {
        if (replacement.conversation_id) void analystApi.deleteConversation(replacement.conversation_id).catch(() => {});
        return true;
      }
      setConversationId(replacement.conversation_id);
      return true;
    } catch (cause) {
      active?.controller?.abort();
      if (requestEpoch.current === resetEpoch) setError(analystErrorMessage(cause));
      return false;
    }
  }, [conversationId]);

  const deleteConversation = useCallback(async () => {
    const active = activeRequest.current;
    requestEpoch.current += 1;
    activeRequest.current = null;
    requestLock.current = false;
    setIsProcessing(false);
    try {
      if (conversationId) await analystApi.deleteConversation(conversationId);
      active?.controller?.abort();
      setConversationId(null);
      setMessages([]);
      setDraft('');
      setError(null);
      setIsOpen(false);
      return true;
    } catch (cause) {
      setError(analystErrorMessage(cause));
      return false;
    }
  }, [conversationId]);

  return {
    isOpen,
    setIsOpen,
    openChat,
    closeChat,
    messages,
    setMessages,
    draft,
    setDraft,
    conversationId,
    setConversationId,
    isProcessing,
    setIsProcessing,
    error,
    setError,
    requestLock,
    health,
    backendConnection,
    generationStatus,
    refreshHealth,
    sendMessage,
    retryMessage,
    cancelTurn,
    resetConversation,
    deleteConversation,
  };
}
