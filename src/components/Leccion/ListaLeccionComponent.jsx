import React, { useCallback, useEffect, useState } from 'react';
import { Check, X } from 'lucide-react';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { TarjetaComponent } from '../Comun/TarjetaComponent';
import { AlertaComponent } from '../Comun/AlertaComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { SelectorComponent } from '../Comun/SelectorComponent';
import { FlujoGroomingComponent } from '../FlujoGrooming/FlujoGroomingComponent';
import { repositorioApi, repositorioErrorMessage } from '../../services/repositorioApi';
import { rotuloCategoria } from '../../data/rotulosPregunta';

const FILTERS = [
  { value: 'propuesta', label: 'Propuestas (por decidir)' },
  { value: 'aprobada', label: 'Aprobadas (ya en el checklist)' },
  { value: 'rechazada', label: 'Rechazadas' },
];

export const ListaLeccionComponent = () => {
  const [estado, setEstado] = useState('propuesta');
  const [lessons, setLessons] = useState([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      setLessons(await repositorioApi.listLessons(estado));
      setError('');
    } catch (cause) {
      setLessons([]);
      setError(repositorioErrorMessage(cause));
    } finally {
      setIsLoading(false);
    }
  }, [estado]);

  useEffect(() => { void load(); }, [load]);

  const decide = async (lessonId, decision) => {
    try {
      await repositorioApi.decideLesson(lessonId, decision);
      await load();
    } catch (cause) {
      setError(repositorioErrorMessage(cause));
    }
  };

  return (
    <div>
      <TituloPaginaComponent
        title="Lecciones y checklist de vacíos"
        description="Lo aprendido en los cambios posteriores al grooming. Solo las lecciones que apruebe el Product Owner pasan al checklist que usa el Agente Analista."
      />

      <TarjetaComponent title="Lecciones aprendidas" subtitle="Decisión del Product Owner">
        <SelectorComponent label="Estado" id="lesson-state" options={FILTERS} value={estado} onChange={(event) => setEstado(event.target.value)} />
        {error && <AlertaComponent type="danger" title="No se pudo cargar">{error}</AlertaComponent>}
        {!error && !isLoading && lessons.length === 0 && (
          <p style={{ fontStyle: 'italic', color: 'var(--color-text-secondary)' }}>No hay lecciones en este estado.</p>
        )}
        <ul style={{ padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {lessons.map((lesson) => (
            <li key={lesson.id} style={{ listStyle: 'none', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '0.85rem 1rem' }}>
              <p style={{ fontSize: '0.875rem', color: 'var(--color-secondary-text)', fontWeight: 700 }}>
                {lesson.codigo} · {rotuloCategoria(lesson.categoria)} · origen {lesson.hu_codigo || 'HU eliminada'}
              </p>
              <p style={{ fontWeight: 600, color: 'var(--color-text-primary)', margin: '0.25rem 0' }}>{lesson.pregunta_sugerida}</p>
              {lesson.terminos.length > 0 && (
                <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>Términos: {lesson.terminos.join(', ')}</p>
              )}
              {lesson.estado === 'propuesta' && (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.6rem' }}>
                  <BotonComponent variant="primary" icon={Check} onClick={() => decide(lesson.id, 'aprobar')}>Aprobar</BotonComponent>
                  <BotonComponent variant="secondary" icon={X} onClick={() => decide(lesson.id, 'rechazar')}>Rechazar</BotonComponent>
                </div>
              )}
            </li>
          ))}
        </ul>
      </TarjetaComponent>

      <div style={{ marginTop: '1.5rem' }}>
        <TarjetaComponent title="Flujo antes y después del grooming" subtitle="Qué funciona hoy con el Agente Analista y qué sigue siendo manual">
          <FlujoGroomingComponent />
        </TarjetaComponent>
      </div>
    </div>
  );
};
