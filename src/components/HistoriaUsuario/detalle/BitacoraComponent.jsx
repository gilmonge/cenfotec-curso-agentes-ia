import React from 'react';
import { InsigniaComponent } from '../../Comun/InsigniaEstadoComponent';
import { ESTADO_NOTA, TIPO_NOTA, leerBitacora, tieneEstado, tipoDeNota } from '../../../utils/bitacora';
import { SIN_IDENTIFICAR } from '../../../utils/usuarioActual';

const VARIANTE_TIPO = {
  decision: 'revisada',
  dependencia: 'pendiente',
  pendiente_tecnico: 'en_analisis',
  supuesto: 'pendiente_de_informacion',
  devolucion: 'respondida',
  nota: 'borrador',
};

const VARIANTE_ESTADO = { abierto: 'pendiente', atendido: 'aprobada' };

// Una fila por entrada: tipo y estado como etiquetas, fecha y origen arriba, el comentario debajo.
// Con onCambiarEstado, las dependencias y los pendientes técnicos se pueden marcar como atendidos.
export const BitacoraComponent = ({ story, onCambiarEstado }) => (
  <ul className="bitacora">
    {leerBitacora(story).map((nota, indice) => {
      const tipo = tipoDeNota(nota);
      const estado = nota.estado === 'atendido' ? 'atendido' : 'abierto';
      return (
        <li key={indice} className="bitacora__entrada">
          <div className="bitacora__cabecera">
            <InsigniaComponent variant={VARIANTE_TIPO[tipo]}>{TIPO_NOTA[tipo]}</InsigniaComponent>
            {tieneEstado(nota) && (
              <InsigniaComponent variant={VARIANTE_ESTADO[estado]}>{ESTADO_NOTA[estado]}</InsigniaComponent>
            )}
            <span className="bitacora__meta">{nota.fecha || 'Sin fecha'} · {nota.autor || SIN_IDENTIFICAR}</span>
            {tieneEstado(nota) && onCambiarEstado && (
              <button
                type="button"
                className="bitacora__accion"
                onClick={() => onCambiarEstado(indice, estado === 'atendido' ? 'abierto' : 'atendido')}
              >
                {estado === 'atendido' ? 'Reabrir' : 'Marcar como atendido'}
              </button>
            )}
          </div>
          <p className="bitacora__texto">{nota.texto}</p>
        </li>
      );
    })}
  </ul>
);
