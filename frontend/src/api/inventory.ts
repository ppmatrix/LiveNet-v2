import { invalidResponse, isRecord, request } from './client';
import type { Resource, ResourcePage } from './contracts';

function nullableString(value: unknown): value is string | null {
  return value === null || typeof value === 'string';
}

function parseResource(data: unknown): Resource {
  if (!isRecord(data) || !['id', 'resource_type', 'display_name', 'administrative_state'].every(
    key => typeof data[key] === 'string' && data[key] !== '',
  ) || !nullableString(data.description) || !isRecord(data.attributes)
      || !nullableString(data.created_at) || !nullableString(data.updated_at)
      || !nullableString(data.archived_at) || !Number.isSafeInteger(data.row_version)
      || (data.row_version as number) < 1) return invalidResponse();
  return data as unknown as Resource;
}

export interface ResourceQuery {
  page: number;
  per_page: number;
  resource_type?: string;
  administrative_state?: string;
}

export async function getResources(query: ResourceQuery, signal?: AbortSignal): Promise<ResourcePage> {
  const params = new URLSearchParams({ page: String(query.page), per_page: String(query.per_page) });
  if (query.resource_type) params.set('resource_type', query.resource_type);
  if (query.administrative_state) params.set('administrative_state', query.administrative_state);
  const data = await request('/inventory/resources', { query: params, signal });
  if (!isRecord(data) || !Array.isArray(data.items) || !Number.isSafeInteger(data.total)
      || (data.total as number) < 0 || !Number.isSafeInteger(data.page) || (data.page as number) < 1
      || !Number.isSafeInteger(data.per_page) || (data.per_page as number) < 1
      || (data.per_page as number) > 100) return invalidResponse();
  return { items: data.items.map(parseResource), total: data.total as number,
    page: data.page as number, per_page: data.per_page as number };
}

export async function getResource(id: string, signal?: AbortSignal): Promise<Resource> {
  return parseResource(await request('/inventory/resources/' + encodeURIComponent(id), { signal }));
}
