import React from 'react';
import { useAsistenteHistoria } from './AsistenteHistoriaContext';
import { AlertaComponent } from '../../Comun/AlertaComponent';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { BotonComponent } from '../../Comun/BotonComponent';
import { MarkdownAsistenteComponent } from '../../AsistenteAnalista/MarkdownAsistenteComponent';
import { PlanAgenteComponent } from '../../Comun/PlanAgenteComponent';
import { TarjetaAnalisisComponent } from '../TarjetaAnalisisComponent';
import { TarjetaComponent } from '../../Comun/TarjetaComponent';

// Vista de un paso del asistente. El estado y las acciones vienen del controlador (useCrearHistoria).
export const PasoAnalisisComponent = () => {
  const {
    agentResponse,
    analysis,
    pendingCount,
    requirementName,
    setActiveStep,
    sources,
  } = useAsistenteHistoria();

  return (
    <div>
      <TarjetaComponent
        title="Paso 2 — Análisis del Agente Analista"
        subtitle="Clasificación de la información en conocida, faltante, supuesta y ambigua."
      >
        <AlertaComponent type="info" title="Análisis completado">
          El agente analizó <strong>"{requirementName}"</strong>. Es una propuesta: usted decide qué llevar a Negocio.
        </AlertaComponent>

        <TarjetaAnalisisComponent analysis={analysis} />

        {agentResponse?.respuesta_markdown && (
          <details style={{ marginTop: '1.25rem' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Ver el resumen completo del agente
            </summary>
            <div style={{ marginTop: '0.75rem' }}>
              <MarkdownAsistenteComponent content={agentResponse.respuesta_markdown} />
            </div>
          </details>
        )}

        {sources.length > 0 && (
          <p style={{ marginTop: '1.25rem', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
            <strong>Fuentes consultadas:</strong>{' '}
            {sources.map((source) => `${source.label} (${source.count})`).join(' · ')}.
            {' '}Las fuentes son simuladas o anonimizadas y deben confirmarse con Negocio.
          </p>
        )}
        <PlanAgenteComponent plan={agentResponse?.plan_agente} style={{ marginTop: '1rem' }} />
        {agentResponse?.limitaciones?.length > 0 && (
          <ul style={{ paddingLeft: '1.2rem', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
            {agentResponse.limitaciones.map((item) => <li key={item}>{item}</li>)}
          </ul>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
          <BotonComponent variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(1)}>
            Atrás
          </BotonComponent>
          <BotonComponent variant="primary" icon={ArrowRight} onClick={() => setActiveStep(3)}>
            Preguntas a Negocio ({pendingCount})
          </BotonComponent>
        </div>
      </TarjetaComponent>
    </div>
  );
};
