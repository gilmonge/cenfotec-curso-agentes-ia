import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, FileText, PlusCircle, HelpCircle, Sparkles, Cpu } from 'lucide-react';
import { AnalystChat } from '../components/analyst-chat/AnalystChat.jsx';

export const MainLayout = () => {
  return (
    <div className="app-container">
      <header className="header">
        <div className="header__inner">
          <NavLink to="/" className="header__brand">
            <div className="brand-icon">
              <Sparkles size={20} />
            </div>
            <div className="brand-text">
              StoryCraft <span>AI</span>
            </div>
          </NavLink>

          <nav className="header__nav">
            <NavLink
              to="/"
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
              className={({ isActive }) =>
                `header__nav-link ${isActive ? 'active' : ''}`
              }
            >
              <PlusCircle size={18} />
              <span>Nueva Historia</span>
            </NavLink>

            <NavLink
              to="/skills"
              className={({ isActive }) =>
                `header__nav-link ${isActive ? 'active' : ''}`
              }
            >
              <Cpu size={18} />
              <span>Skills</span>
            </NavLink>

            <NavLink
              to="/ayuda"
              className={({ isActive }) =>
                `header__nav-link ${isActive ? 'active' : ''}`
              }
            >
              <HelpCircle size={18} />
              <span>Ayuda</span>
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="main-content">
        <Outlet />
      </main>

      <footer className="footer">
        <div className="footer__inner">
          <div>
            <strong>StoryCraft AI</strong> — Prototipo Asistente IA para Historias de Usuario
          </div>
          <div>
            Entorno de demostración &copy; {new Date().getFullYear()}
          </div>
        </div>
      </footer>

      <AnalystChat />
    </div>
  );
};
