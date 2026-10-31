import { useCallback, useEffect, useState } from 'react';
import { EVENTO_USUARIO, guardarNombreUsuario, leerNombreUsuario } from '../utils/usuarioActual';

/** Nombre de la persona que usa la aplicación (se recuerda en el navegador). */
export const useUsuarioActual = () => {
  const [nombre, setNombre] = useState(leerNombreUsuario);

  useEffect(() => {
    const actualizar = () => setNombre(leerNombreUsuario());
    window.addEventListener(EVENTO_USUARIO, actualizar);
    return () => window.removeEventListener(EVENTO_USUARIO, actualizar);
  }, []);

  const guardar = useCallback((nuevo) => guardarNombreUsuario(nuevo), []);
  return { nombre, guardar };
};
