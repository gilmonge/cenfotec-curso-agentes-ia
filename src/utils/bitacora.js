// Bitácora de seguimiento de una HU: notas con fecha y autor que se agregan sin borrar las anteriores.
// En los documentos (Word y PDF) salen solo los textos; la fecha y el autor quedan en el sistema.
import { normalizarNombre } from './usuarioActual';

const hoy = () => new Date().toISOString().slice(0, 10);

// Las HU guardadas antes de la bitácora tenían un único texto en "observations": se leen como la nota inicial.
export function leerBitacora(historia = {}) {
  if (Array.isArray(historia.bitacora)) return historia.bitacora;
  const texto = String(historia.observations ?? '').trim();
  if (!texto) return [];
  return [{ fecha: historia.createdAt ?? '', autor: normalizarNombre(historia.createdBy), texto }];
}

// Devuelve la bitácora de la HU con la nota nueva al final (si hay texto).
export function bitacoraConNota(historia, texto, { fecha = hoy(), autor = '' } = {}) {
  const nota = String(texto ?? '').trim();
  const previas = leerBitacora(historia ?? {});
  return nota ? [...previas, { fecha, autor, texto: nota }] : previas;
}

export const textosBitacora = (historia) => leerBitacora(historia).map((nota) => nota.texto);
