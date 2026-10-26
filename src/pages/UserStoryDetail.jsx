import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageTitle } from '../components/ui/PageTitle';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { StatusBadge } from '../components/ui/StatusBadge';
import { AnalysisCard } from '../components/AnalysisCard';
import { getStoryById, deleteStory } from '../utils/storage';
import {
  ArrowLeft,
  Edit3,
  Trash2,
  Calendar,
  Tag,
  HelpCircle,
  FileCheck,
  ListFilter
} from 'lucide-react';
import { Alert } from '../components/ui/Alert';

export const UserStoryDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [story, setStory] = useState(null);
  const [criteriaViewMode, setCriteriaViewMode] = useState('list'); // 'list' | 'given_when_then'

  useEffect(() => {
    const data = getStoryById(id);
    setStory(data);
  }, [id]);

  if (!story) {
    return (
      <div>
        <Alert type="danger" title="Historia no encontrada">
          No se encontró ninguna historia de usuario con el identificador {id}.
        </Alert>
        <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/historias')}>
          Volver al listado
        </Button>
      </div>
    );
  }

  const handleDelete = () => {
    if (window.confirm(`¿Está seguro de eliminar la historia ${story.id}?`)) {
      deleteStory(story.id);
      navigate('/historias');
    }
  };

  return (
    <div>
      <PageTitle
        title={`${story.id} — ${story.title}`}
        description={`Registrada el ${story.createdAt} | Tipo: ${story.type || 'General'}`}
        action={
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/historias')}>
              Volver
            </Button>
            <Button variant="primary" icon={Edit3} onClick={() => navigate(`/historias/${story.id}/editar`)}>
              Editar
            </Button>
            <Button variant="danger" icon={Trash2} onClick={handleDelete}>
              Eliminar
            </Button>
          </div>
        }
      />

      {/* Main Grid Details */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Status Bar */}
        <div className="card" style={{ padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <StatusBadge status={story.status} />
              <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
                Última actualización: <strong>{story.updatedAt}</strong>
              </span>
            </div>
            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
              Fuente: <strong>{story.infoType || 'Minuta'}</strong>
            </div>
          </div>
        </div>

        {/* User Story Structure Card */}
        <Card title="Historia de Usuario Generada" subtitle="Formato estándar ágil de requerimiento">
          <div className="story-structure">
            <div className="story-structure__item">
              <div className="story-structure__label">Como (Role):</div>
              <div className="story-structure__content">{story.userStory?.asA || 'Usuario del sistema'}</div>
            </div>
            <div className="story-structure__item">
              <div className="story-structure__label">Quiero (Feature):</div>
              <div className="story-structure__content">{story.userStory?.iWant || 'Ejecutar la acción requerida'}</div>
            </div>
            <div className="story-structure__item">
              <div className="story-structure__label">Para (Benefit):</div>
              <div className="story-structure__content">{story.userStory?.soThat || 'Obtener el beneficio de negocio esperable'}</div>
            </div>
          </div>
        </Card>

        {/* Criterios de Aceptación */}
        <Card
          title={`Criterios de Aceptación (${story.acceptanceCriteria?.length || 0})`}
          subtitle="Condiciones de satisfacción verificables"
          action={
            <div style={{ display: 'flex', gap: '0.25rem', backgroundColor: '#f1f5f9', padding: '0.2rem', borderRadius: '6px' }}>
              <button
                type="button"
                onClick={() => setCriteriaViewMode('list')}
                style={{
                  padding: '0.25rem 0.6rem',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  backgroundColor: criteriaViewMode === 'list' ? '#ffffff' : 'transparent',
                  color: criteriaViewMode === 'list' ? '#2563eb' : '#64748b'
                }}
              >
                Lista
              </button>
              <button
                type="button"
                onClick={() => setCriteriaViewMode('given_when_then')}
                style={{
                  padding: '0.25rem 0.6rem',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  backgroundColor: criteriaViewMode === 'given_when_then' ? '#ffffff' : 'transparent',
                  color: criteriaViewMode === 'given_when_then' ? '#2563eb' : '#64748b'
                }}
              >
                Dado/Cuando/Entonces
              </button>
            </div>
          }
        >
          {story.acceptanceCriteria && story.acceptanceCriteria.length > 0 ? (
            criteriaViewMode === 'list' ? (
              <ol style={{ paddingLeft: '1.25rem' }}>
                {story.acceptanceCriteria.map((ac, idx) => (
                  <li key={idx} style={{ marginBottom: '0.6rem', fontSize: '0.95rem', color: '#334155' }}>
                    {ac.text}
                  </li>
                ))}
              </ol>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {story.acceptanceCriteria.map((ac, idx) => (
                  <div key={idx} style={{ padding: '0.85rem 1rem', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '0.875rem' }}>
                    <p style={{ fontWeight: '700', color: '#1e293b', marginBottom: '0.3rem' }}>Criterio {idx + 1}</p>
                    {ac.given && <p style={{ color: '#4f46e5', marginBottom: '0.15rem' }}><strong>GIVEN:</strong> {ac.given}</p>}
                    {ac.when && <p style={{ color: '#0284c7', marginBottom: '0.15rem' }}><strong>WHEN:</strong> {ac.when}</p>}
                    {ac.then && <p style={{ color: '#059669' }}><strong>THEN:</strong> {ac.then}</p>}
                  </div>
                ))}
              </div>
            )
          ) : (
            <p style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Sin criterios de aceptación asignados.</p>
          )}
        </Card>

        {/* Section 14: Preguntas Pendientes */}
        {story.pendingQuestions && story.pendingQuestions.length > 0 && (
          <div style={{ backgroundColor: '#fffbeb', border: '1px solid #fde68a', borderRadius: '10px', padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#b45309', fontWeight: '700', marginBottom: '0.5rem' }}>
              <HelpCircle size={18} />
              <span>Preguntas Pendientes de Negocio ({story.pendingQuestions.length})</span>
            </div>
            <ul style={{ paddingLeft: '1.25rem', color: '#92400e', fontSize: '0.9rem' }}>
              {story.pendingQuestions.map((pq, idx) => (
                <li key={idx} style={{ marginBottom: '0.35rem' }}>{pq}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Analysis Card */}
        {story.analysis && (
          <Card title="Análisis del Requerimiento Original" subtitle="Diagnóstico de datos y supuestos">
            <AnalysisCard analysis={story.analysis} />
          </Card>
        )}

        {/* Observaciones */}
        {story.observations && (
          <Card title="Observaciones" subtitle="Notas de desarrollo y arquitectura">
            <p style={{ fontSize: '0.95rem', color: '#334155', lineHeight: '1.6' }}>
              {story.observations}
            </p>
          </Card>
        )}
      </div>
    </div>
  );
};
