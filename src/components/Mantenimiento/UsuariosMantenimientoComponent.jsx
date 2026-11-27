import React, { useCallback, useEffect, useState } from 'react';
import { Search, UserPlus, Pencil } from 'lucide-react';
import { CampoTextoComponent } from '../Comun/CampoTextoComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { mantenimientoApi } from '../../services/seguridadApi';
import { useSesion } from '../Sesion/SesionContext';
import { ACCION } from '../../config/acciones';

const NUEVO = Object.freeze({ id: '', usuario: '', nombre: '', clave: '', activo: true, roles: [] });

// Buscar usuarios y asignarles o quitarles roles.
export const UsuariosMantenimientoComponent = ({ listaRol, alCambiar }) => {
  const { puede, usuario: actual } = useSesion();
  const editable = puede(ACCION.USUARIO_ADMINISTRAR);
  const [busqueda, setBusqueda] = useState('');
  const [listaUsuario, setListaUsuario] = useState([]);
  const [edicion, setEdicion] = useState(null);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const [guardando, setGuardando] = useState(false);

  const buscar = useCallback(async (texto) => {
    try {
      setListaUsuario(await mantenimientoApi.listarUsuario(texto));
    } catch (fallo) {
      console.error('No se pudieron buscar los usuarios:', fallo);
      setError(fallo?.message || 'No se pudieron buscar los usuarios.');
    }
  }, []);

  useEffect(() => {
    const espera = setTimeout(() => buscar(busqueda.trim()), 250);
    return () => clearTimeout(espera);
  }, [busqueda, buscar]);

  const abrir = (usuario) => {
    setError('');
    setAviso('');
    setEdicion(usuario
      ? { ...usuario, clave: '', roles: usuario.roles.map((rol) => rol.id) }
      : { ...NUEVO });
  };

  const alternarRol = (rolId) => setEdicion((actualEdicion) => ({
    ...actualEdicion,
    roles: actualEdicion.roles.includes(rolId)
      ? actualEdicion.roles.filter((id) => id !== rolId)
      : [...actualEdicion.roles, rolId],
  }));

  const guardar = async (evento) => {
    evento.preventDefault();
    const esNuevo = !edicion.id;
    if (!edicion.nombre.trim() || (esNuevo && !edicion.usuario.trim())) {
      setError('Escriba el nombre y el usuario.');
      return;
    }
    if ((esNuevo || edicion.clave) && edicion.clave.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    setGuardando(true);
    setError('');
    try {
      if (esNuevo) {
        await mantenimientoApi.crearUsuario({
          usuario: edicion.usuario.trim(), nombre: edicion.nombre.trim(), clave: edicion.clave, roles: edicion.roles,
        });
      } else {
        await mantenimientoApi.actualizarUsuario(edicion.id, {
          nombre: edicion.nombre.trim(), activo: edicion.activo, roles: edicion.roles,
          ...(edicion.clave ? { clave: edicion.clave } : {}),
        });
      }
      setAviso(esNuevo ? `Usuario «${edicion.nombre.trim()}» creado.` : 'Cambios guardados.');
      setEdicion(null);
      await buscar(busqueda.trim());
      alCambiar();
    } catch (fallo) {
      console.error('No se pudo guardar el usuario:', fallo);
      setError(fallo?.message || 'No se pudo guardar el usuario.');
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="mantenimiento">
      <div className="mantenimiento__barra">
        <div className="mantenimiento__busqueda">
          <Search size={16} aria-hidden="true" />
          <input
            className="input"
            aria-label="Buscar usuario por nombre o usuario"
            placeholder="Buscar por nombre o usuario"
            value={busqueda}
            onChange={(evento) => setBusqueda(evento.target.value)}
          />
        </div>
        {editable && <BotonComponent variant="secondary" icon={UserPlus} onClick={() => abrir(null)}>Nuevo usuario</BotonComponent>}
      </div>

      {aviso && <AlertaComponent type="success" title="Listo">{aviso}</AlertaComponent>}
      {error && !edicion && <AlertaComponent type="danger" title="No se pudo completar">{error}</AlertaComponent>}

      {edicion && (
        <form className="card mantenimiento__editor" onSubmit={guardar} aria-label={edicion.id ? 'Editar usuario' : 'Nuevo usuario'}>
          <h3 className="card__title">{edicion.id ? `Editar a ${edicion.nombre}` : 'Nuevo usuario'}</h3>
          <div className="mantenimiento__campos">
            <CampoTextoComponent
              label="Nombre"
              id="mant-usuario-nombre"
              required
              maxLength={120}
              value={edicion.nombre}
              onChange={(evento) => setEdicion({ ...edicion, nombre: evento.target.value })}
            />
            <CampoTextoComponent
              label="Usuario"
              id="mant-usuario-usuario"
              required={!edicion.id}
              disabled={Boolean(edicion.id)}
              maxLength={60}
              autoComplete="off"
              hint={edicion.id ? 'El usuario no se cambia.' : 'Letras, números, punto o guion. Ej. ana.mora'}
              value={edicion.usuario}
              onChange={(evento) => setEdicion({ ...edicion, usuario: evento.target.value })}
            />
            <CampoTextoComponent
              label={edicion.id ? 'Nueva contraseña' : 'Contraseña'}
              id="mant-usuario-clave"
              type="password"
              required={!edicion.id}
              autoComplete="new-password"
              maxLength={200}
              hint={edicion.id ? 'Déjela en blanco para no cambiarla.' : 'Al menos 8 caracteres.'}
              value={edicion.clave}
              onChange={(evento) => setEdicion({ ...edicion, clave: evento.target.value })}
            />
          </div>
          <fieldset className="mantenimiento__grupo">
            <legend>Roles</legend>
            {listaRol.map((rol) => (
              <label key={rol.id} className="mantenimiento__casilla">
                <input type="checkbox" checked={edicion.roles.includes(rol.id)} onChange={() => alternarRol(rol.id)} />
                <span>{rol.nombre}</span>
                {rol.descripcion && <span className="form-hint">{rol.descripcion}</span>}
              </label>
            ))}
          </fieldset>
          {edicion.id && edicion.id !== actual?.id && (
            <label className="mantenimiento__casilla">
              <input type="checkbox" checked={edicion.activo} onChange={(evento) => setEdicion({ ...edicion, activo: evento.target.checked })} />
              <span>Usuario activo (si se desactiva, no puede ingresar)</span>
            </label>
          )}
          {error && <AlertaComponent type="danger" title="No se pudo guardar">{error}</AlertaComponent>}
          <div className="mantenimiento__botones">
            <BotonComponent variant="outline" onClick={() => setEdicion(null)} disabled={guardando}>Cancelar</BotonComponent>
            <BotonComponent type="submit" variant="primary" disabled={guardando}>{guardando ? 'Guardando…' : 'Guardar'}</BotonComponent>
          </div>
        </form>
      )}

      <div className="mantenimiento__tabla-envoltura">
        <table className="mantenimiento__tabla">
          <thead>
            <tr><th>Nombre</th><th>Usuario</th><th>Roles</th><th>Estado</th>{editable && <th><span className="sr-only">Editar</span></th>}</tr>
          </thead>
          <tbody>
            {listaUsuario.length === 0 && (
              <tr><td colSpan={editable ? 5 : 4} className="form-hint">No hay usuarios que coincidan con la búsqueda.</td></tr>
            )}
            {listaUsuario.map((item) => (
              <tr key={item.id}>
                <td>{item.nombre}</td>
                <td className="mantenimiento__secundario">{item.usuario}</td>
                <td>
                  {item.roles.length
                    ? item.roles.map((rol) => <span key={rol.id} className="mantenimiento__chip">{rol.nombre}</span>)
                    : <span className="form-hint">Sin roles</span>}
                </td>
                <td>{item.activo ? 'Activo' : 'Inactivo'}</td>
                {editable && (
                  <td>
                    <button type="button" className="btn btn--outline btn--sm" onClick={() => abrir(item)} aria-label={`Editar a ${item.nombre}`}>
                      <Pencil size={14} /> Editar
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
