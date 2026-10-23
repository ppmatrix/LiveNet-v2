export interface User {
  id: string;
  login: string;
  roles: string[];
}

export interface Resource {
  id: string;
  resource_type: string;
  display_name: string;
  description: string | null;
  administrative_state: string;
  attributes: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
  archived_at: string | null;
  row_version: number;
}

export interface ResourcePage {
  items: Resource[];
  total: number;
  page: number;
  per_page: number;
}

export const resourceTypes: Readonly<Record<string, string>> = {
  physical_host: 'Host físico', virtual_machine: 'Máquina virtual',
  container: 'Contentor', network_device: 'Equipamento de rede',
  storage_device: 'Armazenamento', iot_device: 'Dispositivo IoT',
  service: 'Serviço', cluster: 'Cluster',
};

export const administrativeStates: Readonly<Record<string, string>> = {
  active: 'Ativo', maintenance: 'Em manutenção', disabled: 'Desativado', archived: 'Arquivado',
};

export function resourceTypeLabel(value: string): string {
  return Object.hasOwn(resourceTypes, value) ? resourceTypes[value]! : value;
}
