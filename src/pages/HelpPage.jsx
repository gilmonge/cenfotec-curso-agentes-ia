import React from 'react';
import { PageTitle } from '../components/ui/PageTitle';
import { Card } from '../components/ui/Card';
import { Sparkles, HelpCircle, Layers, CheckCircle2, ArrowRight } from 'lucide-react';

export const HelpPage = () => {
  return (
    <div>
      <PageTitle
        title="Centro de Ayuda y Documentación"
        description="Guía de uso para la prueba de concepto del Asistente IA para Historias de Usuario."
      />

      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        <Card title="¿Cómo funciona el Asistente IA?" subtitle="Flujo principal de 5 pasos">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: '#eff6ff', color: '#2563eb', fontWeight: '700', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                1
              </div>
              <div>
                <h5 style={{ fontWeight: '700', fontSize: '0.95rem', color: '#0f172a' }}>Requerimiento</h5>
                <p style={{ fontSize: '0.85rem', color: '#64748b' }}>Ingrese notas de reunión, minutas o descripción libre del requerimiento de negocio.</p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: '#eff6ff', color: '#2563eb', fontWeight: '700', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                2
              </div>
              <div>
                <h5 style={{ fontWeight: '700', fontSize: '0.95rem', color: '#0f172a' }}>Análisis</h5>
                <p style={{ fontSize: '0.85rem', color: '#64748b' }}>El sistema clasifica automáticamente datos conocidos, faltantes, supuestos y ambigüedades.</p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: '#eff6ff', color: '#2563eb', fontWeight: '700', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                3
              </div>
              <div>
                <h5 style={{ fontWeight: '700', fontSize: '0.95rem', color: '#0f172a' }}>Preguntas</h5>
                <p style={{ fontSize: '0.85rem', color: '#64748b' }}>El asistente genera preguntas de aclaración para Negocio clasificadas por categoría.</p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: '#eff6ff', color: '#2563eb', fontWeight: '700', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                4
              </div>
              <div>
                <h5 style={{ fontWeight: '700', fontSize: '0.95rem', color: '#0f172a' }}>Historia & Criterios</h5>
                <p style={{ fontSize: '0.85rem', color: '#64748b' }}>Generación en formato estándar (Como/Quiero/Para) y criterios de aceptación con vista Dado/Cuando/Entonces.</p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: '#eff6ff', color: '#2563eb', fontWeight: '700', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                5
              </div>
              <div>
                <h5 style={{ fontWeight: '700', fontSize: '0.95rem', color: '#0f172a' }}>Revisión y Guardado</h5>
                <p style={{ fontSize: '0.85rem', color: '#64748b' }}>Resumen completo y persistencia simulada en el navegador vía localStorage.</p>
              </div>
            </div>
          </div>
        </Card>

        <Card title="Edición mediante Accordion" subtitle="Secciones colapsables independientes">
          <p style={{ fontSize: '0.9rem', color: '#475569', lineHeight: '1.6', marginBottom: '1rem' }}>
            A diferencia de la creación en Stepper, la pantalla de <strong>Edición</strong> utiliza un componente tipo Accordion para permitir modificar de forma directa cualquier bloque de la historia sin tener que pasar linealmente por todos los pasos.
          </p>
          <ul style={{ paddingLeft: '1.25rem', fontSize: '0.875rem', color: '#334155' }}>
            <li style={{ marginBottom: '0.4rem' }}>Requerimiento inicial</li>
            <li style={{ marginBottom: '0.4rem' }}>Análisis del requerimiento</li>
            <li style={{ marginBottom: '0.4rem' }}>Preguntas para Negocio</li>
            <li style={{ marginBottom: '0.4rem' }}>Historia de usuario (Como / Quiero / Para)</li>
            <li style={{ marginBottom: '0.4rem' }}>Criterios de aceptación</li>
            <li style={{ marginBottom: '0.4rem' }}>Observaciones y notas técnicas</li>
          </ul>
        </Card>
      </div>

      <Card title="Preguntas Frecuentes (FAQ)">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#0f172a', marginBottom: '0.25rem' }}>
              ¿Se requiere conexión a un backend o base de datos real?
            </h4>
            <p style={{ fontSize: '0.875rem', color: '#475569' }}>
              No, esta versión es una prueba de concepto puramente de front-end. Los datos persisten temporalmente en el almacenamiento local de su navegador (<code>localStorage</code>).
            </p>
          </div>

          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#0f172a', marginBottom: '0.25rem' }}>
              ¿Utiliza APIs reales de Inteligencia Artificial como OpenAI o Gemini?
            </h4>
            <p style={{ fontSize: '0.875rem', color: '#475569' }}>
              En este prototipo se utiliza una simulación visual asistida para representar la experiencia de usuario y los tiempos de procesamiento sin consumir API keys externas.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
