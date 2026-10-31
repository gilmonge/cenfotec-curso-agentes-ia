// Datos fijos de la plantilla de los documentos (Word y PDF): colores, código del formato y pie de página.
// Los textos pueden ajustarse sin tocar el código con variables de entorno de Vite.
const env = (nombre, porDefecto) => String(import.meta.env?.[nombre] || porDefecto).trim();

export const COLOR = Object.freeze({
  naranja: 'ED7D31',
  naranjaTexto: 'C55A11',
  durazno: 'F8CBAD',
  durazno_claro: 'FBE4D5',
  gris: 'F4F4F4',
  borde: 'BFBFBF',
});

export const FORMATO = Object.freeze({
  codigo: env('VITE_DOC_CODIGO_FORMATO', 'FOR-HUS'),
  version: env('VITE_DOC_VERSION', 'V 1.0'),
  control: env('VITE_DOC_CONTROL', 'CTL - 01'),
  marca: 'HU',
  organizacion: env('VITE_DOC_ORGANIZACION', 'Historias de Usuario'),
});

export const pieIzquierdo = () => `${FORMATO.codigo}, Historia de Usuario ${FORMATO.version}`;
export const tituloEncabezado = (historia) => `Historia de Usuario ${historia?.number || historia?.id || ''}`.trim();

export const hexARgb = (hex) => [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
