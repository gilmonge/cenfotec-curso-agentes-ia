import { leerNombreUsuario } from './usuarioActual';
import { generarGuid } from './guid';
import { historiasApi } from '../services/repositorioApi';

const STORAGE_KEY = 'historias_usuario_prototipo';
export const EVENTO_SINCRONIZADO = 'historias-sincronizadas';
// --- Sincronización con la base de datos -------------------------------------------------
// localStorage funciona como caché local (lectura inmediata y sin conexión); la base de datos del
// backend es la fuente compartida entre dispositivos. Se activa solo en la aplicación real.
let sincronizacionHabilitada = false;
let colaEscritura = Promise.resolve();

export const habilitarSincronizacion = (habilitada = true) => {
  sincronizacionHabilitada = habilitada;
};

const encolar = (tarea) => {
  if (!sincronizacionHabilitada) return;
  colaEscritura = colaEscritura.then(tarea).catch((error) => {
    console.warn('No se pudo sincronizar la historia con la base de datos:', error?.message ?? error);
  });
};

const porFechaDesc = (a, b) => String(b.createdAt ?? '').localeCompare(String(a.createdAt ?? ''));

// Caché local de las historias (la fuente de verdad es la base de datos). Empieza vacía.
export const getStoredStories = () => {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Error parsing stored stories from localStorage:', error);
    return [];
  }
};

export const saveStoredStories = (stories) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stories));
  } catch (error) {
    console.error('Error saving stories to localStorage:', error);
  }
};

export const getStoryById = (id) => {
  const stories = getStoredStories();
  return stories.find((story) => String(story.id) === String(id)) || null;
};

// Identificador interno de la historia: GUID aleatorio (v4). El código legible que ve la persona
// usuaria es el número de la plantilla (ver etiquetaHistoria en plantillaHu.js).
export const generateStoryId = generarGuid;

export const addStory = (newStory) => {
  const stories = getStoredStories();
  const id = generateStoryId();
  const dateStr = new Date().toISOString().split('T')[0];
  
  const createdStory = {
    id,
    createdAt: dateStr,
    updatedAt: dateStr,
    createdBy: leerNombreUsuario(),
    updatedBy: leerNombreUsuario(),
    status: 'revisada',
    ...newStory
  };

  const updated = [createdStory, ...stories];
  saveStoredStories(updated);
  encolar(() => historiasApi.save(createdStory));
  return createdStory;
};

export const updateStory = (id, updatedFields) => {
  const stories = getStoredStories();
  const index = stories.findIndex((s) => String(s.id) === String(id));
  if (index === -1) return null;

  const dateStr = new Date().toISOString().split('T')[0];
  const updatedStory = {
    ...stories[index],
    ...updatedFields,
    updatedAt: dateStr,
    updatedBy: leerNombreUsuario()
  };

  stories[index] = updatedStory;
  saveStoredStories(stories);
  encolar(() => historiasApi.save(updatedStory));
  return updatedStory;
};

export const deleteStory = (id) => {
  const stories = getStoredStories();
  const filtered = stories.filter((s) => String(s.id) !== String(id));
  saveStoredStories(filtered);
  encolar(() => historiasApi.remove(id));
  return filtered;
};

// Trae las historias de la base de datos y reemplaza la caché local: la base es la fuente de verdad
// (altas, cambios y bajas hechos desde cualquier dispositivo). Lo que este dispositivo aún no envió
// se termina de enviar antes de leer.
export const sincronizarHistorias = async ({ signal } = {}) => {
  if (!sincronizacionHabilitada) return false;
  await colaEscritura;
  const remotas = (await historiasApi.list({ signal })).sort(porFechaDesc);
  const cambio = JSON.stringify(remotas) !== JSON.stringify(getStoredStories());
  saveStoredStories(remotas);
  if (cambio) window.dispatchEvent(new Event(EVENTO_SINCRONIZADO));
  return cambio;
};
