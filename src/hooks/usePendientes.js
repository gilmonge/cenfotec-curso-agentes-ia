import { useCallback, useEffect, useState } from 'react';
import { pendientesApi } from '../services/pendientesApi';

export const EVENTO_PENDIENTES = 'historias-usuario:pendientes-cambiaron';
const CADA_MINUTO = 60_000;
const VACIO = Object.freeze({ por_decidir: [], avisos: [], total: 0 });

// Avisa a las demás vistas que conviene volver a consultar (por ejemplo, después de decidir).
export const avisarCambioPendientes = () => window.dispatchEvent(new Event(EVENTO_PENDIENTES));

/** Lo que espera la decisión de la persona y sus avisos. Se actualiza cada minuto, al volver a la pestaña y al decidir. */
export const usePendientes = () => {
  const [pendientes, setPendientes] = useState(VACIO);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    try {
      setPendientes((await pendientesApi.listar()) ?? VACIO);
    } catch (error) {
      console.warn('No se pudieron consultar los pendientes:', error?.message ?? error);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    cargar();
    const intervalo = window.setInterval(cargar, CADA_MINUTO);
    const alVolver = () => { if (document.visibilityState === 'visible') cargar(); };
    document.addEventListener('visibilitychange', alVolver);
    window.addEventListener(EVENTO_PENDIENTES, cargar);
    return () => {
      window.clearInterval(intervalo);
      document.removeEventListener('visibilitychange', alVolver);
      window.removeEventListener(EVENTO_PENDIENTES, cargar);
    };
  }, [cargar]);

  const marcarLeido = useCallback(async (avisoId) => {
    setPendientes((actual) => ({
      ...actual,
      avisos: actual.avisos.filter((aviso) => aviso.id !== avisoId),
      total: Math.max(0, actual.total - 1),
    }));
    try {
      await pendientesApi.marcarLeido(avisoId);
    } catch (error) {
      console.warn('No se pudo marcar el aviso como leído:', error?.message ?? error);
    }
    avisarCambioPendientes();
  }, []);

  return { ...pendientes, cargando, recargar: cargar, marcarLeido };
};
