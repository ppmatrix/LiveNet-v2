import { Link, Navigate, Route, Routes } from 'react-router';
import { RequireSession } from './auth/RequireSession';
import { AppLayout } from './layout/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { ResourceDetailPage } from './pages/ResourceDetailPage';
import { ResourcesPage } from './pages/ResourcesPage';

export function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route element={<RequireSession />}>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/inventory" replace />} />
        <Route path="/inventory" element={<ResourcesPage />} />
        <Route path="/inventory/:resourceId" element={<ResourceDetailPage />} />
        <Route path="*" element={<><h1>Página não encontrada</h1><p>Este endereço não está disponível.</p><Link to="/inventory">Voltar ao inventário</Link></>} />
      </Route>
    </Route>
  </Routes>;
}
