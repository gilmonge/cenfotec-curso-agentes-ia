import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageTitle } from '../components/ui/PageTitle';
import { Accordion, AccordionItem } from '../components/ui/Accordion';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { StatusBadge } from '../components/ui/StatusBadge';
import { getStoryById, updateStory } from '../utils/storage';
import {
  Save,
  ArrowLeft,
  FileText,
  Search,
  HelpCircle,
  UserCheck,
  CheckSquare,
  MessageSquare
} from 'lucide-react';
import { Alert } from '../components/ui/Alert';

export const EditUserStory = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);

  // Form states matching Accordion sections
  const [title, setTitle] = useState('');
  const [status, setStatus] = useState('revisada');
  const [infoType, setInfoType] = useState('Minuta');
  const [description, setDescription] = useState('');

  const [asA, setAsA] = useState('');
  const [iWant, setIWant] = useState('');
  const [soThat, setSoThat] = useState('');

  const [observations, setObservations] = useState('');

  useEffect(() => {
    const data = getStoryById(id);
    if (data) {
      setStory(data);
      setTitle(data.title || '');
      setStatus(data.status || 'revisada');
      setInfoType(data.infoType || 'Minuta');
      setDescription(data.description || '');

      if (data.userStory) {
        setAsA(data.userStory.asA || '');
        setIWant(data.userStory.iWant || '');
        setSoThat(data.userStory.soThat || '');
      }

      setObservations(data.observations || '');
    }
    setLoading(false);
  }, [id]);

  if (loading) {
    return (
      <div style={{ padding: '3rem', textCenter: 'center' }}>
        Cargando historia de usuario...
      </div>
    );
  }

  if (!story) {
    return (
      <div>
        <Alert type="danger" title="Historia no encontrada">
          No se encontró la historia con ID {id}.
        </Alert>
        <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/historias')}>
          Volver a historias
        </Button>
      </div>
    );
  }

  const handleSave = (e) => {
    e.preventDefault();
    const updated = updateStory(id, {
      title,
      status,
      infoType,
      description,
      userStory: {
        asA,
        iWant,
        soThat
      },
      observations
    });

    if (updated) {
      navigate(`/historias/${id}`);
    }
  };

  return (
    <div>
      <PageTitle
        title={`Editar Historia ${story.id}`}
        description="Utilice las secciones colapsables (Accordion) para modificar los bloques de la historia de usuario."
        action={
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate(`/historias/${id}`)}>
              Cancelar
            </Button>
            <Button variant="primary" icon={Save} onClick={handleSave}>
              Guardar Cambios
            </Button>
          </div>
        }
      />

      <form onSubmit={handleSave}>
        {/* Accordion Container (Requirement 16) */}
        <Accordion>
          {/* Section 1: Requerimiento inicial */}
          <AccordionItem
            title="1. Requerimiento Inicial"
            badge="Información General"
            icon={FileText}
            defaultOpen={true}
          >
            <Input
              label="Título del Requerimiento / Historia"
              id="title"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />

            <div className="grid-2">
              <Select
                label="Estado de la Historia"
                id="status"
                options={[
                  { value: 'borrador', label: 'Borrador' },
                  { value: 'en_analisis', label: 'En análisis' },
                  { value: 'pendiente_de_informacion', label: 'Pendiente de información' },
                  { value: 'generada', label: 'Generada' },
                  { value: 'revisada', label: 'Revisada' }
                ]}
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              />

              <Select
                label="Tipo de información recibida"
                id="infoType"
                options={[
                  { value: 'Descripción libre', label: 'Descripción libre' },
                  { value: 'Minuta', label: 'Minuta de reunión' },
                  { value: 'Notas de conversación', label: 'Notas de conversación' },
                  { value: 'Otro', label: 'Otro' }
                ]}
                value={infoType}
                onChange={(e) => setInfoType(e.target.value)}
              />
            </div>

            <Textarea
              label="Descripción de negocio"
              id="description"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </AccordionItem>

          {/* Section 2: Análisis */}
          <AccordionItem
            title="2. Análisis del Requerimiento"
            badge={`${story.analysis?.knownData?.length || 0} conocidos`}
            icon={Search}
          >
            <div className="grid-2">
              <div>
                <h5 style={{ fontSize: '0.9rem', fontWeight: '700', color: '#10b981', marginBottom: '0.5rem' }}>
                  Datos conocidos ({story.analysis?.knownData?.length || 0})
                </h5>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.875rem', color: '#334155' }}>
                  {story.analysis?.knownData?.map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '0.35rem' }}>{item}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h5 style={{ fontSize: '0.9rem', fontWeight: '700', color: '#ef4444', marginBottom: '0.5rem' }}>
                  Información faltante ({story.analysis?.missingData?.length || 0})
                </h5>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.875rem', color: '#334155' }}>
                  {story.analysis?.missingData?.map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '0.35rem' }}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </AccordionItem>

          {/* Section 3: Preguntas para Negocio */}
          <AccordionItem
            title="3. Preguntas para Negocio"
            badge={`${story.questions?.length || 0} preguntas`}
            icon={HelpCircle}
          >
            {story.questions && story.questions.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {story.questions.map((q, idx) => (
                  <div key={idx} style={{ padding: '0.85rem', backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                      <strong style={{ fontSize: '0.85rem', color: '#4f46e5' }}>{q.category}</strong>
                      <StatusBadge status={q.status} />
                    </div>
                    <p style={{ fontSize: '0.9rem', fontWeight: '600', color: '#0f172a' }}>{q.question}</p>
                    <p style={{ fontSize: '0.85rem', color: '#475569', marginTop: '0.25rem', fontStyle: q.answer ? 'normal' : 'italic' }}>
                      Respuesta: {q.answer || 'Sin respuesta aún.'}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.875rem', color: '#94a3b8' }}>No hay preguntas registradas.</p>
            )}
          </AccordionItem>

          {/* Section 4: Historia de Usuario */}
          <AccordionItem
            title="4. Redacción de Historia de Usuario"
            badge="Estructura Ágil"
            icon={UserCheck}
            defaultOpen={true}
          >
            <Input
              label="Como (Rol / Actor)"
              id="asA"
              value={asA}
              onChange={(e) => setAsA(e.target.value)}
              placeholder="Ej. Usuario del sistema"
            />

            <Input
              label="Quiero (Acción / Necesidad)"
              id="iWant"
              value={iWant}
              onChange={(e) => setIWant(e.target.value)}
              placeholder="Ej. Modificar una cobertura asociada a una póliza"
            />

            <Input
              label="Para (Beneficio / Valor)"
              id="soThat"
              value={soThat}
              onChange={(e) => setSoThat(e.target.value)}
              placeholder="Ej. Mantener actualizada la información contractual"
            />
          </AccordionItem>

          {/* Section 5: Criterios de Aceptación */}
          <AccordionItem
            title="5. Criterios de Aceptación"
            badge={`${story.acceptanceCriteria?.length || 0} criterios`}
            icon={CheckSquare}
          >
            {story.acceptanceCriteria && story.acceptanceCriteria.length > 0 ? (
              <ol style={{ paddingLeft: '1.25rem' }}>
                {story.acceptanceCriteria.map((ac, idx) => (
                  <li key={idx} style={{ fontSize: '0.9rem', color: '#334155', marginBottom: '0.5rem' }}>
                    {ac.text}
                  </li>
                ))}
              </ol>
            ) : (
              <p style={{ fontSize: '0.875rem', color: '#94a3b8' }}>No hay criterios de aceptación definidos.</p>
            )}
          </AccordionItem>

          {/* Section 6: Observaciones */}
          <AccordionItem
            title="6. Observaciones y Notas Técnicas"
            badge="Notas libres"
            icon={MessageSquare}
          >
            <Textarea
              label="Observaciones adicionales"
              id="observations-edit"
              rows={4}
              value={observations}
              onChange={(e) => setObservations(e.target.value)}
              placeholder="Notas para el equipo de desarrollo, arquitectura o QA..."
            />
          </AccordionItem>
        </Accordion>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2rem', gap: '1rem' }}>
          <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate(`/historias/${id}`)}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" icon={Save} size="lg">
            Guardar Todos los Cambios
          </Button>
        </div>
      </form>
    </div>
  );
};
