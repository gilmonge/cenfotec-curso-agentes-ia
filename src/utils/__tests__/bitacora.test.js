import { describe, expect, it } from 'vitest';
import {
  bitacoraConEstado, bitacoraConNota, bitacoraDelFlujo, filasBitacora, leerBitacora, textosBitacora,
} from '../bitacora';

describe('bitácora de seguimiento de la HU', () => {
  it('una HU antigua con un solo texto de observaciones lo muestra como nota inicial', () => {
    const lista = leerBitacora({ observations: ' Tener en cuenta el límite ', createdAt: '2026-10-01', createdBy: 'Ana' });
    expect(lista).toEqual([{ fecha: '2026-10-01', autor: 'Ana', tipo: 'nota', texto: 'Tener en cuenta el límite' }]);
  });

  it('agrega la nota nueva con fecha y autor sin borrar las anteriores', () => {
    const historia = { bitacora: [{ fecha: '2026-10-01', autor: 'Ana', texto: 'Primera' }] };
    const lista = bitacoraConNota(historia, '  Segunda ', { fecha: '2026-10-02', autor: 'Luis' });
    expect(lista).toEqual([
      { fecha: '2026-10-01', autor: 'Ana', texto: 'Primera' },
      { fecha: '2026-10-02', autor: 'Luis', tipo: 'nota', texto: 'Segunda' },
    ]);
  });

  it('una nota vacía no cambia la bitácora y una HU sin notas devuelve lista vacía', () => {
    expect(bitacoraConNota({ bitacora: [] }, '   ')).toEqual([]);
    expect(leerBitacora({})).toEqual([]);
    expect(bitacoraConNota(null, 'Primera', { fecha: '2026-10-02', autor: 'Ana' })).toHaveLength(1);
  });

  it('para los documentos entrega solo los textos', () => {
    expect(textosBitacora({ bitacora: [{ fecha: 'x', autor: 'y', texto: 'A' }, { fecha: 'x', autor: 'y', texto: 'B' }] })).toEqual(['A', 'B']);
  });

  it('el flujo deja decisiones, supuestos, dependencias, pendientes, devoluciones y la nota; no el control de calidad', () => {
    const lista = bitacoraDelFlujo({
      impact_decisions: [{ pregunta: '¿La carga usa el mismo formato?', respuesta: 'Sí.' }],
      analyst: { supuesto_validar_po: ['Se supone que aplica a todos los clientes.'] },
      notas_hu: [
        { tipo: 'dependencia', texto: 'Servicio al Cliente avisará el cambio.' },
        { tipo: 'pendiente_tecnico', texto: 'Confirmar otros reportes.' },
      ],
      devoluciones_po: [{ fecha: '2026-11-25', destino: 'redactor', motivo: 'Quitar el criterio general.', atencion: 'Se quitó.' }],
      ultima_revision: ['No detecté defectos.'],
    }, { fecha: '2026-11-26', persona: 'Yuvania', notaAprobacion: 'Revisar con Desarrollo.' });

    expect(lista.map((nota) => nota.tipo)).toEqual(['decision', 'supuesto', 'dependencia', 'pendiente_tecnico', 'devolucion', 'nota']);
    expect(lista[0]).toMatchObject({ autor: 'Negocio', texto: '¿La carga usa el mismo formato?\nDecisión: Sí.' });
    expect(lista[2]).toMatchObject({ autor: 'Redactor-Revisor', estado: 'abierto' });
    expect(lista[4]).toMatchObject({ fecha: '2026-11-25', texto: 'Motivo: Quitar el criterio general.\nCómo se atendió: Se quitó.' });
    expect(JSON.stringify(lista)).not.toContain('No detecté defectos');
  });

  it('solo las dependencias y los pendientes técnicos cambian de estado, y nada más de la entrada', () => {
    const historia = { bitacora: [
      { fecha: '2026-11-26', autor: 'Redactor-Revisor', tipo: 'dependencia', texto: 'Avisar.', estado: 'abierto' },
      { fecha: '2026-11-26', autor: 'Yuvania', tipo: 'decision', texto: 'Sí.' },
    ] };
    const cambiada = bitacoraConEstado(historia, 0, 'atendido');
    expect(cambiada[0]).toEqual({ ...historia.bitacora[0], estado: 'atendido' });
    expect(bitacoraConEstado(historia, 1, 'atendido')[1]).toEqual(historia.bitacora[1]);
    expect(bitacoraConEstado(historia, 0, 'otro')[0].estado).toBe('abierto');
  });

  it('para los documentos entrega una fila con fecha, tipo, origen, comentario y estado', () => {
    expect(filasBitacora({ bitacora: [
      { fecha: '2026-11-26', autor: 'Redactor-Revisor', tipo: 'pendiente_tecnico', texto: 'Confirmar.', estado: 'atendido' },
      { fecha: '2026-11-26', autor: 'Ana', texto: 'Nota antigua sin tipo' },
    ] })).toEqual([
      { fecha: '2026-11-26', tipo: 'Pendiente técnico', origen: 'Redactor-Revisor', comentario: 'Confirmar.', estado: 'Atendido' },
      { fecha: '2026-11-26', tipo: 'Nota', origen: 'Ana', comentario: 'Nota antigua sin tipo', estado: '' },
    ]);
  });
});
