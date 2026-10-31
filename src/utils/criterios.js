import { ETIQUETA_CRITERIO, quitarEtiqueta } from './plantillaHu';
import { generarGuid } from './guid';

// Un criterio de aceptación son tres campos editables: Dado que, Cuando y Entonces.
const texto = (valor) => String(valor ?? '').trim();

export const criterioNuevo = () => ({ id: generarGuid(), given: '', when: '', then: '' });

// Criterios genéricos de partida, hasta que exista el Agente Redactor-Revisor. No incluyen datos del requerimiento.
export const criteriosGenericos = () => [
  {
    id: generarGuid(),
    given: 'el usuario ingresa la información requerida',
    when: 'confirma el registro',
    then: 'el sistema valida los datos obligatorios y registra la solicitud',
  },
  {
    id: generarGuid(),
    given: 'existe una solicitud vigente para la misma entidad',
    when: 'se intenta registrar una solicitud idéntica',
    then: 'el sistema muestra una advertencia e impide la duplicación',
  },
  {
    id: generarGuid(),
    given: 'una operación se aprueba o se modifica',
    when: 'se consulta la bitácora de auditoría',
    then: 'se muestra el historial con fecha, hora y usuario responsable',
  },
];

const partes = (criterio) => [
  quitarEtiqueta(texto(criterio?.given), ETIQUETA_CRITERIO.given),
  quitarEtiqueta(texto(criterio?.when), ETIQUETA_CRITERIO.when),
  quitarEtiqueta(texto(criterio?.then), ETIQUETA_CRITERIO.then),
];

export const criterioCompleto = (criterio) => partes(criterio).every(Boolean);
export const criterioVacio = (criterio) => partes(criterio).every((parte) => !parte);

// Frase resumen del criterio («Dado que …, cuando …, entonces …»). Si es un criterio antiguo con solo texto, lo devuelve.
export function resumenCriterio(criterio) {
  if (criterioVacio(criterio)) return texto(criterio?.text);
  const [dado, cuando, entonces] = partes(criterio);
  return `Dado que ${dado}, cuando ${cuando}, entonces ${entonces}.`;
}

// Valida la lista: se ignoran los criterios vacíos, no se permiten incompletos y se exige al menos uno completo.
export function validarCriterios(lista = []) {
  const conContenido = lista.filter((criterio) => !criterioVacio(criterio));
  if (conContenido.length === 0) return { ok: false, error: 'Agregue al menos un criterio con Dado que, Cuando y Entonces.' };
  const incompleto = conContenido.findIndex((criterio) => !criterioCompleto(criterio));
  if (incompleto >= 0) {
    return { ok: false, error: `Complete Dado que, Cuando y Entonces del criterio ${lista.indexOf(conContenido[incompleto]) + 1}, o quítelo.` };
  }
  return { ok: true, error: '' };
}

// Lista lista para guardar: sin criterios vacíos y sin etiquetas repetidas dentro del texto.
export function limpiarCriterios(lista = []) {
  return lista
    .filter((criterio) => !criterioVacio(criterio))
    .map((criterio) => {
      const [given, when, then] = partes(criterio);
      return { id: criterio.id || generarGuid(), given, when, then };
    });
}

// Convierte lo guardado a lo editable (un criterio antiguo con solo texto pasa al campo Entonces).
export function criteriosParaEditar(lista = []) {
  return lista.map((criterio) => {
    if (criterioVacio(criterio) && texto(criterio?.text)) {
      return { id: criterio.id || generarGuid(), given: '', when: '', then: texto(criterio.text) };
    }
    const [given, when, then] = partes(criterio);
    return { id: criterio?.id || generarGuid(), given, when, then };
  });
}

export function criteriosCambiaron(anterior = [], nuevo = []) {
  const firma = (lista) => JSON.stringify(limpiarCriterios(criteriosParaEditar(lista)).map(({ given, when, then }) => [given, when, then]));
  return firma(anterior) !== firma(nuevo);
}
