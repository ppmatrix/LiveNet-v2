import { invalidResponse, isRecord, request } from './client';
import type { User } from './contracts';

function userResponse(data: unknown): User {
  if (!isRecord(data) || !isRecord(data.user)) return invalidResponse();
  const user = data.user;
  if (typeof user.id !== 'string' || !user.id || typeof user.login !== 'string'
      || !user.login || !Array.isArray(user.roles)
      || !user.roles.every((role: unknown) => typeof role === 'string')) return invalidResponse();
  return { id: user.id, login: user.login, roles: user.roles as string[] };
}

export async function getCsrf(signal?: AbortSignal): Promise<string> {
  const data = await request('/auth/csrf', { signal });
  if (!isRecord(data) || typeof data.csrf_token !== 'string' || !data.csrf_token) return invalidResponse();
  return data.csrf_token;
}

export async function getMe(signal?: AbortSignal): Promise<User> {
  return userResponse(await request('/auth/me', { signal }));
}

export async function postLogin(login: string, password: string, csrf: string): Promise<void> {
  userResponse(await request('/auth/login', { method: 'POST', body: { login, password }, csrf }));
}

export async function postLogout(csrf: string): Promise<void> {
  await request('/auth/logout', { method: 'POST', csrf });
}
