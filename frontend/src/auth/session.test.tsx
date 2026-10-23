import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { failure, json, mockHttp, page, user } from '../test/http';
import { renderApp } from '../test/renderApp';

describe('sessão e navegação protegida', () => {
  it('recupera a sessão através de me antes de consultar inventário', async () => {
    const fetchMock = mockHttp();
    renderApp();
    expect(screen.getByRole('status')).toHaveTextContent('verificar');
    await screen.findByRole('heading', { name: 'Inventário' });
    expect(screen.getByText(user.login)).toBeInTheDocument();
    expect(fetchMock.mock.calls.slice(0, 3).map(([url]) => new URL(String(url)).pathname))
      .toEqual(['/api/v1/auth/me', '/api/v1/auth/csrf', '/api/v1/inventory/resources']);
  });

  it('redireciona um visitante sem sessão e não consulta inventário', async () => {
    const fetchMock = mockHttp(() => failure(401, 'unauthenticated'));
    renderApp();
    await screen.findByRole('heading', { name: 'Iniciar sessão' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('faz login com CSRF, confirma me e renova CSRF antes de abrir a página privada', async () => {
    let loggedIn = false;
    const events: string[] = [];
    const fetchMock = mockHttp((url, options) => {
      events.push(url.pathname);
      if (url.pathname.endsWith('/auth/me')) return loggedIn ? json({ user }) : failure(401, 'unauthenticated');
      if (url.pathname.endsWith('/auth/csrf')) return json({ csrf_token: loggedIn ? 'session-csrf' : 'pre-login-csrf' });
      if (url.pathname.endsWith('/auth/login')) {
        expect(options.headers).toMatchObject({ 'X-CSRF-Token': 'pre-login-csrf' });
        expect(JSON.parse(String(options.body))).toEqual({ login: 'operador', password: 'test-password' });
        loggedIn = true;
        return json({ user });
      }
      return json(page());
    });
    renderApp('/login');
    const actor = userEvent.setup();
    await actor.type(await screen.findByLabelText('Nome de utilizador'), 'operador');
    await actor.type(screen.getByLabelText('Palavra-passe'), 'test-password');
    await actor.click(screen.getByRole('button', { name: 'Entrar' }));
    await screen.findByRole('heading', { name: 'Inventário' });
    expect(events).toEqual(['/api/v1/auth/me', '/api/v1/auth/csrf', '/api/v1/auth/login',
      '/api/v1/auth/me', '/api/v1/auth/csrf', '/api/v1/inventory/resources']);
    expect(fetchMock.mock.calls.every(([, options]) => options?.credentials === 'include')).toBe(true);
  });

  it('não aceita o resultado de login se me não confirmar a sessão', async () => {
    const fetchMock = mockHttp(url => {
      if (url.pathname.endsWith('/auth/me')) return failure(401, 'unauthenticated');
      if (url.pathname.endsWith('/auth/csrf')) return json({ csrf_token: 'pre-login' });
      return json({ user });
    });
    renderApp('/login');
    const actor = userEvent.setup();
    await actor.type(await screen.findByLabelText('Nome de utilizador'), 'operador');
    await actor.type(screen.getByLabelText('Palavra-passe'), 'test-password');
    await actor.click(screen.getByRole('button', { name: 'Entrar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('sessão terminou');
    expect(fetchMock.mock.calls.some(([url]) => new URL(String(url)).pathname.includes('/inventory/'))).toBe(false);
  });

  it('mostra credenciais inválidas sem expor mensagens internas e limpa a palavra-passe', async () => {
    mockHttp(url => url.pathname.endsWith('/csrf') ? json({ csrf_token: 'test-csrf' }) : failure(401, 'invalid_credentials'));
    renderApp('/login');
    const actor = userEvent.setup();
    await actor.type(await screen.findByLabelText('Nome de utilizador'), 'operador');
    await actor.type(screen.getByLabelText('Palavra-passe'), 'test-password');
    await actor.click(screen.getByRole('button', { name: 'Entrar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('palavra-passe inválidos');
    expect(screen.getByLabelText('Palavra-passe')).toHaveValue('');
    expect(screen.queryByText(/Texto interno/)).not.toBeInTheDocument();
  });

  it('impede submissões concorrentes do formulário', async () => {
    let release: ((value: Response) => void) | undefined;
    const fetchMock = mockHttp(url => {
      if (url.pathname.endsWith('/me')) return failure(401, 'unauthenticated');
      return new Promise<Response>(resolve => { release = resolve; });
    });
    renderApp('/login');
    const login = await screen.findByLabelText('Nome de utilizador');
    fireEvent.change(login, { target: { value: 'operador' } });
    fireEvent.change(screen.getByLabelText('Palavra-passe'), { target: { value: 'test-password' } });
    const form = login.closest('form')!;
    fireEvent.submit(form);
    fireEvent.submit(form);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(screen.getByRole('button', { name: 'A iniciar sessão…' })).toBeDisabled();
    release?.(failure(503, 'security_unavailable'));
    await screen.findByRole('alert');
  });

  it.each([503, 403])('falha fechado ao recuperar sessão: HTTP %s', async status => {
    const fetchMock = mockHttp(() => failure(status, status === 403 ? 'invalid_origin' : 'security_unavailable'));
    renderApp();
    await screen.findByRole('alert');
    expect(screen.queryByRole('heading', { name: 'Inventário' })).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('mostra erro de rede e permite recuperar a sessão novamente', async () => {
    const fetchMock = mockHttp();
    fetchMock.mockRejectedValueOnce(new TypeError('network down'));
    renderApp();
    expect(await screen.findByRole('alert')).toHaveTextContent('contactar o servidor');
    await userEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));
    await screen.findByRole('heading', { name: 'Inventário' });
  });

  it('termina a sessão com CSRF fresco e só depois abandona a área privada', async () => {
    let loggedOut = false;
    let csrfCount = 0;
    const fetchMock = mockHttp((url, options) => {
      if (url.pathname.endsWith('/me')) return loggedOut ? failure(401, 'unauthenticated') : json({ user });
      if (url.pathname.endsWith('/csrf')) return json({ csrf_token: `session-csrf-${++csrfCount}` });
      if (url.pathname.endsWith('/logout')) {
        expect(options.headers).toMatchObject({ 'X-CSRF-Token': 'session-csrf-2' });
        loggedOut = true;
        return json(null, 204);
      }
      return json(page());
    });
    renderApp();
    await screen.findByRole('heading', { name: 'Inventário' });
    await userEvent.click(screen.getByRole('button', { name: 'Terminar sessão' }));
    await screen.findByRole('heading', { name: 'Iniciar sessão' });
    expect(fetchMock.mock.calls.filter(([url]) => new URL(String(url)).pathname.endsWith('/logout'))).toHaveLength(1);
  });

  it('não declara logout bem-sucedido quando o servidor falha', async () => {
    mockHttp(url => {
      if (url.pathname.endsWith('/me')) return json({ user });
      if (url.pathname.endsWith('/csrf')) return json({ csrf_token: 'session-csrf' });
      if (url.pathname.endsWith('/logout')) return failure(503, 'security_unavailable');
      return json(page());
    });
    renderApp();
    await screen.findByRole('heading', { name: 'Inventário' });
    await userEvent.click(screen.getByRole('button', { name: 'Terminar sessão' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('indisponível');
    expect(screen.getByRole('button', { name: 'Terminar sessão' })).toBeEnabled();
    expect(screen.getByText(user.login)).toBeInTheDocument();
  });

  it('recusa uma resposta me incompleta sem abrir páginas privadas', async () => {
    mockHttp(() => json({ user: { login: 'forged' } }));
    renderApp();
    expect(await screen.findByRole('alert')).toHaveTextContent('resposta incompatível');
    expect(screen.queryByRole('heading', { name: 'Inventário' })).not.toBeInTheDocument();
  });
});
