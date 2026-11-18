import { useCallback, useState } from 'react';
import { Link, useParams } from 'react-router';
import { ApiError, errorMessage, invalidResponse } from '../api/client';
import { resourceTypeLabel } from '../api/contracts';
import { getResource } from '../api/inventory';
import { useRemote } from '../api/useRemote';
import { ErrorNotice, Loading } from '../components/Feedback';
import { formatDate, ResourceState } from '../components/ResourceState';
import { useSession } from '../auth/SessionProvider';
import { ResourceDiscoverySection } from '../components/ResourceDiscoverySection';
import { ResourceIdentifiersSection } from '../components/ResourceIdentifiersSection';
import type { Resource } from '../api/contracts';

function resourceIdentity(id:string) {
  const value=id.toLowerCase().replace(/^urn:uuid:/,'').replace(/[{}-]/g,'');
  return /^[0-9a-f]{32}$/.test(value)?value:id;
}

export function ResourceDetailPage() {
  const { resourceId = '' } = useParams();
  // A real route identity change resets all local drafts, even if the next
  // resource is still loading. Refreshes of this UUID retain the mounted view.
  return <ResourceDetailView key={resourceIdentity(resourceId)} resourceId={resourceId}/>;
}

function ResourceDetailView({resourceId}:{resourceId:string}) {
  const { session } = useSession();
  const [snapshot,setSnapshot] = useState<Resource|null>(null);
  const load = useCallback(async (signal: AbortSignal) => {
    const data=await getResource(resourceId,signal);
    if(resourceIdentity(data.id)!==resourceIdentity(resourceId))return invalidResponse();
    if(!signal.aborted)setSnapshot(data);
    return data;
  }, [resourceId]);
  const { result, retry } = useRemote(load);
  const accessDenied=result.status==='error'&&result.error instanceof ApiError&&[401,403,404].includes(result.error.status);
  const resource = accessDenied?null:result.status === 'success'?result.data:snapshot;
  const refreshing=result.status!=='success';
  return <>
    <Link className="back-link" to="/inventory">← Voltar ao inventário</Link>
    <div className="page-heading"><div><p className="eyebrow">DETALHE DO RECURSO</p><h1>{resource?.display_name || 'Recurso'}</h1>
      <p className="muted">Identidade e informação administrativa.</p></div>
      {resource && <div className="page-actions"><ResourceState value={resource.administrative_state} />
        {!refreshing && session.user?.roles.includes('inventory_editor') && resource.administrative_state !== 'archived' && !resource.archived_at
          && <Link className="button" to={'/inventory/' + encodeURIComponent(resource.id) + '/edit'}>Editar</Link>}</div>}</div>
    {result.status === 'loading' && <section className="surface"><Loading label="A carregar o recurso…" /></section>}
    {result.status === 'error' && <ErrorNotice message={errorMessage(result.error)}
      retry={result.error instanceof ApiError && [403, 404].includes(result.error.status) ? undefined : retry} />}
    {resource && <div className="detail-grid">
      <section className="surface detail-panel"><h2>Informação geral</h2><dl>
        <div><dt>Identificador</dt><dd className="identifier">{resource.id}</dd></div>
        <div><dt>Tipo de recurso</dt><dd>{resourceTypeLabel(resource.resource_type)}</dd></div>
        <div><dt>Estado administrativo</dt><dd><ResourceState value={resource.administrative_state} /></dd></div>
        <div><dt>Descrição</dt><dd className="preserve-lines">{resource.description || 'Sem descrição.'}</dd></div>
      </dl></section>
      <section className="surface detail-panel"><h2>Registo</h2><dl>
        <div><dt>Criado em</dt><dd>{formatDate(resource.created_at)}</dd></div>
        <div><dt>Atualizado em</dt><dd>{formatDate(resource.updated_at)}</dd></div>
        <div><dt>Arquivado em</dt><dd>{formatDate(resource.archived_at)}</dd></div>
        <div><dt>Versão do registo</dt><dd>{resource.row_version}</dd></div>
      </dl></section>
      <ResourceDiscoverySection key={resource.id} resourceId={resource.id}/>
      <ResourceIdentifiersSection key={'identifiers-'+resource.id} resourceId={resource.id}
        archived={resource.administrative_state==='archived'||!!resource.archived_at} resourceRefreshing={refreshing} onChanged={retry}/>
      <section className="surface detail-panel attributes-panel"><h2>Atributos</h2>
        {Object.keys(resource.attributes).length ? <pre>{JSON.stringify(resource.attributes, null, 2)}</pre>
          : <p className="muted">Sem atributos adicionais.</p>}</section>
    </div>}
    <p className="context-note">O estado administrativo não indica a disponibilidade operacional do recurso.</p>
  </>;
}
