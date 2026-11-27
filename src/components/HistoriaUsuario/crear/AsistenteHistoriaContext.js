import { createContext, useContext } from 'react';

// El controlador del asistente (useCrearHistoria) se comparte con las vistas de cada paso por este contexto.
export const AsistenteHistoriaContext = createContext(null);

export const useAsistenteHistoria = () => {
  const asistente = useContext(AsistenteHistoriaContext);
  if (!asistente) throw new Error('useAsistenteHistoria debe usarse dentro del asistente para crear una historia.');
  return asistente;
};
