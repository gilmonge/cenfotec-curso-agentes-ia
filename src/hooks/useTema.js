import { useCallback, useEffect, useState } from 'react';

export const CLAVE_ALMACENAMIENTO_TEMA = 'historias_usuario_tema';

const readStoredTheme = () => {
  try {
    const stored = localStorage.getItem(CLAVE_ALMACENAMIENTO_TEMA);
    return stored === 'dark' || stored === 'light' ? stored : null;
  } catch (error) {
    console.error('No se pudo leer el tema guardado:', error);
    return null;
  }
};

const systemPrefersDark = () => {
  try {
    return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-color-scheme: dark)').matches;
  } catch (error) {
    console.error('No se pudo consultar el tema del sistema:', error);
    return false;
  }
};

export const obtenerTemaInicial = () => readStoredTheme() ?? (systemPrefersDark() ? 'dark' : 'light');

/** Tema claro/oscuro de la interfaz. Se recuerda en el navegador y respeta el tema del sistema la primera vez. */
export const useTema = () => {
  const [theme, setTheme] = useState(obtenerTemaInicial);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(CLAVE_ALMACENAMIENTO_TEMA, next);
      } catch (error) {
        console.error('No se pudo guardar el tema:', error);
      }
      return next;
    });
  }, []);

  return { theme, toggleTheme };
};
