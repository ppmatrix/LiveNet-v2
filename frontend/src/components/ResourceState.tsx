import { administrativeStates } from '../api/contracts';

export function ResourceState({ value }: { value: string }) {
  const known = Object.hasOwn(administrativeStates, value);
  return <span className={'state state-' + (known ? value : 'unknown')}>
    <span className="state-dot" aria-hidden="true" />{known ? administrativeStates[value] : value}
  </span>;
}

export function formatDate(value: string | null): string {
  if (!value) return 'Não disponível';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Não disponível'
    : new Intl.DateTimeFormat('pt-PT', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}
