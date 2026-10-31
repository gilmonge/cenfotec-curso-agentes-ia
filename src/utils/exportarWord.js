import {
  AlignmentType, BorderStyle, Document, Footer, Header, Packer, PageNumber, Paragraph, ShadingType,
  Table, TableCell, TableRow, TextRun, VerticalMergeType, WidthType,
} from 'docx';
import { PENDIENTE, quitarEtiqueta } from './plantillaHu';
import { armarContenido } from './contenidoHu';
import { COLOR, FORMATO, pieIzquierdo, tituloEncabezado } from './plantillaDocumento';

const BORDE = { style: BorderStyle.SINGLE, size: 4, color: COLOR.borde };
const BORDES = { top: BORDE, bottom: BORDE, left: BORDE, right: BORDE };
const SIN_BORDE = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
const SIN_BORDES = { top: SIN_BORDE, bottom: SIN_BORDE, left: SIN_BORDE, right: SIN_BORDE };

const parrafo = (texto, opciones = {}) => new Paragraph({
  spacing: { after: 60 },
  alignment: opciones.alineacion,
  children: [new TextRun({ text: texto, bold: opciones.negrita, color: opciones.color, italics: opciones.cursiva, size: opciones.tamano })],
});

const celda = (texto, {
  ancho, negrita = false, fondo, color, columnas = 1, cursiva = false, alineacion, fusion, tamano,
} = {}) => new TableCell({
  borders: BORDES,
  columnSpan: columnas,
  verticalMerge: fusion,
  width: ancho ? { size: ancho, type: WidthType.PERCENTAGE } : undefined,
  shading: fondo ? { type: ShadingType.CLEAR, fill: fondo, color: 'auto' } : undefined,
  margins: { top: 60, bottom: 60, left: 100, right: 100 },
  children: [parrafo(texto, { negrita, color, cursiva, alineacion, tamano })],
});

const esPendiente = (texto) => texto === PENDIENTE;
const rotulo = (texto, ancho) => celda(texto, { ancho, fondo: COLOR.durazno });
const valor = (texto, ancho, columnas = 1) => celda(texto, { ancho, columnas, cursiva: esPendiente(texto) });

// Fila de 4 columnas: rótulo, valor, rótulo, valor
const filaDoble = ([rotuloA, valorA], [rotuloB, valorB]) => new TableRow({
  children: [rotulo(rotuloA, 20), valor(valorA, 30), rotulo(rotuloB, 20), valor(valorB, 30)],
});

const filaSimple = ([nombre, texto]) => new TableRow({ children: [rotulo(nombre, 20), valor(texto, 80, 3)] });

// Barra de título de la sección: la principal va en naranja sólido y las secundarias en durazno.
const filaTitulo = (texto, { principal = false } = {}) => new TableRow({
  children: [celda(texto, {
    columnas: 4,
    negrita: true,
    fondo: principal ? COLOR.naranja : COLOR.durazno,
    color: principal ? 'FFFFFF' : COLOR.naranjaTexto,
    alineacion: principal ? AlignmentType.LEFT : AlignmentType.CENTER,
  })],
});

const tabla = (filas) => new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: filas });


// Devuelve «Etiqueta: texto» sin duplicar la etiqueta si el texto ya la trae.
export function conEtiqueta(texto, etiqueta) {
  const limpio = quitarEtiqueta(texto, etiqueta);
  return limpio ? `${etiqueta}: ${limpio}` : '';
}

function bloqueCriterio(criterio, indice, total) {
  const lista = [];
  if (total > 1) {
    lista.push(new Paragraph({
      keepNext: true,
      spacing: { before: 160, after: 60 },
      children: [new TextRun({ text: `Criterio ${indice + 1}`, bold: true })],
    }));
  }
  if (criterio.partes.length === 0) {
    lista.push(parrafo(criterio.texto));
    return lista;
  }
  criterio.partes.forEach(([etiqueta, texto]) => {
    lista.push(new Paragraph({
      spacing: { after: 60 },
      children: [new TextRun({ text: `${etiqueta}: `, bold: true }), new TextRun({ text: texto })],
    }));
  });
  return lista;
}

const MARCA_LOGO = () => new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  borders: { top: SIN_BORDE, bottom: SIN_BORDE, left: SIN_BORDE, right: SIN_BORDE, insideHorizontal: SIN_BORDE, insideVertical: SIN_BORDE },
  rows: [new TableRow({ children: [new TableCell({
    borders: SIN_BORDES,
    shading: { type: ShadingType.CLEAR, fill: COLOR.naranja, color: 'auto' },
    margins: { top: 40, bottom: 40, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: FORMATO.marca, bold: true, color: 'FFFFFF', size: 28 })],
    })],
  })] })],
});

// Encabezado: marca genérica a la izquierda y el código de la HU a la derecha, con línea naranja.
const encabezado = (historia) => new Header({
  children: [
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      borders: { top: SIN_BORDE, bottom: SIN_BORDE, left: SIN_BORDE, right: SIN_BORDE, insideHorizontal: SIN_BORDE, insideVertical: SIN_BORDE },
      rows: [new TableRow({ children: [
        new TableCell({ borders: SIN_BORDES, width: { size: 15, type: WidthType.PERCENTAGE }, children: [MARCA_LOGO()] }),
        new TableCell({
          borders: SIN_BORDES,
          width: { size: 85, type: WidthType.PERCENTAGE },
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: tituloEncabezado(historia), bold: true, color: '595959', size: 26, smallCaps: true })],
          })],
        }),
      ] })],
    }),
    new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: COLOR.naranja, space: 1 } }, children: [] }),
  ],
});

// Pie: código del formato, control y «Pág. X de Y».
const pie = () => new Footer({
  children: [
    new Paragraph({
      shading: { type: ShadingType.CLEAR, fill: COLOR.gris, color: 'auto' },
      tabStops: [{ type: 'center', position: 5200 }, { type: 'right', position: 9000 }],
      children: [
        new TextRun({ text: pieIzquierdo(), bold: true, size: 16 }),
        new TextRun({ text: `\t${FORMATO.control}`, bold: true, color: COLOR.naranjaTexto, size: 20 }),
        new TextRun({ children: ['\tPág. ', PageNumber.CURRENT, ' de ', PageNumber.TOTAL_PAGES], size: 16 }),
      ],
    }),
  ],
});

export function construirDocumento(historia) {
  const hu = historia ?? {};
  const contenido = armarContenido(hu);

  const referencias = tabla([
    filaTitulo('Referencias', { principal: true }),
    filaDoble(contenido.referencias[0], contenido.referencias[1]),
    filaSimple(contenido.referencias[2]),
    filaSimple(contenido.referencias[3]),
    ...contenido.declaracion.map(([nombre, texto], indice) => new TableRow({
      children: [
        celda(indice === 0 ? 'Declaración de valor' : '', {
          ancho: 20, fondo: COLOR.durazno, fusion: indice === 0 ? VerticalMergeType.RESTART : VerticalMergeType.CONTINUE,
        }),
        celda(nombre, { ancho: 15, fondo: COLOR.durazno }),
        celda(texto, { ancho: 65, columnas: 2, cursiva: esPendiente(texto) }),
      ],
    })),
  ]);

  const [prioridadNegocio, apetito, control, probabilidad] = contenido.priorizacion;
  const priorizacion = tabla([
    filaTitulo('Priorización del negocio'),
    filaDoble(prioridadNegocio, apetito),
    filaDoble(control, probabilidad),
  ]);

  const [sprint, esfuerzo, prioridad, riesgo, dependencias] = contenido.revision;
  const revision = tabla([
    filaTitulo('Revisión de Desarrollo'),
    filaDoble(sprint, esfuerzo),
    filaDoble(prioridad, riesgo),
    filaSimple(dependencias),
  ]);

  const beneficios = tabla([
    filaTitulo('Beneficios esperados', { principal: true }),
    new TableRow({
      children: [new TableCell({
        borders: BORDES,
        columnSpan: 4,
        margins: { top: 100, bottom: 100, left: 160, right: 160 },
        children: contenido.beneficios.length > 0
          ? contenido.beneficios.map((texto) => new Paragraph({ text: texto, bullet: { level: 0 }, spacing: { after: 80 }, alignment: AlignmentType.JUSTIFIED }))
          : [parrafo(PENDIENTE, { cursiva: true })],
      })],
    }),
  ]);

  const firmas = tabla([
    new TableRow({
      children: [
        celda('Firmas de Aprobación', { ancho: 40, negrita: true, fondo: COLOR.naranja, color: 'FFFFFF' }),
        celda('Nombre del responsable', { ancho: 30, fondo: COLOR.durazno_claro }),
        celda('Fecha', { ancho: 15, fondo: COLOR.durazno_claro }),
        celda('Firma', { ancho: 15, fondo: COLOR.durazno_claro }),
      ],
    }),
    ...contenido.firmas.map(([nombreRol, nombre]) => new TableRow({
      children: [
        celda(nombreRol, { ancho: 40, fondo: COLOR.durazno }),
        celda(nombre, { ancho: 30, cursiva: esPendiente(nombre) }),
        celda('', { ancho: 15 }),
        celda('', { ancho: 15 }),
      ],
    })),
  ]);

  const espacio = () => new Paragraph({ text: '' });

  const criterios = contenido.criterios.length > 0
    ? contenido.criterios.flatMap((criterio, indice) => bloqueCriterio(criterio, indice, contenido.criterios.length))
    : [parrafo(PENDIENTE, { cursiva: true })];

  // Como en la plantilla: al final, en página aparte y solo con el texto de cada nota.
  const observaciones = contenido.observaciones.length > 0
    ? [
      new Paragraph({ pageBreakBefore: true, spacing: { after: 200 }, children: [new TextRun({ text: 'Observaciones adicionales', bold: true })] }),
      ...contenido.observaciones.map((texto) => new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: texto })] })),
    ]
    : [];

  return new Document({
    creator: 'Historias de Usuario',
    title: contenido.titulo,
    sections: [{
      headers: { default: encabezado(hu) },
      footers: { default: pie() },
      children: [
        referencias, espacio(),
        priorizacion,
        revision, espacio(),
        beneficios, espacio(),
        firmas, espacio(),
        new Paragraph({ spacing: { before: 200, after: 120 }, children: [new TextRun({ text: 'Criterios de Aceptación', bold: true, size: 26 })] }),
        ...criterios,
        ...observaciones,
      ],
    }],
  });
}

export function nombreArchivo(historia) {
  const base = String(historia?.number || historia?.id || 'historia-de-usuario');
  return `${base.replace(/[^A-Za-z0-9-_]/g, '_')}.docx`;
}

export async function descargarWord(historia) {
  const blob = await Packer.toBlob(construirDocumento(historia));
  const direccion = URL.createObjectURL(blob);
  const enlace = document.createElement('a');
  enlace.href = direccion;
  enlace.download = nombreArchivo(historia);
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(direccion);
}
