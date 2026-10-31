// Respuestas de Negocio a las preguntas de una historia ya guardada (pantalla Editar).
const texto = (valor) => String(valor ?? '').trim();

// Lista de respuestas (una por pregunta, mismo orden) a partir de las preguntas guardadas.
export const respuestasDePreguntas = (listaPregunta = []) => listaPregunta.map((pregunta) => pregunta.answer ?? '');

// ¿Se agregó o cambió alguna respuesta respecto de lo guardado?
export const respuestasCambiaron = (listaPregunta = [], listaRespuesta = []) =>
  listaPregunta.some((pregunta, indice) => texto(pregunta.answer) !== texto(listaRespuesta[indice]));

// "Respondida" solo si hay una respuesta escrita; si no, queda pendiente.
export const aplicarRespuestas = (listaPregunta = [], listaRespuesta = []) =>
  listaPregunta.map((pregunta, indice) => {
    const answer = texto(listaRespuesta[indice]);
    return { ...pregunta, answer, status: answer ? 'respondida' : 'pendiente' };
  });

// Textos de las preguntas que siguen sin respuesta (se calcula siempre desde las preguntas).
export const textoPendiente = (listaPregunta = []) =>
  listaPregunta.filter((pregunta) => !texto(pregunta.answer)).map((pregunta) => pregunta.question);
