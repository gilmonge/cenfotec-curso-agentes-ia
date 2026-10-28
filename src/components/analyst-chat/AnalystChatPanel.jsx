import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ArrowDown, Loader2, Plus, Send, Square, Trash2, X } from 'lucide-react';
import { AnalystMarkdown } from './AnalystMarkdown.jsx';
import { AnalystDeleteDialog } from './AnalystDeleteDialog.jsx';
import { quotaRecoveryMessage, quotaRemainingSeconds } from '../../utils/quotaRecovery.js';

const MESSAGE_LIMIT = 4000;

function codepointLength(value) {
  return Array.from(value).length;
}

function QuotaRecoveryNotice({ retryAt }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (quotaRemainingSeconds(retryAt, Date.now()) !== null
      && quotaRemainingSeconds(retryAt, Date.now()) > 0) {
      let timer = window.setInterval(() => {
        const current = Date.now();
        setNow(current);
        if (quotaRemainingSeconds(retryAt, current) === 0) {
          window.clearInterval(timer);
          timer = null;
        }
      }, 1000);
      return () => {
        if (timer !== null) window.clearInterval(timer);
      };
    }
    return undefined;
  }, [retryAt]);

  return <p role="status" aria-live="off">{quotaRecoveryMessage(retryAt, now)}</p>;
}

function AnalysisDetails({ response }) {
  if (!response) return null;
  const sections = [
    ['Conocida', response.analisis?.conocida],
    ['Faltante', response.analisis?.faltante],
    ['Supuesta', response.analisis?.supuesta],
    ['Ambigua', response.analisis?.ambigua],
  ];

  return (
    <>
      {response.analisis && (
        <details className="analyst-chat-message__details">
          <summary>Análisis del requerimiento</summary>
          {sections.map(([title, values]) => (
            <div key={title}>
              <strong>{title}</strong>
              {values?.length ? (
                <ul>{values.map((value, index) => <li key={`${title}-${index}`}>{value}</li>)}</ul>
              ) : <p>Sin elementos registrados.</p>}
            </div>
          ))}
        </details>
      )}
      {typeof response.listo_para_redactor === 'boolean' && (
        <p className={`analyst-chat-message__readiness analyst-chat-message__readiness--${response.listo_para_redactor ? 'ready' : 'pending'}`}>
          {response.listo_para_redactor ? 'Listo para el Redactor-Revisor' : 'Pendiente de aclaraciones'}
        </p>
      )}
      {response.preguntas?.length > 0 && (
        <details className="analyst-chat-message__details">
          <summary>Preguntas para Negocio ({response.preguntas.length})</summary>
          <ul>{response.preguntas.map((item) => (
            <li key={item.question_id}>
              <strong>{item.categoria}</strong> · {item.estado}: {item.pregunta}
            </li>
          ))}</ul>
        </details>
      )}
      {response.fuentes_consultadas?.length > 0 && (
        <ul className="analyst-chat-message__sources" aria-label="Fuentes consultadas">
          {response.fuentes_consultadas.map((source) => (
            <li key={source.nombre}>
              {source.nombre}: {source.resultados} resultados · {source.duracion_ms} ms
            </li>
          ))}
        </ul>
      )}
      {Number.isFinite(response.duracion_ms) && (
        <p className="analyst-chat-message__sources">Duración: {response.duracion_ms} ms</p>
      )}
      {response.limitaciones?.length > 0 && (
        <p className="analyst-chat-message__limitations">{response.limitaciones.join(' ')}</p>
      )}
    </>
  );
}

export function AnalystChatPanel({
  open,
  messages = [],
  onClose,
  scrollContainerRef,
  closeButtonRef,
  draft = '',
  onDraftChange,
  onSend,
  onRetry,
  isProcessing = false,
  onCancel,
  onReset,
  onDelete,
  onRefreshHealth,
  health,
  backendConnection,
  generationStatus = 'unverified',
  error,
}) {
  const localScrollRef = useRef(null);
  const composerRef = useRef(null);
  const deleteButtonRef = useRef(null);
  const deleteDialogWasOpen = useRef(false);
  const messagesRef = scrollContainerRef ?? localScrollRef;
  const stickToBottom = useRef(true);
  const [showJumpButton, setShowJumpButton] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const characters = codepointLength(draft);
  const healthStatus = typeof health === 'string' ? health : health?.status;
  const backendStatus = backendConnection || (health ? 'connected' : 'checking');
  const opencodeStatus = typeof health === 'object' ? health?.checks?.opencode?.status : null;
  const serviceUnavailable = backendStatus === 'disconnected'
    || !healthStatus
    || healthStatus === 'unavailable'
    || opencodeStatus === 'unavailable';
  const generationLabel = {
    unverified: 'Generación del modelo sin verificar',
    available: 'Generación confirmada en el último envío',
    'model-unavailable': 'Modelo no disponible',
    'quota-exhausted': 'Cuota agotada (429)',
    timeout: `Timeout de ${health?.timeout_seconds || 90} segundos`,
  }[generationStatus] || 'Generación del modelo sin verificar';

  useLayoutEffect(() => {
    const container = messagesRef.current;
    if (!container) return;
    if (stickToBottom.current) {
      container.scrollTop = container.scrollHeight;
      setShowJumpButton(false);
    } else {
      setShowJumpButton(true);
    }
  }, [messages.length, messagesRef]);

  useEffect(() => {
    if (deleteDialogOpen) {
      deleteDialogWasOpen.current = true;
    } else if (deleteDialogWasOpen.current) {
      deleteDialogWasOpen.current = false;
      deleteButtonRef.current?.focus();
    }
  }, [deleteDialogOpen]);

  const handleScroll = () => {
    const container = messagesRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.clientHeight - container.scrollTop;
    const shouldStick = distanceFromBottom <= 80;
    stickToBottom.current = shouldStick;
    setShowJumpButton(!shouldStick);
  };

  const jumpToLatest = () => {
    const container = messagesRef.current;
    if (!container) return;
    stickToBottom.current = true;
    container.scrollTop = container.scrollHeight;
    setShowJumpButton(false);
  };

  const submit = (event) => {
    event.preventDefault();
    if (!isProcessing && !serviceUnavailable && characters <= MESSAGE_LIMIT && draft.trim()) {
      void onSend?.(draft);
    }
  };

  const handleComposerKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      composerRef.current?.form?.requestSubmit();
    }
  };

  return (
    <section
      id="analyst-chat-panel"
      className="analyst-chat-panel"
      role="dialog"
      aria-labelledby="analyst-chat-title"
      aria-modal="false"
      aria-hidden={!open}
      hidden={!open}
      tabIndex={-1}
    >
      <header className="analyst-chat-panel__header">
        <div>
          <p className="analyst-chat-panel__eyebrow">StoryCraft AI</p>
          <h2 id="analyst-chat-title">Agente Analista</h2>
          <p className={`analyst-chat-panel__health analyst-chat-panel__health--${backendStatus}`} role="status">
            {backendStatus === 'connected' ? 'Backend conectado' : backendStatus === 'disconnected' ? 'Backend desconectado' : 'Comprobando backend…'}
          </p>
          <p className={`analyst-chat-panel__health analyst-chat-panel__health--${opencodeStatus === 'ok' ? 'connected' : opencodeStatus === 'unavailable' ? 'unavailable' : 'checking'}`}>
            {opencodeStatus === 'ok' ? 'OpenCode Server conectado' : opencodeStatus === 'unavailable' ? 'OpenCode Server desconectado' : 'OpenCode Server sin verificar'}
          </p>
          <p className={`analyst-chat-panel__health analyst-chat-panel__health--${generationStatus}`}>
            {generationLabel}
          </p>
        </div>
        <div className="analyst-chat-panel__header-actions">
          <button className="analyst-chat-panel__icon-button" type="button" onClick={onReset} aria-label="Nuevo chat" title="Nuevo chat">
            <Plus aria-hidden="true" size={19} />
          </button>
          <button ref={deleteButtonRef} className="analyst-chat-panel__icon-button" type="button" onClick={() => setDeleteDialogOpen(true)} aria-label="Eliminar conversación" title="Eliminar conversación">
            <Trash2 aria-hidden="true" size={18} />
          </button>
          <button
            ref={closeButtonRef}
            className="analyst-chat-panel__icon-button"
            type="button"
            onClick={onClose}
            aria-label="Cerrar chat"
          >
            <X aria-hidden="true" size={20} />
          </button>
        </div>
      </header>

      <div className="analyst-chat-panel__body">
        <div
          ref={messagesRef}
          className="analyst-chat-panel__messages"
          role="log"
          aria-label="Mensajes del chat"
          aria-live="polite"
          aria-relevant="additions text"
          onScroll={handleScroll}
          data-testid="analyst-chat-messages"
        >
          {messages.length === 0 && (
            <p className="analyst-chat-panel__empty">Cuéntame qué necesidad o proceso quieres analizar.</p>
          )}
          {messages.map((message) => (
            <article
              className={`analyst-chat-message analyst-chat-message--${message.role}`}
              key={message.id}
              data-message-id={message.id}
            >
              <p className="analyst-chat-message__author">
                {message.role === 'user' ? 'Tú' : 'Agente Analista'}
              </p>
              <div className="analyst-chat-message__text">
                {message.role === 'assistant' ? (
                  <AnalystMarkdown content={message.text || ''} />
                ) : message.text}
              </div>
              {message.status === 'failed' && (
                <div className="analyst-chat-message__failure">
                  {message.errorCode === 'OPENCODE_RATE_LIMITED'
                    ? <QuotaRecoveryNotice retryAt={message.retryAt} />
                    : <p role="status">No se obtuvo respuesta: {message.error}</p>}
                  <button type="button" onClick={() => onRetry?.(message.id)} disabled={isProcessing || backendStatus === 'disconnected'}>
                    Reintentar este mensaje
                  </button>
                </div>
              )}
              {message.role === 'assistant' && <AnalysisDetails response={message.response} />}
            </article>
          ))}
          {isProcessing && (
            <p className="analyst-chat-panel__processing" role="status">
              <Loader2 aria-hidden="true" size={16} className="analyst-chat-panel__spinner" />
              Analizando con el agente…
            </p>
          )}
        </div>
        {showJumpButton && (
          <button className="analyst-chat-panel__jump" type="button" onClick={jumpToLatest}>
            <ArrowDown aria-hidden="true" size={16} />
            Ir al último mensaje
          </button>
        )}
      </div>

      <form className="analyst-chat-composer" onSubmit={submit}>
        {error && <p className="analyst-chat-composer__error" role="alert">{error}</p>}
        <label className="analyst-chat-composer__label" htmlFor="analyst-chat-input">Mensaje</label>
        <textarea
          ref={composerRef}
          id="analyst-chat-input"
          aria-label="Escribe tu requerimiento"
          value={draft}
          onChange={(event) => onDraftChange?.(event.target.value)}
          onKeyDown={handleComposerKeyDown}
          placeholder="Describe la necesidad o proceso…"
          rows={3}
          maxLength={8000}
          disabled={isProcessing || serviceUnavailable}
        />
        <div className="analyst-chat-composer__footer">
          <span className={characters > MESSAGE_LIMIT ? 'is-over-limit' : ''} aria-live="polite">
            {characters}/{MESSAGE_LIMIT}
          </span>
          {isProcessing ? (
            <button className="analyst-chat-composer__button analyst-chat-composer__button--cancel" type="button" onClick={onCancel}>
              <Square aria-hidden="true" size={15} /> Cancelar
            </button>
          ) : (
            <button className="analyst-chat-composer__button" type="submit" disabled={serviceUnavailable || !draft.trim() || characters > MESSAGE_LIMIT}>
              <Send aria-hidden="true" size={16} /> Enviar
            </button>
          )}
        </div>
        {serviceUnavailable && (
          <div className="analyst-chat-composer__hint">
            <span>{backendStatus === 'disconnected' ? 'No se puede conectar con FastAPI.' : opencodeStatus === 'unavailable' ? 'OpenCode Server no está conectado.' : 'El servicio del agente no está listo.'} Comprueba su estado antes de enviar.</span>
            <button type="button" onClick={onRefreshHealth}>Reintentar conexión</button>
          </div>
        )}
      </form>
      {deleteDialogOpen && (
        <AnalystDeleteDialog
          onCancel={() => setDeleteDialogOpen(false)}
          onConfirm={() => {
            setDeleteDialogOpen(false);
            void onDelete?.();
          }}
        />
      )}
    </section>
  );
}
