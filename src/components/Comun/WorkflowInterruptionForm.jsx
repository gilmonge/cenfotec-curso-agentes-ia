import React, { useEffect, useState } from 'react';
import { AlertaComponent } from './AlertaComponent';
import { BotonComponent } from './BotonComponent';
import { puedeResponder, registroInterrupcion, textoDe } from '../../flujo/interrupciones';
import { useSesion } from '../Sesion/SesionContext';
import { sesionApi } from '../../services/seguridadApi';
import { useConfirmacion } from './ConfirmacionComponent';

// Formulario genérico de intervención humana. Qué campos muestra y qué respuesta arma lo decide el
// registro de interrupciones (src/flujo/interrupciones.jsx) según el tipo que manda el backend.
export const WorkflowInterruptionForm = ({
  interrupt, onResume, busy = false, error = '', canSubmit = true, borrador = {}, onSaveDraft,
}) => {
  // Las respuestas escritas en otra sesión y guardadas sin enviar empiezan cargadas.
  const [valor, setValor] = useState(() => ({ answers: { ...borrador }, decision: '', reason: '', lessonDecisions: {} }));
  const [draftNotice, setDraftNotice] = useState('');
  const [validationError, setValidationError] = useState('');
  const confirmar = useConfirmacion();
  const { puede, seguridad } = useSesion();
  const tipo = interrupt ? registroInterrupcion[interrupt.kind] : null;
  const permitido = !tipo || puedeResponder(tipo, puede);
  const [listaAprobador, setListaAprobador] = useState([]);

  // Sin permiso para decidir: se indica quién puede hacerlo (por ejemplo, los Product Owner).
  useEffect(() => {
    if (!seguridad || permitido || interrupt?.kind !== 'po_approval') return;
    sesionApi.listarAprobador().then(setListaAprobador).catch((fallo) => {
      console.error('No se pudo consultar quién puede aprobar:', fallo);
    });
  }, [seguridad, permitido, interrupt?.kind]);

  if (!interrupt) return null;
  if (!tipo) {
    return <AlertaComponent type="danger" title="Intervención no reconocida">El flujo pidió una intervención que esta versión no sabe mostrar.</AlertaComponent>;
  }
  if (!permitido) {
    const nombres = listaAprobador.map((persona) => persona.nombre).join(', ');
    return (
      <AlertaComponent type="info" title="Esta decisión le corresponde a otra persona">
        {interrupt.kind === 'po_approval'
          ? `La historia quedó pendiente de aprobación${nombres ? ` por: ${nombres}` : ' de un Product Owner'}. La verán en Historias de Usuario → En proceso.`
          : 'Su rol no tiene la acción necesaria para responder este paso. Pida a un administrador que se la asigne en Mantenimiento.'}
      </AlertaComponent>
    );
  }

  const cambiar = (parcial) => {
    setValidationError('');
    setDraftNotice('');
    setValor((actual) => ({ ...actual, ...parcial }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    const resultado = tipo.construir(interrupt, valor);
    if (resultado.error) {
      setValidationError(resultado.error);
      return;
    }
    if (resultado.confirmar && !(await confirmar({
      titulo: 'Confirmar decisión',
      mensaje: resultado.confirmar,
      textoConfirmar: 'Confirmar',
      peligro: ['rechazar', 'detener'].includes(resultado.response?.decision),
    }))) return;
    setValidationError('');
    await onResume({ kind: interrupt.kind, interrupt_id: interrupt.interrupt_id, response: resultado.response });
  };

  const titulo = textoDe(tipo.titulo, interrupt);
  const descripcion = textoDe(tipo.descripcion, interrupt);
  const { Campos } = tipo;
  const hayPregunta = (interrupt.payload?.questions ?? []).length > 0;

  return (
    <form onSubmit={submit} className="workflow-human-form" aria-label="Intervención humana requerida">
      {titulo && <h3>{titulo}</h3>}
      {descripcion && <p>{descripcion}</p>}
      <Campos interrupt={interrupt} valor={valor} cambiar={cambiar} puede={puede} />

      {validationError && <AlertaComponent type="warning" title="Revise la respuesta">{validationError}</AlertaComponent>}
      {draftNotice && <AlertaComponent type="success" title="Respuestas guardadas">{draftNotice}</AlertaComponent>}
      {error && <AlertaComponent type="danger" title="No se pudo continuar">{error}</AlertaComponent>}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <BotonComponent type="submit" variant="primary" disabled={busy || !interrupt.kind || !canSubmit}>
          {busy ? 'Enviando…' : 'Confirmar y continuar'}
        </BotonComponent>
        {onSaveDraft && tipo.borrador && hayPregunta && (
          <BotonComponent
            type="button"
            variant="secondary"
            disabled={busy}
            onClick={async () => {
              const guardado = await onSaveDraft(valor.answers);
              if (guardado) setDraftNotice('Puede salir y retomarlas después desde Historias de Usuario → En proceso.');
            }}
          >
            Guardar sin enviar
          </BotonComponent>
        )}
      </div>
    </form>
  );
};
