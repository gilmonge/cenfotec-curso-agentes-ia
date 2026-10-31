import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, FileText, PlusCircle, HelpCircle, Sparkles, Moon, Sun, UserRound } from 'lucide-react';
import { useTema } from '../../hooks/useTema';
import { useUsuarioActual } from '../../hooks/useUsuarioActual';
import { DialogoUsuarioComponent } from '../Usuario/DialogoUsuarioComponent';
import { TEXTO_PIE } from '../../config/entorno';
import { AsistenteAyudaComponent } from '../AsistenteAyuda/AsistenteAyudaComponent';

export const EnvolturaPaginaComponent = () => {
  const { theme, toggleTheme } = useTema();
  const isDark = theme === 'dark';
  const { nombre, guardar } = useUsuarioActual();
  const [mostrarUsuario, setMostrarUsuario] = useState(false);

  return (
    <div className="app-container">
      <header className="header">
        <div className="header__inner">
          <NavLink to="/" className="header__brand" aria-label="Historias de Usuario, ir al inicio">
            <div className="brand-icon">
              <Sparkles size={20} />
            </div>
            <div className="brand-text">
              Historias de Usuario
            </div>
          </NavLink>

          <nav className="header__nav">
            <NavLink
              to="/"
              title="Ir al Dashboard"
              end
              className={({ isActive }) =>
                `header__nav-link ${isActive ? 'active' : ''}`
              }
            >
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </NavLink>

            <NavLink
              to="/historias"
              title="Ver Historias de Usuario"
              end
              className={({ isActive }) =>
                `header__nav-link ${isActive ? 'active' : ''}`
              }
            >
              <FileText size={18} />
              <span>Historias de Usuario</span>
            </NavLink>

            <NavLink
              to="/historias/nueva"
              title="Crear Nueva Historia"
              className={({ isActive }) =>
                `header__nav-link ${isActive ? 'active' : ''}`
              }
            >
              <PlusCircle size={18} />
              <span>Nueva Historia</span>
            </NavLink>



            <NavLink
              to="/ayuda"
              title="Ver Ayuda"
              className={({ isActive }) =>
                `header__nav-link ${isActive ? 'active' : ''}`
              }
            >
              <HelpCircle size={18} />
              <span>Ayuda</span>
            </NavLink>
          </nav>

          <button
            type="button"
            className="header__theme-toggle header__user"
            onClick={() => setMostrarUsuario(true)}
            aria-label={nombre ? `Usuario: ${nombre}. Cambiar nombre` : 'Identificarse'}
            title="Su nombre queda registrado en las historias que cree o modifique"
          >
            <UserRound size={18} />
            <span>{nombre || 'Identificarse'}</span>
          </button>

          <button
            type="button"
            className="header__theme-toggle"
            onClick={toggleTheme}
            aria-label={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
            title={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
            <span>{isDark ? 'Modo claro' : 'Modo oscuro'}</span>
          </button>
        </div>
      </header>

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

      <main className="main-content">
        <Outlet />
      </main>

      <AsistenteAyudaComponent />

      <footer className="footer">
        <div className="footer__inner">
          <div>{TEXTO_PIE}</div>
        </div>
      </footer>
    </div>
  );
};
