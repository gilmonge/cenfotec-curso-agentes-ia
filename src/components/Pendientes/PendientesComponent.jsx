import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, CornerUpLeft, XCircle } from 'lucide-react';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { usePendientes } from '../../hooks/usePendientes';

// Lo que espera la decisión de la persona (según sus acciones) y los avisos sobre las historias que creó.
const POR_DECIDIR = Object.freeze({
  por_aprobar: 'Historia por aprobar',
  cambio_por_decidir: 'Cambio por decidir',
});

const AVISO = Object.freeze({
  aprobada: { icono: CheckCircle2, clase: 'exito', titulo: 'Su historia fue aprobada' },
  devuelta: { icono: CornerUpLeft, clase: 'advertencia', titulo: 'Su historia fue devuelta para ajustes' },
  rechazada: { icono: XCircle, clase: 'peligro', titulo: 'Su historia fue rechazada' },
});

const fecha = (valor) => {
  if (!valor) return '';
  const leida = new Date(valor);
  return Number.isNaN(leida.getTime()) ? '' : leida.toLocaleString('es-CR', { dateStyle: 'medium', timeStyle: 'short' });
};

export const PendientesComponent = () => {
  const navigate = useNavigate();
  const { por_decidir: porDecidir, avisos, cargando, marcarLeido } = usePendientes();
  const abrir = (workflowId) => navigate(`/historias/nueva?flujo=${encodeURIComponent(workflowId)}`);

  return (
    <div className="pendientes">
      <TituloPaginaComponent
        title="Pendientes"
        description="Lo que espera su decisión y los avisos sobre las historias que usted creó."
      />

      <section className="pendientes__bloque" aria-labelledby="pendientes-decision">
        <h2 id="pendientes-decision" className="pendientes__titulo">
          Espera su decisión <span className="pendientes__cuenta">{porDecidir.length}</span>
        </h2>
        {porDecidir.length === 0 ? (
          <p className="pendientes__vacio">{cargando ? 'Consultando…' : 'No hay nada esperando su decisión.'}</p>
        ) : (
          <ul className="pendientes__lista">
            {porDecidir.map((item) => (
              <li key={item.workflow_id} className="pendientes__fila">
                <span className="pendientes__punto" aria-hidden="true" />
                <div className="pendientes__texto">
                  <p className="pendientes__nombre">{item.titulo}</p>
                  <p className="pendientes__meta">
                    {POR_DECIDIR[item.tipo] ?? 'Por decidir'}
                    {item.creado_por ? ` · ${item.creado_por}` : ''}
                    {item.actualizado_en ? ` · ${fecha(item.actualizado_en)}` : ''}
                  </p>
                </div>
                <BotonComponent variant="primary" size="sm" onClick={() => abrir(item.workflow_id)}>
                  Revisar y decidir
                </BotonComponent>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="pendientes__bloque" aria-labelledby="pendientes-avisos">
        <h2 id="pendientes-avisos" className="pendientes__titulo">
          Avisos sobre sus historias <span className="pendientes__cuenta">{avisos.length}</span>
        </h2>
        {avisos.length === 0 ? (
          <p className="pendientes__vacio">{cargando ? 'Consultando…' : 'No tiene avisos nuevos.'}</p>
        ) : (
          <ul className="pendientes__lista">
            {avisos.map((aviso) => {
              const tipo = AVISO[aviso.tipo] ?? AVISO.devuelta;
              const Icono = tipo.icono;
              return (
                <li key={aviso.id} className="pendientes__fila">
                  <span className={`pendientes__icono pendientes__icono--${tipo.clase}`} aria-hidden="true"><Icono size={16} /></span>
                  <div className="pendientes__texto">
                    <p className="pendientes__nombre">{tipo.titulo}: {aviso.titulo}</p>
                    <p className="pendientes__meta">
                      {aviso.autor ? `Por ${aviso.autor}` : 'Product Owner'}{aviso.creado_en ? ` · ${fecha(aviso.creado_en)}` : ''}
                    </p>
                    {aviso.detalle && <p className="pendientes__motivo">Motivo: {aviso.detalle}</p>}
                  </div>
                  <div className="pendientes__acciones">
                    {aviso.tipo === 'devuelta' && aviso.workflow_id && (
                      <BotonComponent variant="secondary" size="sm" onClick={() => abrir(aviso.workflow_id)}>Retomar</BotonComponent>
                    )}
                    <BotonComponent variant="secondary" size="sm" onClick={() => marcarLeido(aviso.id)}>
                      Marcar como leído
                    </BotonComponent>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
};
