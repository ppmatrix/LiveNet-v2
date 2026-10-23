import { describe, expect, it, vi } from 'vitest';
import { apiUrl, errorMessage, request } from './client';
import { json, mockHttp } from '../test/http';

describe('cliente HTTP', () => {
  it('inclui cookies, JSON, CSRF e AbortSignal', async () => {
    const fetchMock = mockHttp(() => json({ ok: true }));
    const controller = new AbortController();
    await request('/auth/login', { method: 'POST', body: { login: 'teste', password: 'test-only' },
      csrf: 'csrf-test', signal: controller.signal });
    expect(fetchMock).toHaveBeenCalledWith(new URL('https://lab.test/api/v1/auth/login'), expect.objectContaining({
      credentials: 'include', cache: 'no-store', redirect: 'error', signal: controller.signal,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': 'csrf-test' },
    }));
  });

  it.each(['https://other.test/api/v1', 'http://lab.test/api/v1', 'https://user:secret@lab.test/api/v1'])('recusa URL não autorizada %s', base => {
    expect(() => apiUrl('/auth/me', base)).toThrow();
  });

  it('permite configurar um caminho base da mesma origem', () => {
    expect(apiUrl('/auth/me', '/api/v1').href).toBe('https://lab.test/api/v1/auth/me');
  });

  it('recusa execução a partir de uma página HTTP antes de fetch', async () => {
    const fetchMock = mockHttp();
    vi.stubGlobal('window', { location: { protocol: 'http:', origin: 'http://lab.test' } });
    try {
      await expect(request('/auth/me')).rejects.toMatchObject({ code: 'https_required' });
      expect(fetchMock).not.toHaveBeenCalled();
    } finally { vi.unstubAllGlobals(); }
  });

  it('recusa mutação sem CSRF antes de fetch', async () => {
    const fetchMock = mockHttp();
    await expect(request('/auth/logout', { method: 'POST' })).rejects.toMatchObject({ code: 'invalid_csrf' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('preserva cancelamento sem o converter em erro de rede', async () => {
    mockHttp(() => Promise.reject(new DOMException('cancelled', 'AbortError')));
    await expect(request('/auth/me')).rejects.toHaveProperty('name', 'AbortError');
  });

  it('trata falha de rede sem expor a mensagem original', async () => {
    mockHttp(() => Promise.reject(new Error('private-driver-message')));
    try { await request('/auth/me'); } catch (error) {
      expect(errorMessage(error)).toContain('contactar o servidor');
      expect(String(error)).not.toContain('private-driver-message');
    }
  });

  it('não trata resposta HTML como sessão válida', async () => {
    mockHttp(() => new Response('<html>not the API</html>', { status: 200 }));
    await expect(request('/auth/me')).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('não exporta tokens para armazenamento do browser', async () => {
    const local = vi.spyOn(Storage.prototype, 'setItem');
    mockHttp(() => json({ csrf_token: 'test-only' }));
    await request('/auth/csrf');
    expect(local).not.toHaveBeenCalled();
  });
});
