import { useCallback, useState } from 'react';
import { deleteStory } from '../utils/storage';
import { repositorioApi, repositorioErrorMessage } from '../services/repositorioApi';

/**
 * Eliminación de una historia con confirmación.
 * Si la historia ya se aprobó (está en el Repositorio de HU), primero se borra allí para que el agente
 * deje de usarla como referencia; si eso falla, la historia NO se borra localmente y se informa el motivo.
 */
export const useEliminarHistoria = (onDeleted) => {
  const [storyToDelete, setStoryToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const requestDelete = useCallback((story) => {
    setDeleteError('');
    setStoryToDelete(story);
  }, []);

  const cancelDelete = useCallback(() => {
    if (isDeleting) return;
    setStoryToDelete(null);
    setDeleteError('');
  }, [isDeleting]);

  const confirmDelete = useCallback(async () => {
    if (!storyToDelete || isDeleting) return;
    setIsDeleting(true);
    setDeleteError('');
    try {
      if (storyToDelete.repositorySynced) {
        try {
          await repositorioApi.deleteStory(storyToDelete.id);
        } catch (error) {
          // Si el repositorio ya no la tiene, el objetivo se cumplió: se continúa con el borrado local.
          if (error?.code !== 'REPOSITORY_NOT_FOUND') throw error;
        }
      }
      deleteStory(storyToDelete.id);
      const deleted = storyToDelete;
      setStoryToDelete(null);
      onDeleted?.(deleted);
    } catch (error) {
      console.error('No se pudo eliminar la historia:', error);
      setDeleteError(repositorioErrorMessage(error));
    } finally {
      setIsDeleting(false);
    }
  }, [storyToDelete, isDeleting, onDeleted]);

  return { storyToDelete, isDeleting, deleteError, requestDelete, cancelDelete, confirmDelete };
};
