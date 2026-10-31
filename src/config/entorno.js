// Valores de compilación que se pueden cambiar con variables de entorno (Vite las lee al construir):
//   VITE_ANIO     año de derechos reservados del pie de página (por defecto, el año actual)
//   VITE_VERSION  versión que se muestra en el pie de página (por defecto, 1.0.0)
const limpiar = (valor, patron, porDefecto) => {
  const texto = String(valor ?? '').trim();
  return patron.test(texto) ? texto : porDefecto;
};

export const ANIO_DERECHOS = limpiar(import.meta.env?.VITE_ANIO, /^\d{4}$/, String(new Date().getFullYear()));
export const VERSION_APLICACION = limpiar(import.meta.env?.VITE_VERSION, /^[0-9A-Za-z][0-9A-Za-z.+-]{0,29}$/, '1.0.0');
export const TEXTO_PIE = `HISTORIAS DE USUARIO ® Derechos Reservados ${ANIO_DERECHOS} - V.${VERSION_APLICACION}`;
