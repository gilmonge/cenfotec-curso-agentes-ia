import { rotuloHerramienta } from '../../data/rotulosPregunta';

/**
 * Muestra cómo trabajó un agente: qué decidió consultar en cada ronda, por qué,
 * y si pidió criterio al Asesor Técnico. Solo describe el plan; no muestra resultados.
 */
export function PlanAgenteComponent({ plan = [], titulo = 'Cómo trabajó el agente', style }) {
  if (!Array.isArray(plan) || plan.length === 0) return null;
  return (
    <details className="plan-agente" style={style}>
      <summary style={{ cursor: 'pointer', fontWeight: 700, color: 'var(--color-text-primary)' }}>{titulo}</summary>
      {plan.map((paso) => (
        <div key={paso.ronda} style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
          <p style={{ margin: 0 }}>
            <strong>Ronda {paso.ronda}</strong>
            {paso.origen === 'predeterminado' ? ' (consulta completa del sistema)' : ''}
            {paso.razonamiento ? `: ${paso.razonamiento}` : ''}
          </p>
          {paso.consultas.length > 0 ? (
            <ul aria-label={`Consultas de la ronda ${paso.ronda}`} style={{ paddingLeft: '1.2rem', margin: '0.35rem 0 0' }}>
              {paso.consultas.map((item, indice) => (
                <li key={`${item.herramienta}-${indice}`}>
                  {rotuloHerramienta(item.herramienta)}: «{item.consulta}»
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ margin: '0.35rem 0 0' }}>No consideró necesario consultar más fuentes.</p>
          )}
          {paso.asesor_consultado && <p style={{ margin: '0.35rem 0 0' }}>Consultó al Asesor Técnico.</p>}
        </div>
      ))}
    </details>
  );
}

export default PlanAgenteComponent;
