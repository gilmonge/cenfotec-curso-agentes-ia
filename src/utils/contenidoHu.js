import { PENDIENTE, ROLES_FIRMA, limpiarLista, quitarEtiqueta } from './plantillaHu';
import { filasBitacora } from './bitacora';

const valorOPendiente = (valor) => {
  const texto = String(valor ?? '').trim();
  return texto || PENDIENTE;
};

// Modelo de contenido de la HU (independiente del formato de salida: PDF, etc.).
export function armarContenido(historia) {
  const hu = historia ?? {};
  const relato = hu.userStory ?? {};
  const firmante = hu.signers ?? {};
  const nombre = `${hu.number || hu.id || ''} ${hu.title || ''}`.trim();

  return {
    titulo: nombre || 'Historia de Usuario',
    referencias: [
      ['Historia de Usuario', valorOPendiente(nombre)],
      ['Solicitud de Requerimiento / Incidente / Problema', valorOPendiente(hu.requestType)],
      ['Sistema', valorOPendiente(hu.system)],
      ['Solicitante', valorOPendiente(hu.requester)],
    ],
    declaracion: [
      ['Como', valorOPendiente(relato.asA)],
      ['Quiero', valorOPendiente(relato.iWant)],
      ['Para', valorOPendiente(relato.soThat)],
    ],
    priorizacion: [
      ['Prioridad Negocio', PENDIENTE],
      ['Apetito al riesgo', PENDIENTE],
      ['% de Control sobre el riesgo', PENDIENTE],
      ['Probabilidad de ocurrencia del riesgo', PENDIENTE],
    ],
    revision: [
      ['Sprint', PENDIENTE],
      ['Esfuerzo (puntos)', PENDIENTE],
      ['Prioridad', PENDIENTE],
      ['Riesgo Desarrollo', PENDIENTE],
      ['Dependencias', PENDIENTE],
    ],
    beneficios: limpiarLista(hu.benefits),
    // Una fila por entrada de la bitácora: Fecha | Tipo | Origen | Comentario | Estado.
    observaciones: filasBitacora(hu),
    firmas: ROLES_FIRMA.map((rol) => [
      `${rol.rotulo}:`,
      valorOPendiente(firmante[rol.clave] || (rol.clave === 'elaborado' ? hu.createdBy : '')),
    ]),
    criterios: (hu.acceptanceCriteria ?? []).map((criterio) => {
      const partes = [
        ['Dado que', criterio.given],
        ['Cuando', criterio.when],
        ['Entonces', criterio.then],
      ]
        .map(([etiqueta, texto]) => [etiqueta, quitarEtiqueta(texto, etiqueta)])
        // «Dado que» ya trae el «que»: si el texto también empieza con «que», se quita.
        .map(([etiqueta, texto]) => [etiqueta, etiqueta === 'Dado que' ? texto.replace(/^que\s+/i, '') : texto])
        .filter(([, texto]) => texto);
      return { partes, texto: String(criterio.text ?? '').trim() };
    }),
  };
}
