import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { BotonComponent } from '../Comun/BotonComponent';
import { TarjetaHistoriaUsuarioComponent } from './TarjetaHistoriaUsuarioComponent';
import { DialogoEliminarHistoriaComponent } from './DialogoEliminarHistoriaComponent';
import { useEliminarHistoria } from '../../hooks/useEliminarHistoria';
import { EVENTO_SINCRONIZADO, getStoredStories } from '../../utils/storage';
import { etiquetaHistoria } from '../../utils/plantillaHu';
import { PlusCircle, Search, Filter, LayoutGrid, List } from 'lucide-react';
import { EstadoVacioComponent } from '../Comun/EstadoVacioComponent';

const CLAVE_VISTA = 'historias_usuario_vista';

const leerVista = () => {
  try {
    return localStorage.getItem(CLAVE_VISTA) === 'lista' ? 'lista' : 'cuadro';
  } catch (error) {
    console.error('No se pudo leer la vista guardada:', error);
    return 'cuadro';
  }
};

export const ListaHistoriaUsuarioComponent = () => {
  const navigate = useNavigate();
  const [stories, setStories] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [vista, setVista] = useState(leerVista);

  const cambiarVista = (nueva) => {
    setVista(nueva);
    try {
      localStorage.setItem(CLAVE_VISTA, nueva);
    } catch (error) {
      console.error('No se pudo guardar la vista elegida:', error);
    }
  };

  useEffect(() => {
    const refrescar = () => setStories(getStoredStories());
    refrescar();
    window.addEventListener(EVENTO_SINCRONIZADO, refrescar);
    return () => window.removeEventListener(EVENTO_SINCRONIZADO, refrescar);
  }, []);

  const { storyToDelete, isDeleting, deleteError, requestDelete, cancelDelete, confirmDelete } = useEliminarHistoria(() => {
    setStories(getStoredStories());
  });

  const handleView = (id) => {
    navigate(`/historias/${id}`);
  };

  const handleRequestChange = (id) => {
    navigate(`/historias/${id}/solicitar-cambio`);
  };

  const handleEdit = (id) => {
    navigate(`/historias/${id}/editar`);
  };

  const filteredStories = stories.filter((story) => {
    const matchesSearch =
      story.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      etiquetaHistoria(story).toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === 'all' || story.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div>
      <TituloPaginaComponent
        title="Historias de Usuario"
        description="Gestione y consulte todas las Historias de Usuario generadas y registradas."
        action={
          <BotonComponent
            variant="primary"
            icon={PlusCircle}
            onClick={() => navigate('/historias/nueva')}
          >
            Nueva Historia
          </BotonComponent>
        }
      />

      {/* Filter and Search Bar */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: 1, minWidth: '240px', position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
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
            <Filter size={18} style={{ color: 'var(--color-text-muted)' }} />
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

          <div className="view-toggle" role="group" aria-label="Tipo de vista">
            <button type="button" className="view-toggle__button" aria-pressed={vista === 'cuadro'} onClick={() => cambiarVista('cuadro')}>
              <LayoutGrid size={16} /> Cuadros
            </button>
            <button type="button" className="view-toggle__button" aria-pressed={vista === 'lista'} onClick={() => cambiarVista('lista')}>
              <List size={16} /> Lista
            </button>
          </div>
        </div>
      </div>

      {filteredStories.length === 0 ? (
        <EstadoVacioComponent
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
        <div className={vista === 'lista' ? 'story-list' : 'grid-3'}>
          {filteredStories.map((story) => (
            <TarjetaHistoriaUsuarioComponent
              key={story.id}
              story={story}
              onView={handleView}
              onEdit={handleEdit}
              onRequestChange={handleRequestChange}
              onDelete={requestDelete}
              variante={vista}
            />
          ))}
        </div>
      )}

      {storyToDelete && (
        <DialogoEliminarHistoriaComponent
          story={storyToDelete}
          isDeleting={isDeleting}
          error={deleteError}
          onCancel={cancelDelete}
          onConfirm={confirmDelete}
        />
      )}
    </div>
  );
};
