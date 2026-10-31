// Registro de las ediciones hechas sobre una HU ya aprobada: quién, cuándo y qué campos cambió.
// Una edición corrige la HU tal como está; no genera una revisión nueva (eso solo lo hace un cambio de alcance).
import { criteriosCambiaron } from './criterios';
import { FIRMANTE_VACIO, limpiarLista, normalizarCodigoHu } from './plantillaHu';

const texto = (valor) => String(valor ?? '').trim();
const igualesLista = (a, b) => JSON.stringify(limpiarLista(a ?? [])) === JSON.stringify(limpiarLista(b ?? []));

// Nombres de los campos que cambiaron, en lenguaje de la persona usuaria.
export function camposEditados(original = {}, nuevo = {}) {
  const campos = [];
  if (texto(original.title) !== texto(nuevo.title)) campos.push('Título');
  const antes = original.userStory ?? {};
  const despues = nuevo.userStory ?? {};
  if (['asA', 'iWant', 'soThat'].some((clave) => texto(antes[clave]) !== texto(despues[clave]))) campos.push('Historia (Como / Quiero / Para)');
  if (criteriosCambiaron(original.acceptanceCriteria, nuevo.acceptanceCriteria)) campos.push('Criterios de aceptación');
  const plantillaCambio = texto(original.system) !== texto(nuevo.system)
    || normalizarCodigoHu(original.codigoHu ?? original.area ?? '') !== normalizarCodigoHu(nuevo.codigoHu ?? '')
    || texto(original.requester) !== texto(nuevo.requester)
    || texto(original.number) !== texto(nuevo.number)
    || !igualesLista(original.benefits, nuevo.benefits)
    || JSON.stringify({ ...FIRMANTE_VACIO, ...(original.signers ?? {}) }) !== JSON.stringify({ ...FIRMANTE_VACIO, ...(nuevo.signers ?? {}) });
  if (plantillaCambio) campos.push('Datos de la plantilla');
  if (texto(nuevo.notaNueva)) campos.push('Observaciones');
  return campos;
}

export function registrarEdicion(historia = {}, campos = [], { fecha = new Date().toISOString(), autor = '' } = {}) {
  return [...(historia.ediciones ?? []), { fecha, autor, campos }];
}
