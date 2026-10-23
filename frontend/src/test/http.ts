// HTTP doubles live only in the test tree; the normal app has no mock mode.
import { vi } from 'vitest';
import type { Resource, ResourcePage } from '../api/contracts';

export const user = { id: 'aa14086b-6c80-4bad-86fc-41dc38d21212', login: 'operador', roles: ['inventory_reader'] };
export const resource: Resource = {
  id: '272b1a76-a172-4314-a4fe-eef7b706bff2', display_name: 'Router do laboratório',
  resource_type: 'network_device', administrative_state: 'active', description: 'Recurso de teste.',
  attributes: {}, created_at: '2026-10-23T10:00:00Z', updated_at: '2026-10-23T11:00:00Z',
  archived_at: null, row_version: 1,
};

export function page(items: Resource[] = [resource], overrides: Partial<ResourcePage> = {}): ResourcePage {
  return { items, page: 1, per_page: 50, total: items.length, ...overrides };
}

export function json(data: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status, headers: { 'Content-Type': 'application/json' },
  });
}

export function failure(status: number, code: string): Response {
  return json({ error: { code, message: 'Texto interno que nunca deve ser mostrado.' } }, status);
}

export type Handler = (url: URL, options: RequestInit) => Response | Promise<Response>;

export function mockHttp(handler?: Handler) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, options: RequestInit = {}) => {
    const url = new URL(String(input));
    if (handler) return handler(url, options);
    if (url.pathname.endsWith('/auth/me')) return json({ user });
    if (url.pathname.endsWith('/auth/csrf')) return json({ csrf_token: 'test-only-csrf' });
    if (url.pathname.endsWith('/inventory/resources')) return json(page());
    if (url.pathname.endsWith('/inventory/resources/' + resource.id)) return json(resource);
    throw new Error('Unexpected HTTP request in test: ' + url.pathname);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}
