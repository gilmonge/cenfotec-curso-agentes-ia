import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { PENDIENTE } from './plantillaHu';
import { armarContenido } from './contenidoHu';
import { COLOR, FORMATO, hexARgb, pieIzquierdo, tituloEncabezado } from './plantillaDocumento';

const NARANJA = hexARgb(COLOR.naranja);
const NARANJA_TEXTO = hexARgb(COLOR.naranjaTexto);
const DURAZNO = hexARgb(COLOR.durazno);
const DURAZNO_CLARO = hexARgb(COLOR.durazno_claro);
const GRIS = hexARgb(COLOR.gris);
const BORDE = hexARgb(COLOR.borde);

const MARGEN = 14;
const ANCHO_PAGINA = 210;
const ANCHO_TEXTO = ANCHO_PAGINA - MARGEN * 2;
const MARGEN_SUPERIOR = 30;
const MARGEN_INFERIOR = 30;
const LIMITE_Y = 297 - MARGEN_INFERIOR;
const INTERLINEA = 4.6;

export function nombreArchivoPdf(historia) {
  const base = String(historia?.number || historia?.id || 'historia-de-usuario');
  return `${base.replace(/[^A-Za-z0-9-_]/g, '_')}.pdf`;
}

const estiloTabla = {
  theme: 'grid',
  styles: { fontSize: 9, cellPadding: 2, lineColor: BORDE, lineWidth: 0.1, textColor: 30 },
  margin: { left: MARGEN, right: MARGEN, top: MARGEN_SUPERIOR, bottom: MARGEN_INFERIOR },
};

const rotulo = (content, extra = {}) => ({ content, styles: { fillColor: DURAZNO, fontStyle: 'normal', ...extra.styles }, ...extra });
const barra = (content, columnas, principal) => ({
  content,
  colSpan: columnas,
  styles: principal
    ? { fillColor: NARANJA, textColor: 255, fontStyle: 'bold', halign: 'left' }
    : { fillColor: DURAZNO, textColor: NARANJA_TEXTO, fontStyle: 'bold', halign: 'center' },
});

const pares = (lista) => lista.reduce((acumulado, item, indice) => (
  indice % 2 === 0 ? [...acumulado, [item, lista[indice + 1]]] : acumulado
), []);

// Dos pares rótulo/valor por fila (4 columnas); si sobra uno, ocupa el ancho restante.
const filasDobles = (lista) => pares(lista).map(([a, b]) => (b
  ? [rotulo(a[0]), a[1], rotulo(b[0]), b[1]]
  : [rotulo(a[0]), { content: a[1], colSpan: 3 }]));

function dibujarTabla(doc, cuerpo, { cabecera, columnas }) {
  autoTable(doc, {
    ...estiloTabla,
    startY: (doc.lastAutoTable?.finalY ?? MARGEN_SUPERIOR - 6) + 5,
    head: cabecera,
    body: cuerpo,
    columnStyles: columnas,
    didParseCell: (datos) => {
      if (datos.section === 'body' && datos.cell.text.join('') === PENDIENTE) {
        datos.cell.styles.fontStyle = 'italic';
        datos.cell.styles.textColor = 120;
      }
    },
  });
}

const anchos4 = { 0: { cellWidth: 38 }, 1: { cellWidth: 48 }, 2: { cellWidth: 38 }, 3: { cellWidth: 58 } };

function referencias(doc, contenido) {
  const [historia, solicitud, sistema, solicitante] = contenido.referencias;
  const filas = [
    [rotulo(historia[0]), { content: historia[1], colSpan: 3 }],
    [rotulo(solicitud[0]), { content: solicitud[1], colSpan: 3 }],
    [rotulo(sistema[0]), sistema[1], rotulo(solicitante[0]), solicitante[1]],
    ...contenido.declaracion.map(([nombre, texto], indice) => (indice === 0
      ? [rotulo('Declaración de valor', { rowSpan: 3 }), rotulo(nombre), { content: texto, colSpan: 2 }]
      : [rotulo(nombre), { content: texto, colSpan: 2 }])),
  ];
  dibujarTabla(doc, filas, { cabecera: [[barra('Referencias', 4, true)]], columnas: anchos4 });
}

// Encabezado y pie de cada página, dibujados al final para conocer el total de páginas.
function marcarPaginas(doc, historia) {
  const total = doc.getNumberOfPages();
  for (let pagina = 1; pagina <= total; pagina += 1) {
    doc.setPage(pagina);

    doc.setFillColor(...NARANJA);
    doc.rect(MARGEN, 10, 14, 10, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(255);
    doc.text(FORMATO.marca, MARGEN + 7, 16.8, { align: 'center' });
    doc.setFontSize(8);
    doc.setTextColor(100);
    doc.text(FORMATO.organizacion, MARGEN + 17, 16.8);
    doc.setFontSize(13);
    doc.setTextColor(89);
    doc.text(tituloEncabezado(historia), ANCHO_PAGINA - MARGEN, 16.8, { align: 'right' });
    doc.setDrawColor(...NARANJA);
    doc.setLineWidth(0.8);
    doc.line(MARGEN, 22, ANCHO_PAGINA - MARGEN, 22);

    doc.setFillColor(...GRIS);
    doc.rect(MARGEN, 277, ANCHO_TEXTO, 6, 'F');
    doc.setFontSize(8);
    doc.setTextColor(30);
    doc.text(pieIzquierdo(), MARGEN + 2, 281);
    doc.setFontSize(10);
    doc.setTextColor(...NARANJA_TEXTO);
    doc.text(FORMATO.control, ANCHO_PAGINA / 2, 281, { align: 'center' });
    doc.setFontSize(8);
    doc.setTextColor(30);
    doc.text(`Pág. ${pagina} de ${total}`, ANCHO_PAGINA - MARGEN - 2, 281, { align: 'right' });
  }
}

export function construirPdf(historia) {
  const hu = historia ?? {};
  const contenido = armarContenido(hu);
  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  doc.setProperties({ title: contenido.titulo, creator: 'Historias de Usuario' });

  referencias(doc, contenido);

  dibujarTabla(doc, filasDobles(contenido.priorizacion), {
    cabecera: [[barra('Priorización del negocio', 4, false)]],
    columnas: anchos4,
  });
  dibujarTabla(doc, filasDobles(contenido.revision), {
    cabecera: [[barra('Revisión de Desarrollo', 4, false)]],
    columnas: anchos4,
  });

  const viñetas = contenido.beneficios.length > 0
    ? contenido.beneficios.map((texto) => `•  ${texto}`).join('\n')
    : PENDIENTE;
  dibujarTabla(doc, [[{ content: viñetas, styles: { cellPadding: 4, halign: 'left' } }]], {
    cabecera: [[barra('Beneficios esperados', 1, true)]],
    columnas: {},
  });

  autoTable(doc, {
    ...estiloTabla,
    startY: doc.lastAutoTable.finalY + 5,
    head: [[
      { content: 'Firmas de Aprobación', styles: { fillColor: NARANJA, textColor: 255, fontStyle: 'bold' } },
      { content: 'Nombre del responsable', styles: { fillColor: DURAZNO_CLARO, textColor: 30, fontStyle: 'normal' } },
      { content: 'Fecha', styles: { fillColor: DURAZNO_CLARO, textColor: 30, fontStyle: 'normal' } },
      { content: 'Firma', styles: { fillColor: DURAZNO_CLARO, textColor: 30, fontStyle: 'normal' } },
    ]],
    body: contenido.firmas.map(([nombreRol, nombre]) => [rotulo(nombreRol), nombre, '', '']),
    styles: { ...estiloTabla.styles, cellPadding: 3 },
    columnStyles: { 0: { cellWidth: 60 }, 2: { cellWidth: 25 }, 3: { cellWidth: 30 } },
    didParseCell: (datos) => {
      if (datos.section === 'body' && datos.cell.text.join('') === PENDIENTE) {
        datos.cell.styles.fontStyle = 'italic';
        datos.cell.styles.textColor = 120;
      }
    },
  });

  let y = doc.lastAutoTable.finalY + 10;
  const salto = (alto) => {
    if (y + alto > LIMITE_Y) { doc.addPage(); y = MARGEN_SUPERIOR; }
  };

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(30);
  salto(30);
  doc.text('Criterios de Aceptación', MARGEN, y);
  y += 7;

  doc.setFontSize(10);
  if (contenido.criterios.length === 0) {
    doc.setFont('helvetica', 'italic');
    doc.setTextColor(120);
    doc.text(PENDIENTE, MARGEN, y);
    y += INTERLINEA;
  }
  contenido.criterios.forEach((criterio, indice) => {
    salto(14);
    if (contenido.criterios.length > 1) {
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(30);
      doc.text(`Criterio ${indice + 1}`, MARGEN, y);
      y += 5;
    }
    const lineas = criterio.partes.length ? criterio.partes : [['', criterio.texto]];
    lineas.forEach(([etiqueta, texto]) => {
      const marca = etiqueta ? `${etiqueta}: ` : '';
      doc.setTextColor(30);
      doc.setFont('helvetica', 'bold');
      const anchoMarca = marca ? doc.getTextWidth(marca) : 0;
      doc.setFont('helvetica', 'normal');
      const primera = doc.splitTextToSize(texto, ANCHO_TEXTO - anchoMarca);
      const resto = doc.splitTextToSize(primera.slice(1).join(' '), ANCHO_TEXTO);
      const alto = (1 + (primera.length > 1 ? resto.length : 0)) * INTERLINEA + 1.5;
      salto(alto);
      if (marca) {
        doc.setFont('helvetica', 'bold');
        doc.text(marca, MARGEN, y);
        doc.setFont('helvetica', 'normal');
      }
      doc.text(primera[0] ?? '', MARGEN + anchoMarca, y);
      if (primera.length > 1) doc.text(resto, MARGEN, y + INTERLINEA);
      y += alto;
    });
    y += 3;
  });

  // Como en la plantilla: al final, en página aparte y solo con el texto de cada nota.
  if (contenido.observaciones.length > 0) {
    doc.addPage();
    y = MARGEN_SUPERIOR;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(30);
    doc.text('Observaciones adicionales', MARGEN, y);
    y += 8;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    contenido.observaciones.forEach((texto) => {
      const envuelto = doc.splitTextToSize(texto, ANCHO_TEXTO);
      salto(envuelto.length * INTERLINEA + 4);
      doc.text(envuelto, MARGEN, y);
      y += envuelto.length * INTERLINEA + 4;
    });
  }

  marcarPaginas(doc, hu);
  return doc;
}

export async function descargarPdf(historia) {
  construirPdf(historia).save(nombreArchivoPdf(historia));
}
