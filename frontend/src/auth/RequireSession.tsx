import { Navigate, Outlet, useLocation } from 'react-router';
import { ErrorNotice, Loading } from '../components/Feedback';
import { useSession } from './SessionProvider';

export function RequireSession() {
  const { session, retry } = useSession();
  const location = useLocation();
  if (session.status === 'loading') return <main className="session-gate"><Loading label="A verificar a sessão…" /></main>;
  if (session.status === 'error') return <main className="session-gate">
    <h1>Não foi possível verificar a sessão</h1>
    <ErrorNotice message={session.error || 'Serviço indisponível.'} retry={retry} />
  </main>;
  if (session.status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return <Outlet />;
}
