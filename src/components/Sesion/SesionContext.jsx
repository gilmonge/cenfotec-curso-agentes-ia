import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { sesionApi } from '../../services/seguridadApi';
import { EVENTO_SESION_VENCIDA, guardarToken } from '../../utils/sesion';
import { guardarNombreUsuario } from '../../utils/usuarioActual';

// Sesión por usuario: quién es la persona y qué acciones tiene. Sin seguridad activa en el backend
// (desarrollo local) todo está permitido. Fuera del proveedor (pruebas de componentes) también.
const SIN_SEGURIDAD = Object.freeze({
  cargando: false, seguridad: false, usuario: null, puede: () => true, entrar: async () => null, salir: () => {},
});
const SesionContext = createContext(SIN_SEGURIDAD);

export const SesionProvider = ({ children }) => {
  // En las pruebas la aplicación se muestra de una vez (la sesión responde sin seguridad).
  const [estado, setEstado] = useState({
    cargando: import.meta.env.MODE !== 'test', seguridad: false, usuario: null, error: '',
  });

  const aplicar = useCallback((respuesta) => {
    const usuario = respuesta?.usuario ?? null;
    // El nombre de la sesión es el que queda como «Creado por» y «Modificado por».
    if (usuario?.nombre) guardarNombreUsuario(usuario.nombre);
    setEstado({ cargando: false, seguridad: Boolean(respuesta?.seguridad), usuario, error: '' });
  }, []);

  const cargar = useCallback(async () => {
    try {
      aplicar(await sesionApi.leer());
    } catch (error) {
      console.error('No se pudo leer la sesión:', error);
      // Sin backend (o un backend anterior sin seguridad) la aplicación sigue como antes.
      setEstado({ cargando: false, seguridad: false, usuario: null, error: '' });
    }
  }, [aplicar]);

  useEffect(() => {
    cargar();
    const alVencer = () => {
      guardarToken('');
      setEstado((actual) => ({ ...actual, usuario: null, error: 'Su sesión venció. Inicie sesión de nuevo.' }));
    };
    window.addEventListener(EVENTO_SESION_VENCIDA, alVencer);
    return () => window.removeEventListener(EVENTO_SESION_VENCIDA, alVencer);
  }, [cargar]);

  const entrar = useCallback(async (usuario, clave) => {
    const respuesta = await sesionApi.iniciar(usuario, clave);
    guardarToken(respuesta.token);
    aplicar(respuesta);
    return respuesta.usuario;
  }, [aplicar]);

  const salir = useCallback(() => {
    guardarToken('');
    guardarNombreUsuario('');
    setEstado((actual) => ({ ...actual, usuario: null, error: '' }));
  }, []);

  const valor = useMemo(() => {
    const lista = new Set(estado.usuario?.acciones ?? []);
    // accion: un código o una lista (basta con tener una de ellas).
    const puede = (accion) => !estado.seguridad || !accion
      || (Array.isArray(accion) ? accion.some((codigo) => lista.has(codigo)) : lista.has(accion));
    return { ...estado, puede, entrar, salir };
  }, [estado, entrar, salir]);

  return <SesionContext.Provider value={valor}>{children}</SesionContext.Provider>;
};

export const useSesion = () => useContext(SesionContext);

// Muestra su contenido solo si la persona tiene la acción. Uso: <Permitido accion={ACCION.HISTORIA_CREAR}>…</Permitido>
export const Permitido = ({ accion, children, sino = null }) => (useSesion().puede(accion) ? children : sino);
