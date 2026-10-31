// Plantilla de la Historia de Usuario: campos que se piden y valores por defecto.
// Se usa en el asistente "Nueva Historia", en la edición y en la exportación a Word.

export const PREFIJO_HU = (import.meta.env?.VITE_PREFIJO_HU || 'HU').trim();
export const PENDIENTE = 'Pendiente de completar';

export const TIPOS_SOLICITUD = Object.freeze(['Requerimiento', 'Incidente', 'Problema']);

export const ROLES_FIRMA = Object.freeze([
  { clave: 'elaborado', rotulo: 'Elaborado y Product Owner' },
  { clave: 'supervisor', rotulo: 'Supervisor del área solicitante' },
  { clave: 'coordinador', rotulo: 'Coordinador de desarrollo' },
  { clave: 'aprobador', rotulo: 'Aprobado' },
]);

export const FIRMANTE_VACIO = Object.freeze(
  Object.fromEntries(ROLES_FIRMA.map((rol) => [rol.clave, '']))
);

export function normalizarCodigoHu(codigo) {
  return String(codigo ?? '')
    .trim()
    .toUpperCase()
    .replace(/\s+/g, '-')
    .replace(/[^A-Z0-9-]/g, '');
}

// Propone el siguiente número disponible para el código de HU: PREFIJO-CODIGO-001, 002, ...
export function numeroSugerido(codigoHu, listaHistoria = []) {
  const codigoNormalizado = normalizarCodigoHu(codigoHu);
  if (!codigoNormalizado) return '';
  const base = `${PREFIJO_HU}-${codigoNormalizado}-`;
  const mayor = listaHistoria.reduce((acumulado, historia) => {
    const numero = String(historia?.number ?? '');
    if (!numero.startsWith(base)) return acumulado;
    const consecutivo = Number.parseInt(numero.slice(base.length), 10);
    return Number.isFinite(consecutivo) ? Math.max(acumulado, consecutivo) : acumulado;
  }, 0);
  return `${base}${String(mayor + 1).padStart(3, '0')}`;
}

// Código legible de la historia (HU-CODIGO-001). El id es un GUID interno y nunca se muestra como código.
export const SIN_CODIGO = 'Sin código';
export function etiquetaHistoria(historia = {}) {
  return String(historia?.number ?? '').trim() || SIN_CODIGO;
}

export function limpiarLista(lista) {
  return (lista ?? []).map((texto) => String(texto ?? '').trim()).filter(Boolean);
}

// Etiquetas en español de los criterios de aceptación (Dado / Cuando / Entonces).
export const ETIQUETA_CRITERIO = Object.freeze({ given: 'Dado que', when: 'Cuando', then: 'Entonces' });

// Quita la etiqueta si el texto ya la trae («Dado que ...») para no mostrarla dos veces.
export function quitarEtiqueta(texto, etiqueta) {
  const patron = new RegExp(`^${etiqueta.replace(/\s+/g, '\\s+')}\\s*:?\\s*`, 'i');
  return String(texto ?? '').trim().replace(patron, '');
}

// Indica si al editar cambió el requerimiento que el Agente Analista ya había analizado.
export function requerimientoCambio(anterior = {}, nuevo = {}) {
  const campo = (valor) => String(valor ?? '').trim();
  return campo(anterior.title) !== campo(nuevo.title)
    || campo(anterior.infoType) !== campo(nuevo.infoType)
    || campo(anterior.description) !== campo(nuevo.description);
}

// Datos con los que el asistente se vuelve a abrir para re-analizar un borrador.
export function construirReanalisis(historia = {}) {
  return {
    name: historia.title ?? '',
    infoType: historia.infoType ?? 'Minuta',
    description: historia.description ?? '',
    system: historia.system ?? '',
    codigoHu: historia.codigoHu ?? historia.area ?? '',
    requester: historia.requester ?? '',
    requestType: historia.requestType,
    number: historia.number ?? '',
    benefits: historia.benefits ?? [],
    signers: historia.signers ?? {},
    // Las respuestas ya registradas viajan al agente para que no se vuelvan a preguntar.
    questions: historia.questions ?? [],
  };
}
