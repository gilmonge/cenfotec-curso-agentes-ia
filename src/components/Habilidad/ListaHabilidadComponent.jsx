import React, { useState, useMemo } from 'react';
import { TituloPaginaComponent } from '../Comun/TituloPaginaComponent';
import { TarjetaHabilidadComponent } from './TarjetaHabilidadComponent';
import { ModalDetalleHabilidadComponent } from './ModalDetalleHabilidadComponent';
import { skillsData } from '../../data/skillsData';
import { Cpu, ShieldCheck, CheckSquare, BookOpen, Search, SlidersHorizontal } from 'lucide-react';

export const ListaHabilidadComponent = () => {
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const filteredSkills = useMemo(() => {
    return skillsData.filter((skill) => {
      const matchesSearch =
        skill.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory =
        selectedCategory === 'all' || skill.categoryTag === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }, [searchQuery, selectedCategory]);

  const totalSections = useMemo(() => {
    return skillsData.reduce(
      (acc, skill) => acc + skill.checklistSections.length,
      0
    );
  }, []);

  const totalCriteria = useMemo(() => {
    return skillsData.reduce((acc, skill) => {
      return (
        acc +
        skill.checklistSections.reduce(
          (secAcc, sec) => secAcc + sec.items.length,
          0
        )
      );
    }, 0);
  }, []);

  return (
    <div className="skills-page">
      <TituloPaginaComponent
        title="Dashboard de Skills (.agents/skills)"
        description="Catálogo visual de habilidades y criterios de revisión técnica integrados en el workspace."
      />

      {/* Summary Metrics Top Bar */}
      <div className="grid-4" style={{ marginBottom: '2rem' }}>
        <div className="metric-card">
          <div className="metric-card__header">
            <span className="metric-card__label">Skills Disponibles</span>
            <div className="metric-card__icon-box">
              <Cpu size={22} />
            </div>
          </div>
          <div className="metric-card__value">{skillsData.length}</div>
          <div className="metric-card__footer">
            <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              Ubicación: <code>.agents/skills/</code>
            </span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-card__header">
            <span className="metric-card__label">Categorías Técnicas</span>
            <div className="metric-card__icon-box" style={{ color: 'var(--color-secondary-text)', backgroundColor: 'var(--color-secondary-light)' }}>
              <ShieldCheck size={22} />
            </div>
          </div>
          <div className="metric-card__value">2</div>
          <div className="metric-card__footer">
            <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              Resiliencia & Observabilidad
            </span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-card__header">
            <span className="metric-card__label">Bloques de Verificación</span>
            <div className="metric-card__icon-box" style={{ color: 'var(--color-success-text)', backgroundColor: 'var(--color-success-light)' }}>
              <CheckSquare size={22} />
            </div>
          </div>
          <div className="metric-card__value">{totalSections}</div>
          <div className="metric-card__footer">
            <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              Secciones especializadas
            </span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-card__header">
            <span className="metric-card__label">Criterios de Aceptación</span>
            <div className="metric-card__icon-box" style={{ color: 'var(--color-warning-text)', backgroundColor: 'var(--color-warning-light)' }}>
              <BookOpen size={22} />
            </div>
          </div>
          <div className="metric-card__value">{totalCriteria}</div>
          <div className="metric-card__footer">
            <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              Checklist total de items
            </span>
          </div>
        </div>
      </div>

      {/* Filters & Controls */}
      <div className="skills-toolbar">
        <div className="skills-toolbar__search">
          <Search size={18} className="skills-toolbar__search-icon" />
          <input
            type="text"
            className="input"
            placeholder="Buscar por nombre, palabra clave o descripción..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="skills-toolbar__filter">
          <SlidersHorizontal size={16} className="skills-toolbar__filter-icon" />
          <select
            className="select"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            <option value="all">Todas las categorías</option>
            <option value="resilience">Resiliencia y Manejo de Errores</option>
            <option value="observability">Observabilidad y Diagnóstico</option>
          </select>
        </div>
      </div>

      {/* Skills Grid */}
      {filteredSkills.length > 0 ? (
        <div className="grid-2" style={{ marginBottom: '2rem' }}>
          {filteredSkills.map((skill) => (
            <TarjetaHabilidadComponent
              key={skill.id}
              skill={skill}
              onOpen={(s) => setSelectedSkill(s)}
            />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-state__icon">
            <Search size={28} />
          </div>
          <h3 className="empty-state__title">No se encontraron skills</h3>
          <p className="empty-state__desc">
            No hay habilidades que coincidan con la búsqueda "{searchQuery}". Intente cambiar los filtros o el texto.
          </p>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => {
              setSearchQuery('');
              setSelectedCategory('all');
            }}
          >
            Limpiar Filtros
          </button>
        </div>
      )}

      {/* Detail Modal */}
      {selectedSkill && (
        <ModalDetalleHabilidadComponent
          skill={selectedSkill}
          onClose={() => setSelectedSkill(null)}
        />
      )}
    </div>
  );
};
