import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { UserStoriesList } from './pages/UserStoriesList';
import { NewUserStory } from './pages/NewUserStory';
import { UserStoryDetail } from './pages/UserStoryDetail';
import { EditUserStory } from './pages/EditUserStory';
import { SkillsPage } from './pages/SkillsPage';
import { HelpPage } from './pages/HelpPage';

export function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="historias" element={<UserStoriesList />} />
          <Route path="historias/nueva" element={<NewUserStory />} />
          <Route path="historias/:id" element={<UserStoryDetail />} />
          <Route path="historias/:id/editar" element={<EditUserStory />} />
          <Route path="skills" element={<SkillsPage />} />
          <Route path="ayuda" element={<HelpPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
