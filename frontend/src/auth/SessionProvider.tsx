import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { getCsrf, getMe, postLogin, postLogout } from '../api/auth';
import { ApiError, errorMessage, isAbort } from '../api/client';
import type { User } from '../api/contracts';

type SessionState =
  | { status: 'loading'; user: null; error: null }
  | { status: 'authenticated'; user: User; error: string | null }
  | { status: 'unauthenticated' | 'error'; user: null; error: string | null };

interface SessionContextValue {
  session: SessionState;
  pending: boolean;
  login: (login: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  retry: () => void;
  expire: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState>({ status: 'loading', user: null, error: null });
  const [pending, setPending] = useState(false);
  const [revision, setRevision] = useState(0);
  const sequence = useRef(0);
  const busy = useRef(false);

  const expire = useCallback(() => {
    sequence.current += 1;
    setSession({ status: 'unauthenticated', user: null, error: 'A sessão terminou. Inicie sessão novamente.' });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const run = ++sequence.current;
    setSession({ status: 'loading', user: null, error: null });
    async function restore() {
      try {
        const user = await getMe(controller.signal);
        await getCsrf(controller.signal);
        if (sequence.current === run) setSession({ status: 'authenticated', user, error: null });
      } catch (error) {
        if (isAbort(error) || sequence.current !== run) return;
        setSession(error instanceof ApiError && error.status === 401
          ? { status: 'unauthenticated', user: null, error: null }
          : { status: 'error', user: null, error: errorMessage(error) });
      }
    }
    void restore();
    return () => { controller.abort(); sequence.current += 1; };
  }, [revision]);

  async function login(identifier: string, password: string) {
    if (busy.current || session.status === 'loading' || session.status === 'authenticated') return;
    busy.current = true;
    setPending(true);
    const run = ++sequence.current;
    setSession({ status: 'unauthenticated', user: null, error: null });
    try {
      const preLoginCsrf = await getCsrf();
      await postLogin(identifier, password, preLoginCsrf);
      // The login response alone never opens private pages.
      const user = await getMe();
      await getCsrf(); // Pre-login CSRF was invalidated by the backend.
      if (sequence.current === run) setSession({ status: 'authenticated', user, error: null });
    } catch (error) {
      if (sequence.current === run) setSession({
        status: error instanceof ApiError && error.status === 401 ? 'unauthenticated' : 'error',
        user: null, error: errorMessage(error),
      });
    } finally { busy.current = false; setPending(false); }
  }

  async function logout() {
    if (busy.current || session.status !== 'authenticated') return;
    busy.current = true;
    setPending(true);
    const run = ++sequence.current;
    const user = session.user;
    try {
      // Get a fresh token bound to the current session; never reuse pre-login CSRF.
      await postLogout(await getCsrf());
      if (sequence.current === run) setSession({ status: 'unauthenticated', user: null, error: null });
    } catch (error) {
      if (sequence.current === run) {
        if (error instanceof ApiError && error.status === 401) expire();
        else setSession({ status: 'authenticated', user, error: errorMessage(error) });
      }
    } finally { busy.current = false; setPending(false); }
  }

  return <SessionContext.Provider value={{ session, pending, login, logout, expire,
    retry: () => { if (!busy.current) setRevision(value => value + 1); } }}>
    {children}
  </SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error('SessionProvider em falta.');
  return context;
}
