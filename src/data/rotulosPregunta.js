// Textos que ve la persona de Negocio para las categorías de pregunta del agente.
// Los valores internos (clave) no cambian: los usan el agente, su validación y las lecciones.
export const ROTULO_CATEGORIA = Object.freeze({
  'Reglas de negocio': {
    rotulo: 'Cómo debe funcionar',
    ayuda: 'Las reglas o condiciones que deciden qué ocurre en cada caso.',
  },
  'Datos requeridos': {
    rotulo: 'Qué información se necesita',
    ayuda: 'Los datos que hay que pedir, mostrar o guardar.',
  },
  Validaciones: {
    rotulo: 'Qué se debe revisar',
    ayuda: 'Los controles para evitar datos incorrectos y qué avisar cuando algo no cumple.',
  },
  Excepciones: {
    rotulo: 'Qué pasa si algo sale mal',
    ayuda: 'Casos poco comunes o errores: qué debe ocurrir y qué debe ver la persona.',
  },
  'Comportamiento esperado': {
    rotulo: 'Qué debería ver o lograr la persona',
    ayuda: 'Cómo se espera que se use y qué resultado debe obtener.',
  },
});

export const rotuloCategoria = (categoria) => ROTULO_CATEGORIA[categoria]?.rotulo ?? categoria;
export const ayudaCategoria = (categoria) => ROTULO_CATEGORIA[categoria]?.ayuda ?? '';
