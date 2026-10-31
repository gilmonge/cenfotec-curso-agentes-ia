import React from 'react';
import { RefreshCw } from 'lucide-react';
import { AlertaComponent } from '../../Comun/AlertaComponent';
import { BotonComponent } from '../../Comun/BotonComponent';

// Avisos que deben verse en cualquier sección: no se esconden al cambiar de pestaña.
export const AvisosHistoriaComponent = ({ story, onReanalizar }) => {
  if (!story.analisisDesactualizado || story.status === 'aprobada') return null;
  return (
    <AlertaComponent type="warning" title="Análisis desactualizado">
      {story.respuestasNuevas
        ? 'Se agregaron o cambiaron respuestas de Negocio después del último análisis: hay que volver a analizar para que el agente las tome en cuenta.'
        : 'El requerimiento cambió después del último análisis; el análisis, las preguntas y los criterios ya no reflejan la información editada.'}
      <div style={{ marginTop: '0.75rem' }}>
        <BotonComponent variant="primary" size="sm" icon={RefreshCw} onClick={onReanalizar}>Volver a analizar</BotonComponent>
      </div>
    </AlertaComponent>
  );
};
