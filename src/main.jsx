import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './styles/main.scss';
import { habilitarSincronizacion, sincronizarHistorias } from './utils/storage';

// Las historias viven en la base de datos del backend; el navegador solo guarda una copia local.
habilitarSincronizacion();
sincronizarHistorias().catch((error) => console.warn('Sin sincronización con la base de datos:', error?.message ?? error));
window.addEventListener('focus', () => { sincronizarHistorias().catch(() => {}); });

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
