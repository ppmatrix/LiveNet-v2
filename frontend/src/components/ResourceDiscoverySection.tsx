import { useCallback,useState } from 'react';
import { Link } from 'react-router';
import { getResourceDiscoveryHistory } from '../api/discovery';
import { useRemote } from '../api/useRemote';
import { ApiError,errorMessage } from '../api/client';
import { DiscoveryEvidence } from './DiscoveryEvidence';
import { ErrorNotice,Loading } from './Feedback';
import { formatDate } from './ResourceState';

export function ResourceDiscoverySection({resourceId}:{resourceId:string}) {
  const [page,setPage]=useState(1);
  const load=useCallback((signal:AbortSignal)=>getResourceDiscoveryHistory(resourceId,page,signal),[resourceId,page]);
  const {result,retry}=useRemote(load);
  const data=result.status==='success'?result.data:null;
  return <section className="surface detail-panel attributes-panel" aria-labelledby="resource-discovery-title">
    <h2 id="resource-discovery-title">Descoberta</h2>
    <p>O IP abaixo é uma observação histórica, não uma identidade permanente nem uma indicação de disponibilidade atual.</p>
    {result.status==='loading'&&<Loading label="A carregar o histórico de Descoberta…"/>}
    {result.status==='error'&&<ErrorNotice message={'Não foi possível consultar o histórico de Descoberta. '+errorMessage(result.error)}
      retry={result.error instanceof ApiError&&[403,404].includes(result.error.status)?undefined:retry}/>}
    {data&&(data.total===0?<p>Sem observações de Descoberta associadas a este recurso.</p>:<>
      <p>Histórico de observações adicionadas ou associadas por decisão explícita. Mais recentes primeiro.</p>
      <div className="table-scroll"><table><caption>Histórico de Descoberta do recurso</caption>
        <thead><tr><th scope="col">IP observado</th><th scope="col">Observado em</th><th scope="col">Evidência TCP</th><th scope="col">Decisão</th><th scope="col">Execução original</th></tr></thead>
        <tbody>{data.items.map(item=><tr key={item.id}>
          <td className="identifier">{item.ip}</td><td><time dateTime={item.observed_at}>{formatDate(item.observed_at)}</time></td>
          <td><DiscoveryEvidence evidence={item.evidence}/></td>
          <td>{item.decision.mode==='create'?'Adicionado':'Associado'}<p className="context-note">Decidido em <time dateTime={item.decision.decided_at}>{formatDate(item.decision.decided_at)}</time></p></td>
          <td><Link to={'/discovery/jobs/'+encodeURIComponent(item.job_id)}>Ver execução</Link></td>
        </tr>)}</tbody>
      </table></div>
      <div className="pagination"><p>Página {data.page} · {data.total} observações associadas</p><div>
        <button className="button button-secondary button-small" disabled={data.page<=1} onClick={()=>setPage(data.page-1)}>Observações anteriores</button>
        <button className="button button-secondary button-small" disabled={data.page*data.per_page>=data.total} onClick={()=>setPage(data.page+1)}>Observações seguintes</button>
      </div></div>
    </>)}
  </section>;
}
