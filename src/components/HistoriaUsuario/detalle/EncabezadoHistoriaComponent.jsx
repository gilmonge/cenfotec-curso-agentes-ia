import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { TituloPaginaComponent } from '../../Comun/TituloPaginaComponent';
import { BotonComponent } from '../../Comun/BotonComponent';
import { InsigniaEstadoComponent } from '../../Comun/InsigniaEstadoComponent';
import { etiquetaHistoria } from '../../../utils/plantillaHu';
import { etiquetaRevision, numeroRevision } from '../../../utils/revisiones';
import { SIN_IDENTIFICAR } from '../../../utils/usuarioActual';

// Título y estado de la HU. El detalle es solo de consulta: lo único que ofrece es Volver; las acciones (Editar, Solicitar cambio, Descargar) se usan desde el listado.
export const EncabezadoHistoriaComponent = ({ story, onVolver }) => (
  <>
    <TituloPaginaComponent
      title={`${etiquetaHistoria(story)}${numeroRevision(story) > 1 ? ` · ${etiquetaRevision(story)}` : ''} — ${story.title}`}
      description={`Creada por ${story.createdBy || SIN_IDENTIFICAR} el ${story.createdAt} | Modificada por ${story.updatedBy || story.createdBy || SIN_IDENTIFICAR} el ${story.updatedAt || story.createdAt} | Tipo: ${story.type || 'General'}`}
      action={
        <div className="page-title__actions">
          <BotonComponent variant="secondary" icon={ArrowLeft} onClick={onVolver}>Volver</BotonComponent>
        </div>
      }
    />
    <div className="detalle-estado">
      <InsigniaEstadoComponent status={story.status} />
      <span>Última actualización: <strong>{story.updatedAt}</strong></span>
      <span className="detalle-estado__fuente">Fuente: <strong>{story.infoType || 'Minuta'}</strong></span>
    </div>
  </>
);
