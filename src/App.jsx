import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { EnvolturaPaginaComponent } from './components/EnvolturaPagina/EnvolturaPaginaComponent';
import { listaRuta } from './config/rutas';
import { ConfirmacionProvider } from './components/Comun/ConfirmacionComponent';
import { AlertaComponent } from './components/Comun/AlertaComponent';
import { SesionProvider, useSesion } from './components/Sesion/SesionContext';
import { InicioSesionComponent } from './components/Sesion/InicioSesionComponent';

// Una pantalla con «accion» en el registro solo se abre si la persona tiene esa acción.
const PantallaProtegida = ({ accion, componente: Componente }) => (useSesion().puede(accion) ? <Componente /> : (
  <AlertaComponent type="warning" title="No tiene acceso a esta pantalla">
    Pida a un administrador que le asigne un rol con esta acción en Mantenimiento.
  </AlertaComponent>
));

const Aplicacion = () => {
  const { cargando, seguridad, usuario } = useSesion();
  if (cargando) return <div className="inicio-sesion"><p className="form-hint">Cargando…</p></div>;
  if (seguridad && !usuario) return <InicioSesionComponent />;
  return (
    <Routes>
      <Route path="/" element={<EnvolturaPaginaComponent />}>
        {listaRuta.map(({ ruta, componente, accion }) => {
          const elemento = <PantallaProtegida accion={accion} componente={componente} />;
          return ruta
            ? <Route key={ruta} path={ruta} element={elemento} />
            : <Route key="inicio" index element={elemento} />;
        })}
      </Route>
    </Routes>
  );
};

// Las rutas salen del registro único (src/config/rutas.jsx): aquí no se agregan pantallas.
export function App() {
  return (
    <Router>
      <SesionProvider>
        <ConfirmacionProvider>
          <Aplicacion />
        </ConfirmacionProvider>
      </SesionProvider>
    </Router>
  );
}

export default App;
