// Revisiones de una HU aprobada: un cambio de alcance no crea otra HU, la misma HU (mismo código) pasa
// a una revisión nueva. La revisión vigente es la que se muestra y se guarda en el Repositorio de HU;
// las anteriores quedan en el historial de la propia historia.
import { construirReanalisis, etiquetaHistoria } from './plantillaHu';

export const MOTIVO_INICIAL = 'Aprobación inicial';

export const numeroRevision = (historia = {}) => Number(historia.revision) > 0 ? Number(historia.revision) : 1;

export const etiquetaRevision = (historia = {}) => `Rev. ${numeroRevision(historia)}`;

// Datos con los que se abre el asistente para analizar el cambio sobre la HU vigente.
export function construirRevision(historia = {}, solicitud = '') {
  const usuario = historia.userStory ?? {};
  return {
    ...construirReanalisis(historia),
    name: historia.title ?? '',
    infoType: 'Solicitud de cambio',
    description: [
      `Cambio de alcance sobre la HU aprobada ${etiquetaHistoria(historia)} (${historia.title ?? ''}), ${etiquetaRevision(historia)} vigente.`,
      `HU vigente: Como ${usuario.asA ?? ''}, quiero ${usuario.iWant ?? ''}, para ${usuario.soThat ?? ''}.`,
      `Cambio pedido por Negocio: ${solicitud}`,
    ].join('\n'),
    userStory: usuario,
    acceptanceCriteria: historia.acceptanceCriteria ?? [],
    revisionDeId: historia.id,
    motivoRevision: String(solicitud ?? '').trim(),
  };
}

// Foto de la revisión vigente para guardarla en el historial antes de reemplazarla.
export function fotoRevision(historia = {}) {
  return {
    revision: numeroRevision(historia),
    approvedAt: historia.approvedAt ?? historia.updatedAt ?? historia.createdAt ?? '',
    title: historia.title ?? '',
    userStory: historia.userStory ?? {},
    acceptanceCriteria: historia.acceptanceCriteria ?? [],
    motivo: historia.motivoRevision || MOTIVO_INICIAL,
  };
}

// Campos que cambian en la HU original cuando se aprueba una revisión nueva.
export function aplicarRevision(original = {}, datosNuevo = {}, motivo = '') {
  return {
    ...datosNuevo,
    revision: numeroRevision(original) + 1,
    motivoRevision: String(motivo ?? '').trim(),
    revisiones: [...(original.revisiones ?? []), fotoRevision(original)],
  };
}
