// Bitácora de seguimiento de una HU: una entrada por idea, con fecha, tipo, origen y comentario.
// Las entradas no se editan ni se borran; las dependencias y los pendientes técnicos tienen estado
// (abierto / atendido) para marcarlos en el grooming. Las correcciones se hacen con una nota nueva.
import { normalizarNombre } from './usuarioActual';

const hoy = () => new Date().toISOString().slice(0, 10);

export const TIPO_NOTA = Object.freeze({
  decision: 'Decisión',
  dependencia: 'Dependencia',
  pendiente_tecnico: 'Pendiente técnico',
  supuesto: 'Supuesto por validar',
  devolucion: 'Devolución del PO',
  nota: 'Nota',
});

export const ESTADO_NOTA = Object.freeze({ abierto: 'Abierto', atendido: 'Atendido' });

// Solo lo que pide una acción tiene estado.
const TIPO_CON_ESTADO = new Set(['dependencia', 'pendiente_tecnico']);

export const ORIGEN = Object.freeze({ analista: 'Analista', redactor: 'Redactor-Revisor', negocio: 'Negocio' });

export const tipoDeNota = (nota) => (TIPO_NOTA[nota?.tipo] ? nota.tipo : 'nota');
export const tieneEstado = (nota) => TIPO_CON_ESTADO.has(tipoDeNota(nota));

// Las HU guardadas antes de la bitácora tenían un único texto en "observations": se leen como la nota inicial.
export function leerBitacora(historia = {}) {
  if (Array.isArray(historia.bitacora)) return historia.bitacora;
  const texto = String(historia.observations ?? '').trim();
  if (!texto) return [];
  return [{ fecha: historia.createdAt ?? '', autor: normalizarNombre(historia.createdBy), tipo: 'nota', texto }];
}

// Devuelve la bitácora de la HU con la nota nueva al final (si hay texto).
export function bitacoraConNota(historia, texto, { fecha = hoy(), autor = '' } = {}) {
  const nota = String(texto ?? '').trim();
  const previas = leerBitacora(historia ?? {});
  return nota ? [...previas, { fecha, autor, tipo: 'nota', texto: nota }] : previas;
}

// Cambia solo el estado de una dependencia o de un pendiente técnico; el resto de la entrada no se toca.
export function bitacoraConEstado(historia, indice, estado) {
  return leerBitacora(historia).map((nota, posicion) => (
    posicion === indice && tieneEstado(nota) && ESTADO_NOTA[estado] ? { ...nota, estado } : nota
  ));
}

const limpio = (texto) => String(texto ?? '').trim();

// Entradas que deja el flujo multiagente al aprobar la HU. Las observaciones de control de calidad
// del Redactor-Revisor no entran: sirvieron para revisar la historia, no para implementarla.
export function bitacoraDelFlujo(resultado = {}, { fecha = hoy(), persona = '', notaAprobacion = '' } = {}) {
  const lista = [];
  (resultado.impact_decisions ?? []).forEach((item) => {
    if (limpio(item.respuesta)) {
      // Las decisiones del Asesor las responde Negocio, en la misma ronda que las preguntas del Analista.
      lista.push({ fecha, autor: ORIGEN.negocio, tipo: 'decision', texto: `${limpio(item.pregunta)}\nDecisión: ${limpio(item.respuesta)}` });
    }
  });
  (resultado.analyst?.supuesto_validar_po ?? []).forEach((texto) => {
    if (limpio(texto)) lista.push({ fecha, autor: ORIGEN.analista, tipo: 'supuesto', texto: limpio(texto) });
  });
  (resultado.notas_hu ?? []).forEach((nota) => {
    if (limpio(nota.texto) && TIPO_CON_ESTADO.has(nota.tipo)) {
      lista.push({ fecha, autor: ORIGEN.redactor, tipo: nota.tipo, texto: limpio(nota.texto), estado: 'abierto' });
    }
  });
  (resultado.devoluciones_po ?? []).forEach((devolucion) => {
    const atencion = limpio(devolucion.atencion);
    lista.push({
      fecha: devolucion.fecha || fecha,
      autor: persona,
      tipo: 'devolucion',
      texto: `Motivo: ${limpio(devolucion.motivo)}${atencion ? `\nCómo se atendió: ${atencion}` : ''}`,
    });
  });
  if (limpio(notaAprobacion)) lista.push({ fecha, autor: persona, tipo: 'nota', texto: limpio(notaAprobacion) });
  return lista;
}

// Para los documentos: una fila por entrada (Fecha | Tipo | Origen | Comentario | Estado).
export const filasBitacora = (historia) => leerBitacora(historia).map((nota) => ({
  fecha: nota.fecha || '',
  tipo: TIPO_NOTA[tipoDeNota(nota)],
  origen: nota.autor || '',
  comentario: nota.texto,
  estado: tieneEstado(nota) ? ESTADO_NOTA[nota.estado] ?? ESTADO_NOTA.abierto : '',
}));

export const textosBitacora = (historia) => leerBitacora(historia).map((nota) => nota.texto);
