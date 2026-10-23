import { useEffect, useState } from 'react';
import { useSession } from '../auth/SessionProvider';
import { ApiError, isAbort } from './client';

type Remote<T> = { status: 'loading' } | { status: 'error'; error: unknown } | { status: 'success'; data: T };

export function useRemote<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [result, setResult] = useState<Remote<T>>({ status: 'loading' });
  const [revision, setRevision] = useState(0);
  const { expire } = useSession();
  useEffect(() => {
    const controller = new AbortController();
    setResult({ status: 'loading' });
    void load(controller.signal).then(data => {
      if (!controller.signal.aborted) setResult({ status: 'success', data });
    }).catch((error: unknown) => {
      if (controller.signal.aborted || isAbort(error)) return;
      if (error instanceof ApiError && error.status === 401) expire();
      else setResult({ status: 'error', error });
    });
    return () => controller.abort();
  }, [load, revision, expire]);
  return { result, retry: () => setRevision(value => value + 1) };
}
