import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageTitle } from '../components/ui/PageTitle';
import { MetricCard } from '../components/MetricCard';
import { getStoredStories } from '../utils/storage';
import { FileText, PlusCircle, Sparkles, CheckCircle2, Clock, HelpCircle } from 'lucide-react';
import { Card } from '../components/ui/Card';

export const Dashboard = () => {
  const navigate = useNavigate();
  const [stories, setStories] = useState([]);

  useEffect(() => {
    setStories(getStoredStories());
  }, []);

  const totalStories = stories.length;
  const reviewedCount = stories.filter(s => s.status === 'revisada').length;
  const inAnalysisCount = stories.filter(s => s.status === 'en_analisis' || s.status === 'borrador').length;
  const pendingCount = stories.filter(s => s.status === 'pendiente_de_informacion').length;

  return (
    <div>
      <PageTitle
        title="Dashboard de Historias de Usuario"
        description="Gestión inteligente y análisis asistido por IA para requerimientos de software."
      />

      <div style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
        color: '#ffffff',
        borderRadius: '16px',
        padding: '2rem',
        marginBottom: '2rem',
        boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1.5rem'
      }}>
        <div style={{ maxWidth: '600px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', backgroundColor: 'rgba(255,255,255,0.1)', padding: '0.3rem 0.8rem', borderRadius: '9999px', fontSize: '0.8rem', fontWeight: '600', marginBottom: '1rem' }}>
            <Sparkles size={14} style={{ color: '#60a5fa' }} />
            <span>Asistente Inteligente de Requerimientos</span>
          </div>
          <h2 style={{ fontSize: '1.75rem', fontWeight: '800', marginBottom: '0.5rem', letterSpacing: '-0.02em' }}>
            Transforma requerimientos en Historias de Usuario listas para desarrollo
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: '1.6' }}>
            Analiza minutas, aclara ambigüedades con preguntas para Negocio y genera automáticamente criterios de aceptación estructurados.
          </p>
        </div>

        <div>
          <button
            onClick={() => navigate('/historias/nueva')}
            style={{
              backgroundColor: '#2563eb',
              color: '#ffffff',
              border: 'none',
              padding: '0.85rem 1.6rem',
              borderRadius: '10px',
              fontSize: '0.95rem',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.6rem',
              boxShadow: '0 4px 14px rgba(37, 99, 235, 0.4)',
              transition: 'transform 0.2s ease, background-color 0.2s ease'
            }}
          >
            <PlusCircle size={20} />
            Crear Historia con Stepper
          </button>
        </div>
      </div>

      {/* Metric Cards (Requirements 6: Card 1 & Card 2) */}
      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        <MetricCard
          icon={FileText}
          value={`${totalStories} Historias`}
          label="Historias de Usuario registradas en la plataforma"
          buttonText="Ver listado completo de historias"
          onButtonClick={() => navigate('/historias')}
          variant="outline"
        />

        <MetricCard
          icon={PlusCircle}
          value="Nueva Historia"
          label="Inicie el asistente interactivo de 5 pasos para crear una historia"
          buttonText="Iniciar proceso de creación"
          onButtonClick={() => navigate('/historias/nueva')}
          variant="primary"
        />
      </div>

      {/* Quick Summary Grid */}
      <h3 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#0f172a', marginBottom: '1rem' }}>
        Estado del Repositorio
      </h3>
      <div className="grid-3">
        <Card title="Completadas y Revisadas" subtitle="Listas para refinamiento">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.5rem' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', backgroundColor: '#ecfdf5', color: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CheckCircle2 size={22} />
            </div>
            <div>
              <span style={{ fontSize: '1.75rem', fontWeight: '800', color: '#0f172a' }}>{reviewedCount}</span>
              <p style={{ fontSize: '0.8rem', color: '#64748b' }}>Historias listas</p>
            </div>
          </div>
        </Card>

        <Card title="En Proceso de Análisis" subtitle="Requerimientos en definición">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.5rem' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', backgroundColor: '#e0f2fe', color: '#0284c7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Clock size={22} />
            </div>
            <div>
              <span style={{ fontSize: '1.75rem', fontWeight: '800', color: '#0f172a' }}>{inAnalysisCount}</span>
              <p style={{ fontSize: '0.8rem', color: '#64748b' }}>En progreso</p>
            </div>
          </div>
        </Card>

        <Card title="Pendiente de Información" subtitle="Aclaraciones de negocio">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.5rem' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', backgroundColor: '#fef3c7', color: '#d97706', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <HelpCircle size={22} />
            </div>
            <div>
              <span style={{ fontSize: '1.75rem', fontWeight: '800', color: '#0f172a' }}>{pendingCount}</span>
              <p style={{ fontSize: '0.8rem', color: '#64748b' }}>Preguntas abiertas</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
