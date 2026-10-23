export class ApiError extends Error {
  constructor(public readonly status: number, public readonly code: string) {
    super('Pedido à API não concluído.');
    this.name = 'ApiError';
  }
}

export function isAbort(error: unknown): boolean {
  // DOMException may come from a different browser realm than Error.
  return isRecord(error) && error.name === 'AbortError';
}

export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Não foi possível concluir o pedido.';
  if (error.code === 'invalid_origin' || error.code === 'https_required') {
    return 'O acesso requer a origem HTTPS autorizada. Verifique o endereço da aplicação.';
  }
  if (error.code === 'invalid_csrf') return 'A proteção do pedido expirou ou é inválida. Tente novamente.';
  if (error.code === 'invalid_credentials') return 'Nome de utilizador ou palavra-passe inválidos.';
  if (error.status === 401) return 'A sessão terminou. Inicie sessão novamente.';
  if (error.status === 403) return 'Não tem permissão para aceder a este conteúdo.';
  if (error.status === 404) return 'Recurso não encontrado ou não acessível.';
  if (error.status === 429) return 'Demasiadas tentativas. Aguarde antes de tentar novamente.';
  if (error.code === 'network_error') return 'Não foi possível contactar o servidor. Verifique a ligação.';
  if (error.code === 'invalid_response') return 'O servidor devolveu uma resposta incompatível.';
  if (error.status >= 500) return 'O serviço está indisponível. Tente novamente mais tarde.';
  return 'Não foi possível concluir o pedido. Verifique os dados e tente novamente.';
}

export function apiUrl(path: string, base = import.meta.env.VITE_API_BASE_URL || '/api/v1'): URL {
  try {
    const url = new URL(base.replace(/\/$/, '') + path, window.location.origin);
    if (window.location.protocol !== 'https:' || url.protocol !== 'https:'
        || url.origin !== window.location.origin || url.username || url.password
        || url.hash || url.search) throw new Error();
    return url;
  } catch {
    throw new ApiError(0, 'https_required');
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  csrf?: string;
  signal?: AbortSignal;
  query?: URLSearchParams;
}

export async function request(path: string, options: RequestOptions = {}): Promise<unknown> {
  const url = apiUrl(path);
  if (options.query) url.search = options.query.toString();
  const headers: Record<string, string> = { Accept: 'application/json' };
  const method = options.method || 'GET';
  if (method !== 'GET') {
    if (!options.csrf) throw new ApiError(403, 'invalid_csrf');
    headers['X-CSRF-Token'] = options.csrf;
  }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  let response: Response;
  try {
    response = await fetch(url, {
      method, headers, credentials: 'include', cache: 'no-store', redirect: 'error',
      signal: options.signal,
      ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
    });
  } catch (error) {
    if (isAbort(error)) throw error;
    throw new ApiError(0, 'network_error');
  }
  let data: unknown;
  if (response.status !== 204) {
    try { data = await response.json(); }
    catch { throw new ApiError(response.ok ? 0 : response.status, 'invalid_response'); }
  }
  if (!response.ok) {
    const code = isRecord(data) && isRecord(data.error) && typeof data.error.code === 'string'
      ? data.error.code : 'http_error';
    // Never display backend messages, response bodies or request credentials.
    throw new ApiError(response.status, code);
  }
  return data;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function invalidResponse(): never { throw new ApiError(0, 'invalid_response'); }
