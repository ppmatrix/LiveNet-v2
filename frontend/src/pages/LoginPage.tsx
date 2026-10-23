import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useLocation } from 'react-router';
import { isRecord } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { ErrorNotice, Loading } from '../components/Feedback';

export function LoginPage() {
  const { session, pending, login, retry } = useSession();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const submitting = useRef(false);
  const location = useLocation();
  if (session.status === 'authenticated') {
    const state: unknown = location.state;
    const target = isRecord(state) && typeof state.from === 'string'
      && /^\/inventory(?:\/|\?|$)/.test(state.from) ? state.from : '/inventory';
    return <Navigate to={target} replace />;
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    try { await login(identifier, password); }
    finally { setPassword(''); submitting.current = false; }
  }
  return <main className="login-shell">
    <section className="login-intro" aria-label="LiveNet">
      <div className="brand"><span className="brand-mark" aria-hidden="true">L</span>LiveNet<span className="version">v2</span></div>
      <div><p className="eyebrow">GESTÃO DE INFRAESTRUTURA</p><h1>Conheça a sua<br />infraestrutura.</h1>
        <p className="intro-copy">Um lugar para consultar e organizar os recursos do seu laboratório.</p></div>
      <p className="intro-footer">Inventário · Identidade · Contexto</p>
    </section>
    <section className="login-panel" aria-labelledby="login-title">
      <div className="login-card"><p className="eyebrow">ÁREA DE TRABALHO</p><h2 id="login-title">Iniciar sessão</h2>
        <p className="muted">Utilize a sua conta LiveNet para aceder ao inventário.</p>
        {session.status === 'loading' ? <Loading label="A verificar a sessão…" /> : <>
          {session.error && <ErrorNotice message={session.error} retry={session.status === 'error' ? retry : undefined} />}
          <form onSubmit={event => { void submit(event); }}>
            <label htmlFor="login">Nome de utilizador</label>
            <input id="login" name="login" autoComplete="username" required maxLength={128}
              value={identifier} onChange={event => setIdentifier(event.target.value)} disabled={pending} autoCapitalize="none" spellCheck={false} />
            <label htmlFor="password">Palavra-passe</label>
            <input id="password" name="password" type="password" autoComplete="current-password" required maxLength={1024}
              value={password} onChange={event => setPassword(event.target.value)} disabled={pending} />
            <button className="button" type="submit" disabled={pending || !identifier.trim() || !password}>
              {pending ? 'A iniciar sessão…' : 'Entrar'}</button>
          </form>
        </>}
        <p className="login-note">O acesso está sujeito às permissões da sua conta.</p>
      </div>
    </section>
  </main>;
}
