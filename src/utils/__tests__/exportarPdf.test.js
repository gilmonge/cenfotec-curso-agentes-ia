import { describe, expect, it } from 'vitest';
import { armarContenido } from '../contenidoHu';
import { construirPdf, nombreArchivoPdf } from '../exportarPdf';
import { PENDIENTE } from '../plantillaHu';
import { Packer } from 'docx';
import { construirDocumento } from '../exportarWord';

const historia = {
  id: 'HU-1',
  number: 'HU-POL-001',
  title: 'Registrar póliza',
  system: 'Sistema',
  userStory: { asA: 'analista', iWant: 'registrar', soThat: 'controlar' },
  benefits: ['Menos errores', ' '],
  signers: { elaborado: 'Persona A' },
  acceptanceCriteria: [
    { given: 'Dado que existe una póliza', when: 'Cuando se guarda', then: 'Entonces se confirma' },
    { text: 'Criterio libre' },
  ],
};

describe('exportar PDF', () => {
  it('arma el contenido sin duplicar etiquetas y con pendientes', () => {
    const contenido = armarContenido(historia);
    expect(contenido.titulo).toBe('HU-POL-001 Registrar póliza');
    expect(contenido.criterios[0].partes[0]).toEqual(['Dado que', 'existe una póliza']);
    expect(contenido.criterios[1].texto).toBe('Criterio libre');
    expect(contenido.beneficios).toEqual(['Menos errores']);
    expect(contenido.referencias.find(([r]) => r === 'Solicitante')[1]).toBe(PENDIENTE);
  });

  it('genera un PDF de al menos una página y un nombre seguro', () => {
    const doc = construirPdf(historia);
    expect(doc.getNumberOfPages()).toBeGreaterThanOrEqual(1);
    expect(doc.output('arraybuffer').byteLength).toBeGreaterThan(1000);
    expect(nombreArchivoPdf({ number: 'HU POL/1' })).toBe('HU_POL_1.pdf');
  });

  it('no falla con una historia vacía', () => {
    expect(() => construirPdf({})).not.toThrow();
  });

  it('incluye la declaración de valor y solo el texto de las observaciones', () => {
    const conNotas = {
      ...historia,
      bitacora: [{ fecha: '2026-10-01', autor: 'Ana', texto: 'Nota uno' }, { fecha: '2026-10-02', autor: 'Luis', texto: 'Nota dos' }],
    };
    const contenido = armarContenido(conNotas);
    expect(contenido.declaracion).toEqual([['Como', 'analista'], ['Quiero', 'registrar'], ['Para', 'controlar']]);
    expect(contenido.observaciones).toEqual(['Nota uno', 'Nota dos']);
    expect(armarContenido(historia).observaciones).toEqual([]);
  });

  it('agrega una página de observaciones solo cuando hay notas', () => {
    const sin = construirPdf(historia).getNumberOfPages();
    const con = construirPdf({ ...historia, bitacora: [{ fecha: '2026-10-01', autor: 'Ana', texto: 'Nota' }] }).getNumberOfPages();
    expect(con).toBe(sin + 1);
  });

  it('genera el Word con la plantilla sin fallar, con y sin datos', async () => {
    const conNotas = { ...historia, bitacora: [{ fecha: '2026-10-01', autor: 'Ana', texto: 'Nota' }] };
    expect((await Packer.toBuffer(construirDocumento(conNotas))).byteLength).toBeGreaterThan(1000);
    expect((await Packer.toBuffer(construirDocumento({}))).byteLength).toBeGreaterThan(1000);
  });
});
