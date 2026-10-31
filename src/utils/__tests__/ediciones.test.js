import { describe, expect, it } from 'vitest';
import { camposEditados, registrarEdicion } from '../ediciones';
import { accionesDisponibles } from '../accionesHistoria';

const base = {
  title: 'Consulta de reclamos',
  userStory: { asA: 'Ejecutivo', iWant: 'consultar', soThat: 'atender' },
  acceptanceCriteria: [{ id: 'a', given: 'x', when: 'y', then: 'z' }],
  system: 'Reclamos', codigoHu: 'RECL', requester: 'Servicio', number: 'HU-RECL-001', benefits: ['Menos errores'], signers: {},
};

describe('ediciones de una HU aprobada', () => {
  it('sin cambios no hay campos editados', () => {
    expect(camposEditados(base, { ...base })).toEqual([]);
  });

  it('nombra en lenguaje claro lo que cambió', () => {
    const nuevo = { ...base, userStory: { ...base.userStory, asA: 'Ejecutivo de Servicio' }, benefits: ['Menos errores', 'Más rápido'], notaNueva: 'Ojo con el rol' };
    expect(camposEditados(base, nuevo)).toEqual(['Historia (Como / Quiero / Para)', 'Datos de la plantilla', 'Observaciones']);
  });

  it('el registro agrega quién, cuándo y qué campos sin borrar los anteriores', () => {
    const lista = registrarEdicion({ ediciones: [{ fecha: 'a', autor: 'x', campos: ['Título'] }] }, ['Criterios de aceptación'], { fecha: '2026-10-31T10:00:00Z', autor: 'Ana' });
    expect(lista).toHaveLength(2);
    expect(lista[1]).toEqual({ fecha: '2026-10-31T10:00:00Z', autor: 'Ana', campos: ['Criterios de aceptación'] });
  });
});

describe('acciones disponibles de una HU', () => {
  it('antes de aprobarse no hay Solicitar cambio y Editar siempre está', () => {
    expect(accionesDisponibles({ status: 'revisada' })).toEqual(['ver', 'editar', 'descargar', 'eliminar']);
  });

  it('una HU aprobada suma Solicitar cambio', () => {
    expect(accionesDisponibles({ status: 'aprobada' })).toEqual(['ver', 'editar', 'solicitar-cambio', 'descargar', 'eliminar']);
  });

  it('se pueden omitir acciones (el detalle no repite Ver ni Eliminar)', () => {
    expect(accionesDisponibles({ status: 'aprobada' }, { omitir: ['ver', 'eliminar'] })).toEqual(['editar', 'solicitar-cambio', 'descargar']);
  });
});
