import { useCallback } from 'react';
import { Link, useSearchParams } from 'react-router';
import { ApiError, errorMessage } from '../api/client';
import { administrativeStates, resourceTypeLabel, resourceTypes } from '../api/contracts';
import { getResources } from '../api/inventory';
import { useRemote } from '../api/useRemote';
import { ErrorNotice, Loading } from '../components/Feedback';
import { ResourceState } from '../components/ResourceState';

function positive(value: string | null, fallback: number, max: number): number {
  return value && /^[1-9][0-9]{0,9}$/.test(value) && Number(value) <= max ? Number(value) : fallback;
}

export function ResourcesPage() {
  const [params, setParams] = useSearchParams();
  const page = positive(params.get('page'), 1, 2 ** 31 - 1);
  const perPage = positive(params.get('per_page'), 50, 100);
  const resourceType = Object.hasOwn(resourceTypes, params.get('resource_type') || '') ? params.get('resource_type') || '' : '';
  const administrativeState = Object.hasOwn(administrativeStates, params.get('administrative_state') || '') ? params.get('administrative_state') || '' : '';
  const load = useCallback((signal: AbortSignal) => getResources({ page, per_page: perPage,
    resource_type: resourceType, administrative_state: administrativeState }, signal), [page, perPage, resourceType, administrativeState]);
  const { result, retry } = useRemote(load);

  function change(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== 'page') next.set('page', '1');
    setParams(next);
  }
  const data = result.status === 'success' ? result.data : null;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1;
  return <>
    <div className="page-heading"><div><p className="eyebrow">RECURSOS</p><h1>Inventário</h1>
      <p className="muted">Consulte os recursos e o seu contexto administrativo.</p></div>
      {data && <div className="total-count"><strong>{data.total}</strong><span>recursos encontrados</span></div>}
    </div>
    <section className="surface" aria-label="Recursos do inventário">
      <div className="filters"><div><label htmlFor="resource-type">Tipo de recurso</label>
        <select id="resource-type" value={resourceType} onChange={event => change('resource_type', event.target.value)}>
          <option value="">Todos os tipos</option>{Object.entries(resourceTypes).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></div>
        <div><label htmlFor="administrative-state">Estado administrativo</label>
          <select id="administrative-state" value={administrativeState} onChange={event => change('administrative_state', event.target.value)}>
            <option value="">Todos os estados</option>{Object.entries(administrativeStates).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select></div>
        <div className="page-size"><label htmlFor="per-page">Por página</label>
          <select id="per-page" value={perPage} onChange={event => change('per_page', event.target.value)}>
            {[...new Set([25, 50, 100, perPage])].sort((a, b) => a - b).map(value => <option key={value} value={value}>{value}</option>)}
          </select></div>
      </div>
      {result.status === 'loading' && <Loading label="A carregar os recursos…" />}
      {result.status === 'error' && <div className="surface-message"><ErrorNotice message={errorMessage(result.error)}
        retry={result.error instanceof ApiError && result.error.status === 403 ? undefined : retry} /></div>}
      {data && <>
        {data.items.length === 0 ? <div className="empty-state"><span className="empty-icon" aria-hidden="true">▦</span>
          <h2>Nenhum recurso encontrado</h2><p>Não existem recursos nesta página com os filtros selecionados.</p></div>
          : <div className="table-scroll"><table><caption className="sr-only">Recursos inventariados</caption>
            <thead><tr><th scope="col">Nome</th><th scope="col">Tipo</th><th scope="col">Estado administrativo</th><th scope="col">Identificador</th></tr></thead>
            <tbody>{data.items.map(resource => <tr key={resource.id}>
              <td><Link className="resource-link" to={'/inventory/' + encodeURIComponent(resource.id)}>{resource.display_name}<span aria-hidden="true"> ↗</span></Link></td>
              <td>{resourceTypeLabel(resource.resource_type)}</td>
              <td><ResourceState value={resource.administrative_state} /></td><td className="identifier">{resource.id}</td>
            </tr>)}</tbody>
          </table></div>}
        <div className="pagination"><p>Página <strong>{data.page}</strong> de {totalPages} · {data.total} recursos</p>
          <div><button className="button button-secondary button-small" disabled={data.page <= 1} onClick={() => change('page', String(data.page - 1))}>Anterior</button>
            <button className="button button-secondary button-small" disabled={data.page >= totalPages} onClick={() => change('page', String(data.page + 1))}>Seguinte</button></div>
        </div>
      </>}
    </section>
    <p className="context-note">O estado administrativo não indica a disponibilidade operacional do recurso.</p>
  </>;
}
