import React, { useCallback, useEffect, useState } from 'react';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { SeccionesConPestanasComponent } from '../HistoriaUsuario/detalle/SeccionesConPestanasComponent';
import { mantenimientoApi } from '../../services/seguridadApi';
import { useSesion } from '../Sesion/SesionContext';
import { UsuariosMantenimientoComponent } from './UsuariosMantenimientoComponent';
import { RolesMantenimientoComponent } from './RolesMantenimientoComponent';

// Mantenimiento: a los usuarios se les asignan o quitan roles y a los roles se les asignan o quitan acciones.
// Las acciones salen del catálogo del backend: una acción nueva aparece aquí sin tocar esta pantalla.
export const MantenimientoComponent = () => {
  const { seguridad } = useSesion();
  const [listaRol, setListaRol] = useState([]);
  const [listaAccion, setListaAccion] = useState([]);
  const [error, setError] = useState('');

  const cargarRol = useCallback(async () => {
    try {
      setListaRol(await mantenimientoApi.listarRol());
    } catch (fallo) {
      console.error('No se pudieron cargar los roles:', fallo);
      setError(fallo?.message || 'No se pudieron cargar los roles.');
    }
  }, []);

  useEffect(() => {
    if (!seguridad) return;
    cargarRol();
    mantenimientoApi.listarAccion().then(setListaAccion).catch((fallo) => {
      console.error('No se pudo cargar el catálogo de acciones:', fallo);
      setError(fallo?.message || 'No se pudo cargar el catálogo de acciones.');
    });
  }, [seguridad, cargarRol]);

  if (!seguridad) {
    return (
      <div>
        <TituloPaginaComponent title="Mantenimiento" description="Usuarios, roles y acciones." />
        <AlertaComponent type="info" title="La seguridad no está activa en este ambiente">
          En desarrollo local (sin ACCESO_USUARIO y ACCESO_CLAVE) todas las acciones están permitidas y no hay usuarios.
        </AlertaComponent>
      </div>
    );
  }

  const secciones = [
    {
      id: 'usuarios',
      titulo: 'Usuarios',
      contenido: <UsuariosMantenimientoComponent listaRol={listaRol} alCambiar={cargarRol} />,
    },
    {
      id: 'roles',
      titulo: 'Roles',
      contador: listaRol.length || null,
      contenido: <RolesMantenimientoComponent listaRol={listaRol} listaAccion={listaAccion} alCambiar={cargarRol} />,
    },
  ];

  return (
    <div>
      <TituloPaginaComponent
        title="Mantenimiento"
        description="Asigne roles a los usuarios y acciones a los roles. Un cambio aplica de inmediato."
      />
      {error && <AlertaComponent type="danger" title="No se pudo cargar">{error}</AlertaComponent>}
      <SeccionesConPestanasComponent etiqueta="Secciones de mantenimiento" inicial="usuarios" secciones={secciones} />
    </div>
  );
};
