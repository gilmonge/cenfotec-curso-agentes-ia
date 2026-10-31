import { describe, expect, it } from 'vitest';
import JSZip from 'jszip';
import { Packer } from 'docx';
import { PENDIENTE, construirReanalisis, normalizarCodigoHu, numeroSugerido, requerimientoCambio } from '../plantillaHu';
import { conEtiqueta, construirDocumento, nombreArchivo } from '../exportarWord';

describe('numeroSugerido', () => {
  it('normaliza el código de HU y empieza en 001', () => {
    expect(normalizarCodigoHu(' pol of ')).toBe('POL-OF');
    expect(numeroSugerido('pol-of', [])).toBe('HU-POL-OF-001');
  });

  it('continúa el último consecutivo del mismo área', () => {
    const lista = [{ number: 'HU-POL-OF-002' }, { number: 'HU-POL-OF-005' }, { number: 'HU-GEN-COM-009' }];
    expect(numeroSugerido('POL-OF', lista)).toBe('HU-POL-OF-006');
    expect(numeroSugerido('GEN-COM', lista)).toBe('HU-GEN-COM-010');
  });

  it('devuelve vacío sin área', () => {
    expect(numeroSugerido('  ', [])).toBe('');
  });
});

describe('conEtiqueta', () => {
  it('no duplica la etiqueta existente', () => {
    expect(conEtiqueta('Dado que el usuario guarda', 'Dado que')).toBe('Dado que: el usuario guarda');
    expect(conEtiqueta('el usuario guarda', 'Cuando')).toBe('Cuando: el usuario guarda');
  });
});

describe('exportación a Word', () => {
  const historia = {
    id: 'HU-100',
    number: 'HU-POL-OF-001',
    title: 'Estado de coberturas',
    requestType: 'Requerimiento',
    system: 'Sistema de pólizas',
    codigoHu: 'POL-OF',
    userStory: { asA: 'Usuario del sistema', iWant: 'ver el estado', soThat: 'conocerlo rápido' },
    benefits: ['Menos errores', '  ', 'Más control'],
    signers: { elaborado: 'Persona Uno' },
    acceptanceCriteria: [{ given: 'Dado que hay coberturas', when: 'Cuando se consulta', then: 'Entonces se muestra el estado' }],
  };

  const leerTexto = async (doc) => {
    const buffer = await Packer.toBuffer(doc);
    const zip = await JSZip.loadAsync(buffer);
    return (await zip.file('word/document.xml').async('string')).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  };

  it('incluye las secciones de la plantilla y marca lo pendiente', async () => {
    const texto = await leerTexto(construirDocumento(historia));
    ['Referencias', 'Priorización del negocio', 'Revisión de Desarrollo', 'Beneficios esperados',
      'Firmas de Aprobación', 'Criterios de Aceptación', 'HU-POL-OF-001 Estado de coberturas',
      'Menos errores', 'Más control', 'Persona Uno', 'Dado que:', 'Entonces:'].forEach((fragmento) => {
      expect(texto).toContain(fragmento);
    });
    expect(texto).toContain(PENDIENTE);
  });

  it('genera un documento válido aun con una historia casi vacía', async () => {
    const texto = await leerTexto(construirDocumento({ id: 'HU-1', title: 'Solo título' }));
    expect(texto).toContain(PENDIENTE);
  });

  it('nombra el archivo con el número de la HU', () => {
    expect(nombreArchivo(historia)).toBe('HU-POL-OF-001.docx');
  });
});

describe('re-análisis de borradores', () => {
  it('detecta cambios solo en el requerimiento', () => {
    const base = { title: 'A', infoType: 'Minuta', description: 'x' };
    expect(requerimientoCambio(base, { ...base, system: 'otro' })).toBe(false);
    expect(requerimientoCambio(base, { ...base, description: 'y' })).toBe(true);
  });

  it('construye el prefill con el código de HU', () => {
    expect(construirReanalisis({ title: 'A', area: 'POL' }).codigoHu).toBe('POL');
  });
});

describe('identificador y código legible de la historia', () => {
  it('genera GUID v4 aleatorios y únicos', async () => {
    const { generateStoryId } = await import('../storage');
    const a = generateStoryId();
    const b = generateStoryId();
    expect(a).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(a).not.toBe(b);
  });

  it('muestra el código de la plantilla; el GUID nunca se usa como código', async () => {
    const { etiquetaHistoria } = await import('../plantillaHu');
    const id = '3f0f5f7e-7d8a-4d3e-9f7a-1a2b3c4d5e6f';
    expect(etiquetaHistoria({ id, number: 'HU-ABC-001' })).toBe('HU-ABC-001');
    expect(etiquetaHistoria({ id })).toBe('Sin código');
    expect(etiquetaHistoria({ id })).not.toContain('3F0F5F7E');
  });
});
