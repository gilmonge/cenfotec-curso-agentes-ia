import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { EnvolturaPaginaComponent } from './components/EnvolturaPagina/EnvolturaPaginaComponent';
import { TableroComponent } from './components/Dashboard/TableroComponent';
import { ListaHistoriaUsuarioComponent } from './components/HistoriaUsuario/ListaHistoriaUsuarioComponent';
import { CrearHistoriaUsuarioComponent } from './components/HistoriaUsuario/CrearHistoriaUsuarioComponent';
import { DetalleHistoriaUsuarioComponent } from './components/HistoriaUsuario/DetalleHistoriaUsuarioComponent';
import { SolicitarCambioHistoriaComponent } from './components/HistoriaUsuario/SolicitarCambioHistoriaComponent';
import { EditarHistoriaUsuarioComponent } from './components/HistoriaUsuario/EditarHistoriaUsuarioComponent';
import { ListaHabilidadComponent } from './components/Habilidad/ListaHabilidadComponent';
import { AyudaComponent } from './components/Ayuda/AyudaComponent';
import { ListaLeccionComponent } from './components/Leccion/ListaLeccionComponent';

export function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<EnvolturaPaginaComponent />}>
          <Route index element={<TableroComponent />} />
          <Route path="historias" element={<ListaHistoriaUsuarioComponent />} />
          <Route path="historias/nueva" element={<CrearHistoriaUsuarioComponent />} />
          <Route path="historias/:id" element={<DetalleHistoriaUsuarioComponent />} />
          <Route path="historias/:id/editar" element={<EditarHistoriaUsuarioComponent />} />
          <Route path="historias/:id/solicitar-cambio" element={<SolicitarCambioHistoriaComponent />} />
          <Route path="lecciones" element={<ListaLeccionComponent />} />
          <Route path="skills" element={<ListaHabilidadComponent />} />
          <Route path="ayuda" element={<AyudaComponent />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
