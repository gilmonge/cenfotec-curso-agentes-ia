import React, { useEffect, useRef, useState } from 'react';
import { HelpCircle, Send, X } from 'lucide-react';
import {
  BIENVENIDA_AYUDA,
  PREGUNTAS_AYUDA,
  SUGERENCIA_INICIAL,
  TEXTO_SIN_COINCIDENCIA,
  buscarPregunta,
} from '../../data/ayudaChat';

const preguntaPorId = (id) => PREGUNTAS_AYUDA.find((item) => item.id === id);

export const AsistenteAyudaComponent = () => {
  const [abierto, setAbierto] = useState(false);
  const [mensaje, setMensaje] = useState([]);
  const [consulta, setConsulta] = useState('');
  const finRef = useRef(null);
  const consecutivo = useRef(0);

  useEffect(() => {
    if (abierto && finRef.current?.scrollIntoView) finRef.current.scrollIntoView({ block: 'end' });
  }, [mensaje, abierto]);

  const agregar = (...nuevo) =>
    setMensaje((actual) => [...actual, ...nuevo.map((item) => ({ ...item, key: consecutivo.current++ }))]);

  const preguntar = (item) => {
    agregar({ rol: 'persona', texto: item.pregunta }, { rol: 'ayuda', respuesta: item });
  };

  const enviar = (evento) => {
    evento.preventDefault();
    const texto = consulta.trim();
    if (!texto) return;
    setConsulta('');
    const item = buscarPregunta(texto);
    if (item) agregar({ rol: 'persona', texto }, { rol: 'ayuda', respuesta: item });
    else agregar({ rol: 'persona', texto }, { rol: 'ayuda', texto: TEXTO_SIN_COINCIDENCIA });
  };

  const ultimo = mensaje[mensaje.length - 1];
  const sugerencia = ultimo?.respuesta
    ? PREGUNTAS_AYUDA.filter((item) => item.id !== ultimo.respuesta.id).slice(0, 4)
    : SUGERENCIA_INICIAL.map(preguntaPorId);

  return (
    <div className="help-chat">
      <section
        id="help-chat-panel"
        className="help-chat-panel"
        role="dialog"
        aria-label="Chat de ayuda"
        hidden={!abierto}
      >
        <header className="help-chat-panel__header">
          <h2>Ayuda</h2>
          <button type="button" className="help-chat-panel__close" onClick={() => setAbierto(false)} aria-label="Cerrar chat de ayuda">
            <X size={18} aria-hidden="true" />
          </button>
        </header>

        <div className="help-chat-panel__messages" role="log" aria-live="polite">
          <p className="help-chat-message help-chat-message--ayuda">{BIENVENIDA_AYUDA}</p>
          {mensaje.map((item) => (
            <div key={item.key} className={`help-chat-message help-chat-message--${item.rol}`}>
              {item.rol === 'persona' && item.texto}
              {item.rol === 'ayuda' && item.texto}
              {item.rol === 'ayuda' && item.respuesta && (
                <>
                  <p>{item.respuesta.texto}</p>
                  {item.respuesta.pasos && (
                    <ol>
                      {item.respuesta.pasos.map((paso) => (
                        <li key={paso}>{paso}</li>
                      ))}
                    </ol>
                  )}
                </>
              )}
            </div>
          ))}
          <div ref={finRef} />
        </div>

        <div className="help-chat-panel__suggestions" aria-label="Preguntas sugeridas">
          {sugerencia.map((item) => (
            <button key={item.id} type="button" onClick={() => preguntar(item)}>
              {item.pregunta}
            </button>
          ))}
        </div>

        <form className="help-chat-panel__form" onSubmit={enviar}>
          <input
            type="text"
            value={consulta}
            onChange={(evento) => setConsulta(evento.target.value)}
            aria-label="Escriba una palabra clave"
            placeholder="Escriba una palabra clave…"
            maxLength={120}
          />
          <button type="submit" aria-label="Enviar" disabled={!consulta.trim()}>
            <Send size={18} aria-hidden="true" />
          </button>
        </form>
      </section>

      <button
        type="button"
        className="help-chat-launcher"
        onClick={() => setAbierto((valor) => !valor)}
        aria-expanded={abierto}
        aria-controls="help-chat-panel"
        aria-label={abierto ? 'Cerrar chat de ayuda' : 'Abrir chat de ayuda'}
        title="Ayuda"
      >
        <HelpCircle size={22} aria-hidden="true" />
        <span>¿Cómo se usa?</span>
      </button>
    </div>
  );
};
