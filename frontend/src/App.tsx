import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { ChatPage } from './pages/ChatPage';
import { SettingsPage } from './pages/SettingsPage';
import { GroupsPage } from './pages/GroupsPage';
import { useTheme } from './hooks/useTheme';

function App() {
  useTheme();

  return (
    <BrowserRouter>
      <Sidebar>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/groups" element={<GroupsPage />} />
        </Routes>
      </Sidebar>
    </BrowserRouter>
  );
}

export default App;
