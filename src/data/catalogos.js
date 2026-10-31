// Listas fijas para los selectores del formulario. Son de ejemplo y se mantienen en el código.
export const OPCION_AREA_SOLICITANTE = Object.freeze([
  'Comercial',
  'Operaciones',
  'Finanzas y Contabilidad',
  'Tecnología de la Información',
  'Servicio al Cliente',
  'Cumplimiento y Riesgos',
  'Recursos Humanos',
]);

export const OPCION_SISTEMA = Object.freeze([
  'Gestión Comercial (CRM)',
  'Facturación y Cobros',
  'Portal de Clientes',
  'Gestión de Reclamos',
  'Reportes y Analítica',
  'Seguridad y Accesos',
]);

// Opciones para SelectorComponent. Si la historia ya trae un valor que no está en la lista,
// se conserva como opción para no perderlo al editar.
export function armarOpcion(lista, valorActual, textoVacio) {
  const actual = String(valorActual ?? '').trim();
  return [
    { value: '', label: textoVacio },
    ...lista.map((valor) => ({ value: valor, label: valor })),
    ...(actual && !lista.includes(actual) ? [{ value: actual, label: actual }] : []),
  ];
}
