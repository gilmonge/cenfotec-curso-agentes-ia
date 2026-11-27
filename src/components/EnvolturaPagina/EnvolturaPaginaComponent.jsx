import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { FileText, Moon, Sun, UserRound, LogOut } from 'lucide-react';
import { useTema } from '../../hooks/useTema';
import { useUsuarioActual } from '../../hooks/useUsuarioActual';
import { DialogoUsuarioComponent } from '../Usuario/DialogoUsuarioComponent';
import { TEXTO_PIE } from '../../config/entorno';
import { listaOpcionMenu } from '../../config/rutas';
import { AsistenteAyudaComponent } from '../AsistenteAyuda/AsistenteAyudaComponent';
import { useSesion } from '../Sesion/SesionContext';
import { useConfirmacion } from '../Comun/ConfirmacionComponent';
import { usePendientes } from '../../hooks/usePendientes';

// Iniciales para el avatar (por ejemplo «Ana Mora» → «AM»).
const iniciales = (texto) => String(texto ?? '').trim().split(/\s+/).slice(0, 2)
  .map((parte) => parte[0]?.toUpperCase() ?? '').join('') || '?';

export const EnvolturaPaginaComponent = () => {
  const { theme, toggleTheme } = useTema();
  const isDark = theme === 'dark';
  const { nombre, guardar } = useUsuarioActual();
  const [mostrarUsuario, setMostrarUsuario] = useState(false);
  const { seguridad, usuario, puede, salir } = useSesion();
  const confirmar = useConfirmacion();
  // Número junto a «Pendientes»: lo que espera la decisión de la persona y sus avisos sin leer.
  const { total: totalPendiente } = usePendientes();
  const contador = { pendientes: totalPendiente };
  const cerrarSesion = async () => {
    if (await confirmar({ titulo: 'Cerrar sesión', mensaje: `¿Cerrar la sesión de ${usuario.nombre}?`, textoConfirmar: 'Cerrar sesión' })) salir();
  };

  // Marca «Ciruela corporativa»: barra lateral en web, solo íconos en tablet y barra inferior en móvil
  // (todo en CSS, src/styles/_layout.scss). La navegación retrocede para que el contenido mande.
  return (
    <div className="app-container">
      <aside className="barra-lateral">
        <NavLink to="/" className="barra-lateral__marca" aria-label="Historias de Usuario, ir al inicio">
          <span className="barra-lateral__logo" aria-hidden="true"><FileText size={16} /></span>
          <span className="barra-lateral__nombre">
            Historias
            <small>de Usuario</small>
          </span>
        </NavLink>

        {/* Las opciones salen del registro único de pantallas (src/config/rutas.jsx). */}
        <nav className="barra-lateral__nav" aria-label="Menú principal">
          {listaOpcionMenu(puede).map(({ destino, etiqueta, corta, titulo, icono: Icono, exacta, contador: claveContador }) => (
            <NavLink
              key={destino}
              to={destino}
              title={titulo}
              end={Boolean(exacta)}
              className={({ isActive }) => `barra-lateral__enlace ${isActive ? 'active' : ''}`}
            >
              <Icono size={18} aria-hidden="true" />
              <span className="barra-lateral__etiqueta">{etiqueta}</span>
              <span className="barra-lateral__corta" aria-hidden="true">{corta ?? etiqueta}</span>
              {contador[claveContador] > 0 && (
                <span className="barra-lateral__contador" aria-label={`${contador[claveContador]} pendientes`}>
                  {contador[claveContador] > 99 ? '99+' : contador[claveContador]}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="barra-lateral__pie">
          {seguridad && usuario ? (
            <button
              type="button"
              className="barra-lateral__usuario"
              onClick={cerrarSesion}
              aria-label={`Usuario: ${usuario.nombre}. Cerrar sesión`}
              title={`${usuario.nombre} (${usuario.roles.map((rol) => rol.nombre).join(', ') || 'sin roles'}). Cerrar sesión`}
            >
              <span className="barra-lateral__avatar" aria-hidden="true">{iniciales(usuario.nombre)}</span>
              <span className="barra-lateral__persona">
                {usuario.nombre}
                <small>{usuario.roles.map((rol) => rol.nombre).join(', ') || 'Sin roles'}</small>
              </span>
              <LogOut size={16} aria-hidden="true" className="barra-lateral__salir" />
            </button>
          ) : (
            <button
              type="button"
              className="barra-lateral__usuario"
              onClick={() => setMostrarUsuario(true)}
              aria-label={nombre ? `Usuario: ${nombre}. Cambiar nombre` : 'Identificarse'}
              title="Su nombre queda registrado en las historias que cree o modifique"
            >
              <span className="barra-lateral__avatar" aria-hidden="true">{nombre ? iniciales(nombre) : <UserRound size={16} />}</span>
              <span className="barra-lateral__persona">
                {nombre || 'Identificarse'}
                <small>{nombre ? 'Cambiar nombre' : 'Su nombre queda en las historias'}</small>
              </span>
            </button>
          )}

          <button
            type="button"
            className="barra-lateral__tema"
            onClick={toggleTheme}
            aria-label={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
            title={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
          >
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </aside>

      {mostrarUsuario && (
        <DialogoUsuarioComponent
          nombreActual={nombre}
          alGuardar={(valor) => {
            guardar(valor);
            setMostrarUsuario(false);
          }}
          alCerrar={() => setMostrarUsuario(false)}
        />
      )}

      <div className="app-cuerpo">
        <main className="main-content">
          <Outlet />
        </main>

        <footer className="footer">
          <div className="footer__inner">
            <div>{TEXTO_PIE}</div>
          </div>
        </footer>
      </div>

      <AsistenteAyudaComponent />
    </div>
  );
};
