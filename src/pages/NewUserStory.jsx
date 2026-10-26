import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageTitle } from '../components/ui/PageTitle';
import { Stepper } from '../components/ui/Stepper';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Alert } from '../components/ui/Alert';
import { AnalysisCard } from '../components/AnalysisCard';
import { QuestionCard } from '../components/QuestionCard';
import { addStory } from '../utils/storage';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  FileCode,
  ListFilter,
  HelpCircle,
  Save,
  Clock
} from 'lucide-react';

const STEPPER_STEPS = [
  { id: 1, label: 'Requerimiento' },
  { id: 2, label: 'Análisis' },
  { id: 3, label: 'Preguntas' },
  { id: 4, label: 'Historia de Usuario' },
  { id: 5, label: 'Revisión' }
];

export const NewUserStory = () => {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [loadingText, setLoadingText] = useState('');
  const [criteriaViewMode, setCriteriaViewMode] = useState('list'); // 'list' | 'given_when_then'

  // Step 1: Requerimiento state
  const [requirementName, setRequirementName] = useState('');
  const [infoType, setInfoType] = useState('Minuta');
  const [description, setDescription] = useState('');

  // Step 2: Simulated Analysis state
  const [analysis, setAnalysis] = useState({
    knownData: [],
    missingData: [],
    assumptions: [],
    ambiguities: []
  });

  // Step 3: Simulated Questions state
  const [questions, setQuestions] = useState([]);

  // Step 4: Generated User Story & Criteria state
  const [userStory, setUserStory] = useState({
    asA: '',
    iWant: '',
    soThat: ''
  });
  const [acceptanceCriteria, setAcceptanceCriteria] = useState([]);
  const [pendingQuestions, setPendingQuestions] = useState([]);

  // Step 5: Observations state
  const [observations, setObservations] = useState('');

  // Step 1 handler -> Trigger simulated AI Analysis
  const handleAnalyzeRequirement = (e) => {
    e.preventDefault();
    if (!requirementName.trim() || !description.trim()) {
      alert('Por favor complete el nombre y la descripción del requerimiento.');
      return;
    }

    setIsProcessing(true);
    setLoadingText('Analizando requerimiento con IA...');

    setTimeout(() => {
      // Generate simulated analysis tailored to inputs
      const simKnownData = [
        `Requerimiento ingresado como '${infoType}': ${requirementName}`,
        'Se identifica un actor de negocio y una acción principal en la solicitud.',
        'Existe un flujo transaccional base que debe ser actualizado.',
        'La solicitud requiere trazabilidad y registro en bitácora de auditoría.'
      ];

      const simMissingData = [
        'No se especifica si se requiere aprobación multinivel antes de confirmar.',
        'Falta definir la regla de tiempo de expiración o vigencia de la operación.'
      ];

      const simAssumptions = [
        'Se asume que la operación se realiza sobre registros en estado activo.',
        'Se asume integración directa con la base de datos principal de seguros/contratos.'
      ];

      const simAmbiguities = [
        'No está claro si aplica a clientes individuales o corporativos por igual.'
      ];

      setAnalysis({
        knownData: simKnownData,
        missingData: simMissingData,
        assumptions: simAssumptions,
        ambiguities: simAmbiguities
      });

      // Generate simulated questions for Step 3
      setQuestions([
        {
          id: 'q-1',
          category: 'Reglas de negocio',
          question: `¿Cuál es la vigencia exacta de las modificaciones para '${requirementName}'?`,
          answer: 'Vigencia a partir del siguiente día hábil.',
          status: 'respondida'
        },
        {
          id: 'q-2',
          category: 'Validaciones',
          question: '¿Qué validación debe realizarse si el cliente tiene pagos pendientes?',
          answer: '',
          status: 'pendiente'
        },
        {
          id: 'q-3',
          category: 'Comportamiento esperado',
          question: '¿Debe enviarse una notificación automática por correo electrónico al finalizar?',
          answer: '',
          status: 'pendiente'
        }
      ]);

      setIsProcessing(false);
      setActiveStep(2);
    }, 1200);
  };

  // Step 3 handler -> Trigger simulated AI Story Generation
  const handleGenerateStory = () => {
    setIsProcessing(true);
    setLoadingText('Generando Historia de Usuario y Criterios de Aceptación...');

    setTimeout(() => {
      // Build generated user story
      setUserStory({
        asA: 'Usuario / Ejecutivo del Sistema',
        iWant: `Gestionar ${requirementName.toLowerCase()} de forma automatizada`,
        soThat: 'pueda mantener actualizados los registros de negocio y garantizar la consistencia operativa.'
      });

      setAcceptanceCriteria([
        {
          id: 'ac-1',
          text: `El sistema debe permitir registrar ${requirementName.toLowerCase()} validando los campos obligatorios.`,
          given: `Dado que el ejecutivo ingresa la información requerida para ${requirementName}`,
          when: 'Cuando presiona el botón de guardar',
          then: 'Entonces el sistema valida los datos y registra la solicitud exitosamente.'
        },
        {
          id: 'ac-2',
          text: 'El sistema debe verificar las condiciones de vigencia e impedir duplicidades en el mismo periodo.',
          given: 'Dado que existe una solicitud en proceso para la misma entidad',
          when: 'Cuando se intenta crear una nueva solicitud idéntica',
          then: 'Entonces el sistema muestra un mensaje de advertencia impidiendo la duplicación.'
        },
        {
          id: 'ac-3',
          text: 'El sistema debe generar un registro de auditoría con fecha, hora y usuario responsable.',
          given: 'Dado que la operación es aprobada o modificada',
          when: 'Cuando se consulte la bitácora de auditoría',
          then: 'Entonces se visualiza el historial completo con los cambios aplicados.'
        }
      ]);

      // Collect unanswered questions into pending questions
      const unresolved = questions
        .filter((q) => q.status === 'pendiente' || !q.answer.trim())
        .map((q) => q.question);

      if (unresolved.length === 0) {
        unresolved.push('¿Se requiere un reporte de resumen semanal para gerencia?');
      }

      setPendingQuestions(unresolved);

      setIsProcessing(false);
      setActiveStep(4);
    }, 1200);
  };

  // Question answer handler
  const handleQuestionAnswerChange = (qId, newAnswer) => {
    setQuestions((prev) =>
      prev.map((q) => {
        if (q.id === qId) {
          return {
            ...q,
            answer: newAnswer,
            status: newAnswer.trim() ? 'respondida' : 'pendiente'
          };
        }
        return q;
      })
    );
  };

  // Final step save handler
  const handleSaveStory = () => {
    const newStoryData = {
      title: requirementName,
      type: 'Nueva Funcionalidad',
      status: pendingQuestions.length > 0 ? 'pendiente_de_informacion' : 'revisada',
      requirementName,
      infoType,
      description,
      analysis,
      questions,
      userStory,
      acceptanceCriteria,
      pendingQuestions,
      observations
    };

    const saved = addStory(newStoryData);
    navigate(`/historias/${saved.id}`);
  };

  return (
    <div>
      <PageTitle
        title="Creación de Historia de Usuario"
        description="Flujo asistido por IA para el análisis y estructuración de historias de usuario."
      />

      <Stepper
        steps={STEPPER_STEPS}
        activeStep={activeStep}
        onStepClick={(step) => setActiveStep(step)}
      />

      {/* Simulated AI Loading Screen */}
      {isProcessing && (
        <div className="ai-loader">
          <div className="ai-loader__spinner"></div>
          <p className="ai-loader__text">{loadingText}</p>
          <p className="ai-loader__subtext">Procesando reglas de negocio y estructurando datos mock...</p>
        </div>
      )}

      {!isProcessing && (
        <>
          {/* STEP 1: Requerimiento */}
          {activeStep === 1 && (
            <Card title="Paso 1 — Definición del Requerimiento" subtitle="Ingrese los datos iniciales o minutas recibidas de Negocio.">
              <form onSubmit={handleAnalyzeRequirement}>
                <Input
                  label="Nombre del requerimiento"
                  id="req-name"
                  required
                  placeholder="Ej. Modificación de coberturas en pólizas vigentes"
                  value={requirementName}
                  onChange={(e) => setRequirementName(e.target.value)}
                />

                <Select
                  label="Tipo de información"
                  id="info-type"
                  required
                  options={[
                    { value: 'Descripción libre', label: 'Descripción libre' },
                    { value: 'Minuta', label: 'Minuta de reunión' },
                    { value: 'Notas de conversación', label: 'Notas de conversación' },
                    { value: 'Otro', label: 'Otro formato' }
                  ]}
                  value={infoType}
                  onChange={(e) => setInfoType(e.target.value)}
                />

                <Textarea
                  label="Descripción o información de negocio"
                  id="req-desc"
                  required
                  rows={5}
                  placeholder="Describa el requerimiento tal como lo expresó el cliente o equipo de negocio..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  hint="Puede copiar y pegar notas desestructuradas, correos o minutas."
                />

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
                  <Button type="submit" variant="primary" icon={Sparkles} size="lg">
                    Analizar Requerimiento
                  </Button>
                </div>
              </form>
            </Card>
          )}

          {/* STEP 2: Análisis */}
          {activeStep === 2 && (
            <div>
              <Card
                title="Paso 2 — Análisis Simulado del Requerimiento"
                subtitle="Diagnóstico automático de elementos identificados, faltantes y ambigüedades."
              >
                <Alert type="info" title="Análisis Completado">
                  Se ha analizado el contenido ingresado para <strong>"{requirementName}"</strong>. Revise la clasificación de los datos detectados.
                </Alert>

                <AnalysisCard analysis={analysis} />

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid #e2e8f0' }}>
                  <Button variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(1)}>
                    Atrás
                  </Button>
                  <Button variant="primary" icon={ArrowRight} onClick={() => setActiveStep(3)}>
                    Preguntas de Aclaración
                  </Button>
                </div>
              </Card>
            </div>
          )}

          {/* STEP 3: Preguntas de Aclaración */}
          {activeStep === 3 && (
            <div>
              <Card
                title="Paso 3 — Preguntas de Aclaración para Negocio"
                subtitle="Responda o revise las dudas identificadas para eliminar ambigüedades antes de generar la historia."
              >
                <Alert type="warning" title="Preguntas de Negocio">
                  Responder estas preguntas ayudará a generar Criterios de Aceptación precisos.
                </Alert>

                {questions.map((q, idx) => (
                  <QuestionCard
                    key={q.id}
                    question={q}
                    index={idx}
                    onAnswerChange={handleQuestionAnswerChange}
                  />
                ))}

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid #e2e8f0' }}>
                  <Button variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(2)}>
                    Atrás
                  </Button>
                  <Button variant="primary" icon={Sparkles} onClick={handleGenerateStory}>
                    Generar Historia de Usuario
                  </Button>
                </div>
              </Card>
            </div>
          )}

          {/* STEP 4: Historia de Usuario */}
          {activeStep === 4 && (
            <div>
              <Card
                title="Paso 4 — Historia de Usuario Generada"
                subtitle="Visualización de la historia en formato estándar y criterios de aceptación."
              >
                <div className="story-structure">
                  <div className="story-structure__item">
                    <div className="story-structure__label">Como:</div>
                    <div className="story-structure__content">{userStory.asA}</div>
                  </div>
                  <div className="story-structure__item">
                    <div className="story-structure__label">Quiero:</div>
                    <div className="story-structure__content">{userStory.iWant}</div>
                  </div>
                  <div className="story-structure__item">
                    <div className="story-structure__label">Para:</div>
                    <div className="story-structure__content">{userStory.soThat}</div>
                  </div>
                </div>

                {/* Acceptance Criteria with selector: List vs Given/When/Then */}
                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h4 style={{ fontSize: '1.05rem', fontWeight: '700', color: '#0f172a' }}>
                      Criterios de Aceptación ({acceptanceCriteria.length})
                    </h4>

                    {/* Format Toggle Selector (Section 13) */}
                    <div style={{ display: 'flex', gap: '0.25rem', backgroundColor: '#f1f5f9', padding: '0.25rem', borderRadius: '8px' }}>
                      <button
                        type="button"
                        onClick={() => setCriteriaViewMode('list')}
                        style={{
                          padding: '0.3rem 0.75rem',
                          fontSize: '0.8rem',
                          fontWeight: '600',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          backgroundColor: criteriaViewMode === 'list' ? '#ffffff' : 'transparent',
                          color: criteriaViewMode === 'list' ? '#2563eb' : '#64748b',
                          boxShadow: criteriaViewMode === 'list' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
                        }}
                      >
                        Lista
                      </button>
                      <button
                        type="button"
                        onClick={() => setCriteriaViewMode('given_when_then')}
                        style={{
                          padding: '0.3rem 0.75rem',
                          fontSize: '0.8rem',
                          fontWeight: '600',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          backgroundColor: criteriaViewMode === 'given_when_then' ? '#ffffff' : 'transparent',
                          color: criteriaViewMode === 'given_when_then' ? '#2563eb' : '#64748b',
                          boxShadow: criteriaViewMode === 'given_when_then' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
                        }}
                      >
                        Dado / Cuando / Entonces
                      </button>
                    </div>
                  </div>

                  {criteriaViewMode === 'list' ? (
                    <ul style={{ paddingLeft: '1.25rem' }}>
                      {acceptanceCriteria.map((ac, idx) => (
                        <li key={ac.id || idx} style={{ marginBottom: '0.6rem', fontSize: '0.95rem', color: '#334155' }}>
                          {ac.text}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {acceptanceCriteria.map((ac, idx) => (
                        <div key={ac.id || idx} style={{ padding: '0.85rem 1rem', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '0.875rem' }}>
                          <p style={{ fontWeight: '700', color: '#1e293b', marginBottom: '0.4rem' }}>Criterio {idx + 1}</p>
                          <p style={{ color: '#4f46e5', marginBottom: '0.2rem' }}><strong>GIVEN:</strong> {ac.given}</p>
                          <p style={{ color: '#0284c7', marginBottom: '0.2rem' }}><strong>WHEN:</strong> {ac.when}</p>
                          <p style={{ color: '#059669' }}><strong>THEN:</strong> {ac.then}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Section 14: Preguntas Pendientes */}
                {pendingQuestions.length > 0 && (
                  <div style={{ backgroundColor: '#fffbeb', border: '1px solid #fde68a', borderRadius: '10px', padding: '1.25rem', marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#b45309', fontWeight: '700', marginBottom: '0.5rem' }}>
                      <HelpCircle size={18} />
                      <span>Preguntas pendientes por resolver ({pendingQuestions.length})</span>
                    </div>
                    <ul style={{ paddingLeft: '1.25rem', color: '#92400e', fontSize: '0.9rem' }}>
                      {pendingQuestions.map((pq, idx) => (
                        <li key={idx} style={{ marginBottom: '0.35rem' }}>{pq}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid #e2e8f0' }}>
                  <Button variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(3)}>
                    Atrás
                  </Button>
                  <Button variant="primary" icon={ArrowRight} onClick={() => setActiveStep(5)}>
                    Revisión Final
                  </Button>
                </div>
              </Card>
            </div>
          )}

          {/* STEP 5: Revisión */}
          {activeStep === 5 && (
            <div>
              <Card
                title="Paso 5 — Resumen y Guardado Final"
                subtitle="Confirme los detalles de la Historia de Usuario antes de guardarla en el repositorio."
              >
                <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
                  <div style={{ padding: '1rem', backgroundColor: '#f8fafc', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                    <h5 style={{ fontSize: '0.85rem', color: '#64748b', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Requerimiento</h5>
                    <p style={{ fontWeight: '700', color: '#0f172a' }}>{requirementName}</p>
                    <p style={{ fontSize: '0.85rem', color: '#475569' }}>Tipo: {infoType}</p>
                  </div>

                  <div style={{ padding: '1rem', backgroundColor: '#f8fafc', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                    <h5 style={{ fontSize: '0.85rem', color: '#64748b', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Resumen de Elementos</h5>
                    <p style={{ fontSize: '0.9rem', color: '#0f172a' }}>✓ Historia redactada</p>
                    <p style={{ fontSize: '0.9rem', color: '#0f172a' }}>✓ {acceptanceCriteria.length} Criterios de aceptación</p>
                    <p style={{ fontSize: '0.9rem', color: pendingQuestions.length > 0 ? '#b45309' : '#059669' }}>
                      {pendingQuestions.length > 0 ? `⚠ ${pendingQuestions.length} Preguntas pendientes` : '✓ Sin preguntas pendientes'}
                    </p>
                  </div>
                </div>

                <div className="story-structure" style={{ marginBottom: '1.5rem' }}>
                  <div className="story-structure__item">
                    <div className="story-structure__label">Como:</div>
                    <div className="story-structure__content">{userStory.asA}</div>
                  </div>
                  <div className="story-structure__item">
                    <div className="story-structure__label">Quiero:</div>
                    <div className="story-structure__content">{userStory.iWant}</div>
                  </div>
                  <div className="story-structure__item">
                    <div className="story-structure__label">Para:</div>
                    <div className="story-structure__content">{userStory.soThat}</div>
                  </div>
                </div>

                <Textarea
                  label="Observaciones adicionales"
                  id="observations"
                  rows={3}
                  placeholder="Ingrese notas o consideraciones técnicas para la fase de implementación..."
                  value={observations}
                  onChange={(e) => setObservations(e.target.value)}
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid #e2e8f0' }}>
                  <Button variant="secondary" icon={ArrowLeft} onClick={() => setActiveStep(4)}>
                    Atrás
                  </Button>
                  <Button variant="primary" icon={Save} size="lg" onClick={handleSaveStory}>
                    Guardar Historia
                  </Button>
                </div>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
};
