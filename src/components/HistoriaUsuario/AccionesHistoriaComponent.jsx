import React from 'react';
import { Eye, GitPullRequest, Pencil, Trash2 } from 'lucide-react';
import { BotonIconoComponent } from '../Comun/BotonIconoComponent';
import { MenuDescargaComponent } from './MenuDescargaComponent';
import { ACCION, accionesDisponibles } from '../../utils/accionesHistoria';
import { etiquetaHistoria } from '../../utils/plantillaHu';
import { ACCION as PERMISO } from '../../config/acciones';
import { useSesion } from '../Sesion/SesionContext';

// Íconos de acción de una HU. Decide qué mostrar según el estado y avisa con callbacks lo que se eligió;
// no navega ni modifica nada por sí mismo.
export const AccionesHistoriaComponent = ({ story, onVer, onEditar, onSolicitarCambio, onEliminar, omitir = [] }) => {
  const { puede } = useSesion();
  const disponibles = accionesDisponibles(story, { omitir });
  // Además del estado de la HU, cada botón pide la acción del rol de la persona.
  const permiso = {
    [ACCION.EDITAR]: PERMISO.HISTORIA_EDITAR,
    [ACCION.SOLICITAR_CAMBIO]: PERMISO.CAMBIO_SOLICITAR,
    [ACCION.ELIMINAR]: PERMISO.HISTORIA_ELIMINAR,
  };
  const hay = (accion) => disponibles.includes(accion) && puede(permiso[accion]);
  return (
    <div className="acciones-historia">
      {hay(ACCION.VER) && <BotonIconoComponent icon={Eye} etiqueta="Ver" onClick={() => onVer(story)} />}
      {hay(ACCION.EDITAR) && <BotonIconoComponent icon={Pencil} etiqueta="Editar" onClick={() => onEditar(story)} />}
      {hay(ACCION.SOLICITAR_CAMBIO) && <BotonIconoComponent icon={GitPullRequest} etiqueta="Solicitar cambio" onClick={() => onSolicitarCambio(story)} />}
      {hay(ACCION.DESCARGAR) && <MenuDescargaComponent story={story} />}
      {hay(ACCION.ELIMINAR) && onEliminar && (
        <BotonIconoComponent icon={Trash2} variant="danger" etiqueta={`Eliminar historia ${etiquetaHistoria(story)}`} onClick={() => onEliminar(story)} />
      )}
    </div>
  );
};
