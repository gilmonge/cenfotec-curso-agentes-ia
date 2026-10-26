import { INITIAL_USER_STORIES } from '../data/mockData';

const STORAGE_KEY = 'storycraft_user_stories';

export const getStoredStories = () => {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_USER_STORIES));
      return INITIAL_USER_STORIES;
    }
    return JSON.parse(data);
  } catch (error) {
    console.error('Error parsing stored stories from localStorage:', error);
    return INITIAL_USER_STORIES;
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

export const addStory = (newStory) => {
  const stories = getStoredStories();
  const id = `HU-${Math.floor(100 + Math.random() * 900)}`;
  const dateStr = new Date().toISOString().split('T')[0];
  
  const createdStory = {
    id,
    createdAt: dateStr,
    updatedAt: dateStr,
    status: 'revisada',
    ...newStory
  };

  const updated = [createdStory, ...stories];
  saveStoredStories(updated);
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
    updatedAt: dateStr
  };

  stories[index] = updatedStory;
  saveStoredStories(stories);
  return updatedStory;
};

export const deleteStory = (id) => {
  const stories = getStoredStories();
  const filtered = stories.filter((s) => String(s.id) !== String(id));
  saveStoredStories(filtered);
  return filtered;
};
