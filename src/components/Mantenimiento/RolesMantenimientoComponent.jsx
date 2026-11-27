import React, { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { CampoTextoComponent } from '../Comun/CampoTextoComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { mantenimientoApi } from '../../services/seguridadApi';
import { useSesion } from '../Sesion/SesionContext';
import { useConfirmacion } from '../Comun/ConfirmacionComponent';
import { ACCION } from '../../config/acciones';

const NUEVO = Object.freeze({ id: '', nombre: '', descripcion: '', acciones: [] });

// Acciones del catálogo agrupadas por módulo, en el orden en que llegan.
const agruparPorModulo = (listaAccion) => listaAccion.reduce((grupos, accion) => {
  const grupo = grupos.find((item) => item.modulo === accion.modulo);
  if (grupo) grupo.lista.push(accion);
  else grupos.push({ modulo: accion.modulo, lista: [accion] });
  return grupos;
}, []);

// Elegir un rol y asignarle o quitarle acciones. Solo se muestra el nombre de cada acción.
export const RolesMantenimientoComponent = ({ listaRol, listaAccion, alCambiar }) => {
  const { puede } = useSesion();
  const confirmar = useConfirmacion();
  const editable = puede(ACCION.ROL_ADMINISTRAR);
  const [seleccion, setSeleccion] = useState('');
  const [edicion, setEdicion] = useState(null);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const [guardando, setGuardando] = useState(false);
  const grupos = useMemo(() => agruparPorModulo(listaAccion), [listaAccion]);

  useEffect(() => {
    if (edicion && !edicion.id) return;
    const rol = listaRol.find((item) => item.id === seleccion) ?? listaRol[0];
    if (rol) {
      setSeleccion(rol.id);
      setEdicion({ ...rol });
    }
    // Solo cuando cambia la lista o la selección; la edición en curso no se pisa al escribir.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listaRol, seleccion]);

  const elegir = (rol) => {
    setError('');
    setAviso('');
    setEdicion({ ...rol });
    setSeleccion(rol.id);
  };

  const nuevo = () => {
    setError('');
    setAviso('');
    setSeleccion('');
    setEdicion({ ...NUEVO });
  };

  const alternar = (codigo) => setEdicion((actual) => ({
    ...actual,
    acciones: actual.acciones.includes(codigo)
      ? actual.acciones.filter((item) => item !== codigo)
      : [...actual.acciones, codigo],
  }));

  const alternarModulo = (grupo, marcar) => setEdicion((actual) => {
    const codigos = grupo.lista.map((accion) => accion.codigo);
    const resto = actual.acciones.filter((codigo) => !codigos.includes(codigo));
    return { ...actual, acciones: marcar ? [...resto, ...codigos] : resto };
  });

  const guardar = async (evento) => {
    evento.preventDefault();
    if (!edicion.nombre.trim()) {
      setError('Escriba el nombre del rol.');
      return;
    }
    setGuardando(true);
    setError('');
    try {
      const datos = { nombre: edicion.nombre.trim(), descripcion: edicion.descripcion.trim(), acciones: edicion.acciones };
      const guardado = edicion.id
        ? await mantenimientoApi.actualizarRol(edicion.id, datos)
        : await mantenimientoApi.crearRol(datos);
      setAviso(edicion.id ? 'Cambios guardados. Aplican de inmediato a los usuarios con este rol.' : `Rol «${guardado.nombre}» creado.`);
      setEdicion({ ...guardado });
      setSeleccion(guardado.id);
      await alCambiar();
    } catch (fallo) {
      console.error('No se pudo guardar el rol:', fallo);
      setError(fallo?.message || 'No se pudo guardar el rol.');
    } finally {
      setGuardando(false);
    }
  };

  const eliminar = async () => {
    const aceptado = await confirmar({
      titulo: 'Eliminar rol',
      mensaje: `Se eliminará el rol «${edicion.nombre}»${edicion.usuarios ? ` y se quitará a ${edicion.usuarios} usuario(s)` : ''}.`,
      textoConfirmar: 'Eliminar',
      textoCancelar: 'Conservar',
      peligro: true,
    });
    if (!aceptado) return;
    try {
      await mantenimientoApi.eliminarRol(edicion.id);
      setAviso(`Rol «${edicion.nombre}» eliminado.`);
      setEdicion(null);
      setSeleccion('');
      await alCambiar();
    } catch (fallo) {
      console.error('No se pudo eliminar el rol:', fallo);
      setError(fallo?.message || 'No se pudo eliminar el rol.');
    }
  };

  return (
    <div className="mantenimiento mantenimiento--roles">
      <div className="card mantenimiento__lista-rol">
        <ul aria-label="Roles">
          {listaRol.map((rol) => (
            <li key={rol.id}>
              <button
                type="button"
                className={`mantenimiento__rol ${rol.id === edicion?.id ? 'mantenimiento__rol--activo' : ''}`}
                aria-pressed={rol.id === edicion?.id}
                onClick={() => elegir(rol)}
              >
                <span>{rol.nombre}</span>
                <span className="form-hint">{rol.usuarios} usuario(s)</span>
              </button>
            </li>
          ))}
        </ul>
        {editable && <BotonComponent variant="secondary" icon={Plus} onClick={nuevo} className="mantenimiento__nuevo">Nuevo rol</BotonComponent>}
      </div>

      {edicion && (
        <form className="card mantenimiento__editor" onSubmit={guardar} aria-label={edicion.id ? `Acciones de ${edicion.nombre}` : 'Nuevo rol'}>
          {aviso && <AlertaComponent type="success" title="Listo">{aviso}</AlertaComponent>}
          <div className="mantenimiento__campos">
            <CampoTextoComponent
              label="Nombre del rol"
              id="mant-rol-nombre"
              required
              disabled={!editable}
              maxLength={80}
              value={edicion.nombre}
              onChange={(evento) => setEdicion({ ...edicion, nombre: evento.target.value })}
            />
            <CampoTextoComponent
              label="Descripción"
              id="mant-rol-descripcion"
              disabled={!editable}
              maxLength={300}
              value={edicion.descripcion}
              onChange={(evento) => setEdicion({ ...edicion, descripcion: evento.target.value })}
            />
          </div>
          {grupos.map((grupo) => {
            const marcadas = grupo.lista.filter((accion) => edicion.acciones.includes(accion.codigo)).length;
            return (
              <fieldset key={grupo.modulo} className="mantenimiento__grupo">
                <legend>
                  {grupo.modulo}
                  {editable && (
                    <button
                      type="button"
                      className="mantenimiento__todas"
                      onClick={() => alternarModulo(grupo, marcadas < grupo.lista.length)}
                    >
                      {marcadas < grupo.lista.length ? 'Marcar todas' : 'Quitar todas'}
                    </button>
                  )}
                </legend>
                {grupo.lista.map((accion) => (
                  <label key={accion.codigo} className="mantenimiento__casilla">
                    <input
                      type="checkbox"
                      disabled={!editable}
                      checked={edicion.acciones.includes(accion.codigo)}
                      onChange={() => alternar(accion.codigo)}
                    />
                    <span>{accion.nombre}</span>
                  </label>
                ))}
              </fieldset>
            );
          })}
          {error && <AlertaComponent type="danger" title="No se pudo guardar">{error}</AlertaComponent>}
          {editable && (
            <div className="mantenimiento__botones">
              {edicion.id && (
                <BotonComponent variant="danger" icon={Trash2} onClick={eliminar} disabled={guardando}>Eliminar rol</BotonComponent>
              )}
              <BotonComponent type="submit" variant="primary" disabled={guardando}>{guardando ? 'Guardando…' : 'Guardar'}</BotonComponent>
            </div>
          )}
        </form>
      )}
    </div>
  );
};
