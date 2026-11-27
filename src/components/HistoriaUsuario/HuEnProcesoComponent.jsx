import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlayCircle, Trash2 } from 'lucide-react';
import { BotonComponent } from '../Comun/BotonComponent';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { deleteWorkflow, listWorkflows } from '../../services/workflowApi';
import { useConfirmacion } from '../Comun/ConfirmacionComponent';
import { useSesion } from '../Sesion/SesionContext';
import { ACCION } from '../../config/acciones';

// Qué espera cada flujo guardado, en lenguaje de la persona usuaria.
const ROTULO_ESPERA = {
  business_answers: 'Esperando respuestas de Negocio',
  po_approval: 'Esperando aprobación del Product Owner',
  product_owner_approval: 'Esperando aprobación del Product Owner',
  change_decision: 'Esperando decisión sobre la solicitud de cambio',
};

const ROTULO_ESTADO = {
  error: 'Se detuvo por un error: puede reintentarlo',
  en_ejecucion: 'Los agentes estaban trabajando',
  fallido: 'Se detuvo sin terminar',
};

const ESTADO_TERMINADO = new Set(['completado', 'cancelado']);

export const describirFlujo = (flujo) => (
  (flujo.espera && ROTULO_ESPERA[flujo.espera]) || ROTULO_ESTADO[flujo.estado] || 'En proceso'
);

const fecha = (valor) => {
  const instante = valor ? new Date(valor) : null;
  return instante && !Number.isNaN(instante.getTime()) ? instante.toLocaleString('es-CR') : '';
};

// HU que todavía no terminan: se pueden retomar en el paso donde quedaron, aunque haya pasado un día.
export const HuEnProcesoComponent = () => {
  const navigate = useNavigate();
  const { puede } = useSesion();
  const [listaFlujo, setListaFlujo] = useState([]);
  const [error, setError] = useState('');
  const confirmar = useConfirmacion();

  useEffect(() => {
    const controller = new AbortController();
    listWorkflows({ signal: controller.signal })
      .then((lista) => setListaFlujo((lista ?? []).filter((flujo) => !ESTADO_TERMINADO.has(flujo.estado) && flujo.modo === 'pre_grooming')))
      .catch((cause) => {
        if (cause?.name === 'AbortError') return;
        // La lista es complementaria: si el servicio no responde, la página sigue sin ella.
        console.warn('No se pudo cargar la lista de HU en proceso:', cause?.message ?? cause);
      });
    return () => controller.abort();
  }, []);

  const descartar = async (flujo) => {
    const acepta = await confirmar({
      titulo: 'Descartar historia en proceso',
      mensaje: `¿Descartar «${flujo.titulo}»?\nSe pierde el avance guardado y no se puede recuperar.`,
      textoConfirmar: 'Descartar',
      textoCancelar: 'Conservar',
      peligro: true,
    });
    if (!acepta) return;
    try {
      await deleteWorkflow(flujo.workflow_id);
      setListaFlujo((actual) => actual.filter((item) => item.workflow_id !== flujo.workflow_id));
    } catch (cause) {
      console.warn('No se pudo descartar la HU en proceso:', cause?.message ?? cause);
      setError('No se pudo descartar la HU en proceso. Intente de nuevo.');
    }
  };

  if (!listaFlujo.length && !error) return null;

  return (
    <section className="card" style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem' }} aria-label="HU en proceso">
      <h3 style={{ marginBottom: '0.25rem' }}>En proceso</h3>
      <p style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', marginBottom: '0.75rem' }}>
        Historias que todavía no terminan. Retómelas en el paso donde quedaron.
      </p>
      {error && <AlertaComponent type="warning" title="HU en proceso">{error}</AlertaComponent>}
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {listaFlujo.map((flujo) => (
          <li
            key={flujo.workflow_id}
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', padding: '0.6rem 0', borderTop: '1px solid var(--color-border)' }}
          >
            <div>
              <strong>{flujo.titulo}</strong>
              <div style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                {describirFlujo(flujo)}
                {flujo.creado_por ? ` · Iniciada por ${flujo.creado_por}` : ''}
                {fecha(flujo.actualizado_en) ? ` · Último cambio: ${fecha(flujo.actualizado_en)}` : ''}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <BotonComponent variant="primary" icon={PlayCircle} onClick={() => navigate(`/historias/nueva?flujo=${encodeURIComponent(flujo.workflow_id)}`)}>
                Retomar
              </BotonComponent>
              {puede(ACCION.HISTORIA_DESCARTAR_EN_PROCESO) && (
                <BotonComponent variant="secondary" icon={Trash2} onClick={() => descartar(flujo)}>
                  Descartar
                </BotonComponent>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
};
