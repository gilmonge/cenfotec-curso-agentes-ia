import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageTitle } from '../components/ui/PageTitle';
import { Button } from '../components/ui/Button';
import { UserStoryCard } from '../components/UserStoryCard';
import { getStoredStories } from '../utils/storage';
import { PlusCircle, Search, Filter } from 'lucide-react';
import { EmptyState } from '../components/ui/EmptyState';

export const UserStoriesList = () => {
  const navigate = useNavigate();
  const [stories, setStories] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    setStories(getStoredStories());
  }, []);

  const handleView = (id) => {
    navigate(`/historias/${id}`);
  };

  const handleEdit = (id) => {
    navigate(`/historias/${id}/editar`);
  };

  const filteredStories = stories.filter((story) => {
    const matchesSearch =
      story.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      story.id.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === 'all' || story.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div>
      <PageTitle
        title="Historias de Usuario"
        description="Gestione y consulte todas las Historias de Usuario generadas y registradas."
        action={
          <Button
            variant="primary"
            icon={PlusCircle}
            onClick={() => navigate('/historias/nueva')}
          >
            Nueva Historia
          </Button>
        }
      />

      {/* Filter and Search Bar */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: 1, minWidth: '240px', position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              type="text"
              className="input"
              placeholder="Buscar por título o código ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ paddingLeft: '2.4rem' }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={18} style={{ color: '#64748b' }} />
            <select
              className="select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ width: 'auto', minWidth: '180px' }}
            >
              <option value="all">Todos los estados</option>
              <option value="borrador">Borrador</option>
              <option value="en_analisis">En análisis</option>
              <option value="pendiente_de_informacion">Pendiente de información</option>
              <option value="generada">Generada</option>
              <option value="revisada">Revisada</option>
            </select>
          </div>
        </div>
      </div>

      {filteredStories.length === 0 ? (
        <EmptyState
          title="No se encontraron Historias de Usuario"
          description={
            searchTerm || statusFilter !== 'all'
              ? 'Intente modificar los filtros de búsqueda.'
              : 'Aún no se ha creado ninguna historia de usuario.'
          }
          actionText="Crear Nueva Historia"
          onAction={() => navigate('/historias/nueva')}
        />
      ) : (
        <div className="grid-3">
          {filteredStories.map((story) => (
            <UserStoryCard
              key={story.id}
              story={story}
              onView={handleView}
              onEdit={handleEdit}
            />
          ))}
        </div>
      )}
    </div>
  );
};
