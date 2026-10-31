import React from 'react';

// Flujo del diagrama de definición del proyecto: antes y después del grooming.
// "state" indica qué parte funciona hoy: real, manual (lo hace una persona) o pendiente.
const STATE_LABEL = {
  real: 'Funciona',
  manual: 'Manual',
  pending: 'No implementado',
};

const BEFORE = [
  { title: 'Analista ingresa requerimiento', detail: 'Minuta, correo o incidente', kind: 'human', where: 'Paso 1' },
  { title: 'Agente Analista', detail: 'Clasifica y genera preguntas', kind: 'agent', state: 'real', where: 'Paso 2' },
  { title: 'Analista valida preguntas', detail: 'Negocio responde', kind: 'human', where: 'Paso 3' },
  { title: '¿Quedan vacíos?', detail: 'Si quedan, vuelve al Agente Analista', kind: 'human', where: 'Paso 3' },
  { title: 'Agente Redactor-Revisor', detail: 'Redacta, revisa y corrige. Hoy la persona edita un borrador', kind: 'agent', state: 'pending', where: 'Paso 4' },
  { title: 'Agente Asesor Técnico', detail: 'Impacto en código', kind: 'agent', state: 'pending' },
  { title: 'Product Owner aprueba', detail: 'HU lista para grooming', kind: 'human', where: 'Paso 5' },
  { title: 'Repositorio de HU', detail: 'Guarda la HU aprobada (memoria de largo plazo)', kind: 'component', state: 'real', where: 'Paso 5' },
];

const AFTER = [
  { title: 'Grooming y sprint', detail: 'Llega una solicitud de cambio', kind: 'human' },
  { title: 'Agente Gestor de Cambios', detail: 'Compara con la HU aprobada. Hoy el Product Owner clasifica a mano', kind: 'agent', state: 'pending' },
  { title: 'Product Owner decide', detail: 'Editar para corregir en el lugar, o Solicitar cambio si cambia el alcance (nueva revisión de la misma HU con nuevo análisis)', kind: 'human', where: 'Listado de HU' },
  { title: 'Registra y aprende', detail: 'Causa raíz y lección', kind: 'agent', state: 'manual', where: 'Listado de HU' },
  { title: 'Checklist de vacíos', detail: 'Mejora con aprobación del Product Owner', kind: 'component', state: 'real', where: 'Lecciones' },
];

const KIND_STYLE = {
  agent: { border: 'var(--color-secondary-text)', background: 'var(--color-secondary-light)', label: 'Agente' },
  component: { border: 'var(--color-success-text)', background: 'var(--color-success-light)', label: 'Componente' },
  human: { border: 'var(--color-border-dark)', background: 'var(--color-surface)', label: 'Paso humano' },
};

function Node({ node }) {
  const style = KIND_STYLE[node.kind];
  return (
    <li
      style={{
        listStyle: 'none',
        border: `1px solid ${style.border}`,
        borderLeft: `5px solid ${style.border}`,
        background: style.background,
        borderRadius: '8px',
        padding: '0.6rem 0.85rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
        <strong style={{ color: 'var(--color-text-primary)' }}>{node.title}</strong>
        <span style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
          {style.label}
          {node.state ? ` · ${STATE_LABEL[node.state]}` : ''}
          {node.where ? ` · ${node.where}` : ''}
        </span>
      </div>
      <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>{node.detail}</div>
    </li>
  );
}

function Phase({ title, nodes }) {
  return (
    <section aria-label={title} style={{ marginBottom: '1.25rem' }}>
      <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-secondary-text)', marginBottom: '0.6rem' }}>{title}</h4>
      <ol style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: 0, margin: 0 }}>
        {nodes.map((node) => <Node key={node.title} node={node} />)}
      </ol>
    </section>
  );
}

export const FlujoGroomingComponent = () => (
  <div>
    <Phase title="Antes del grooming" nodes={BEFORE} />
    <Phase title="Después del grooming" nodes={AFTER} />
  </div>
);
