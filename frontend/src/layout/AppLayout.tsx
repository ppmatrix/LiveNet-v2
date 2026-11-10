import { NavLink, Outlet } from 'react-router';
import { useSession } from '../auth/SessionProvider';
import { ErrorNotice } from '../components/Feedback';

export function AppLayout() {
  const { session, pending, logout } = useSession();
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Saltar para o conteúdo</a>
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark" aria-hidden="true">L</span>LiveNet<span className="version">v2</span></div>
      <p className="nav-label">ÁREA DE TRABALHO</p>
      <nav aria-label="Navegação principal">
        <NavLink to="/inventory"><span aria-hidden="true">▦</span> Inventário</NavLink>
        <NavLink to="/discovery"><span aria-hidden="true">⌕</span> Descoberta</NavLink>
        {['Monitorização', 'Alertas', 'Administração'].map(item =>
          <div className="nav-future" key={item}><span>{item}</span><span className="future-tag">Em breve</span></div>)}
      </nav>
      <div className="sidebar-footer">LiveNet v2<span>Gestão de infraestrutura</span></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><span className="workspace-name">Área de trabalho <span>/</span> Inventário</span>
        <div className="account"><span className="avatar" aria-hidden="true">{session.user?.login.charAt(0).toUpperCase()}</span>
          <span className="account-name">{session.user?.login}</span>
          <button className="button button-secondary button-small" onClick={() => { void logout(); }} disabled={pending}>
            {pending ? 'A terminar…' : 'Terminar sessão'}</button></div>
      </header>
      <main id="main-content" className="main-content" tabIndex={-1}>
        {session.error && <ErrorNotice message={session.error} />}
        <Outlet />
      </main>
      <footer className="workspace-footer">LiveNet v2 <span>Inventário de infraestrutura</span></footer>
    </div>
  </div>;
}
