import React, { useEffect, useRef, useState } from 'react';
import { FileText, LogIn } from 'lucide-react';
import { CampoTextoComponent } from '../Comun/CampoTextoComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { useSesion } from './SesionContext';

/** Ingreso con usuario y contraseña propios: lo que haga la persona queda a su nombre. */
export const InicioSesionComponent = () => {
  const { entrar, error: errorSesion } = useSesion();
  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  const campoRef = useRef(null);

  useEffect(() => {
    campoRef.current?.focus();
  }, []);

  const enviar = async (evento) => {
    evento.preventDefault();
    if (!usuario.trim() || !clave) {
      setError('Escriba su usuario y su contraseña.');
      return;
    }
    setEnviando(true);
    setError('');
    try {
      await entrar(usuario.trim(), clave);
    } catch (fallo) {
      console.error('No se pudo iniciar sesión:', fallo);
      setError(fallo?.status === 401 ? 'Usuario o contraseña incorrectos.' : 'No hay conexión con el servicio. Inténtelo de nuevo.');
      setEnviando(false);
    }
  };

  return (
    <div className="inicio-sesion">
      <section className="inicio-sesion__marca-panel" aria-label="Presentación">
        <div className="inicio-sesion__logo">
          <span className="barra-lateral__logo barra-lateral__logo--grande" aria-hidden="true"><FileText size={18} /></span>
          Historias de Usuario
        </div>
        <div>
          <p className="inicio-sesion__titular">Del requerimiento a la historia lista para grooming.</p>
          <p className="inicio-sesion__bajada">
            Un equipo de agentes analiza, pregunta y redacta. Las personas responden y deciden.
            Cada aprobación queda registrada a nombre de quien la hizo.
          </p>
        </div>
        <div className="inicio-sesion__cifras">
          <div><strong>5 pasos</strong>del requerimiento a la aprobación</div>
          <div><strong>1 ronda</strong>de preguntas a Negocio</div>
          <div><strong>100 %</strong>aprobación humana</div>
        </div>
      </section>
      <section className="inicio-sesion__formulario-panel" aria-label="Ingreso">
        <form className="inicio-sesion__tarjeta" onSubmit={enviar} aria-label="Iniciar sesión">
          <div>
            <h2>Ingresar</h2>
            <p className="form-hint">Use el usuario que le asignó el administrador.</p>
          </div>
          {(error || errorSesion) && <AlertaComponent type="warning" title="No se pudo ingresar">{error || errorSesion}</AlertaComponent>}
          <CampoTextoComponent
            label="Usuario"
            id="sesion-usuario"
            ref={campoRef}
            autoComplete="username"
            value={usuario}
            maxLength={60}
            onChange={(evento) => setUsuario(evento.target.value)}
          />
          <CampoTextoComponent
            label="Contraseña"
            id="sesion-clave"
            type="password"
            autoComplete="current-password"
            value={clave}
            maxLength={200}
            onChange={(evento) => setClave(evento.target.value)}
          />
          <BotonComponent type="submit" variant="primary" icon={LogIn} disabled={enviando} className="inicio-sesion__boton">
            {enviando ? 'Ingresando…' : 'Ingresar'}
          </BotonComponent>
          <p className="form-hint">Lo que cree, apruebe o devuelva queda a su nombre. Si olvidó su contraseña, pídale al administrador que la restablezca en Mantenimiento.</p>
        </form>
      </section>
    </div>
  );
};
