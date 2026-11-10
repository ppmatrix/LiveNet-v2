import { useCallback,useRef,useState } from 'react';
import { Link,useNavigate,useParams } from 'react-router';
import { useRemote } from '../api/useRemote';
import { ApiError,errorMessage } from '../api/client';
import { getDiscoveryConfig,getJobs,startJob,cancelJob,getCandidate,createFromCandidate,associateCandidate } from '../api/discovery';
import { useSession } from '../auth/SessionProvider';
import { ErrorNotice,Loading } from '../components/Feedback';
import { formatDate } from '../components/ResourceState';
import { useDiscoveryJob,discoveryActive } from '../api/useDiscoveryJob';
import { DiscoveryEvidence } from '../components/DiscoveryEvidence';
import { ResourceForm } from './ResourceFormPage';

const statuses:Record<string,string>={queued:'Em fila',running:'Em execução',cancelling:'A cancelar',cancelled:'Cancelada',completed:'Concluída',interrupted:'Interrompida',failed:'Falhou',timed_out:'Tempo esgotado'};

export function DiscoveryPage() {
  const { session,expire }=useSession();const navigate=useNavigate();
  const load=useCallback(async (signal:AbortSignal)=>{const config=await getDiscoveryConfig(signal);return {config,jobs:config.enabled?await getJobs(signal):[]};},[]);
  const {result,retry}=useRemote(load);
  const [target,setTarget]=useState('');const [pending,setPending]=useState(false);const [error,setError]=useState<string|null>(null);const [uncertain,setUncertain]=useState(false);const busy=useRef(false);
  async function start(event:React.FormEvent) {
    event.preventDefault();if(busy.current)return;
    if(!target.trim()){setError('Indique uma rede IPv4 CIDR ou intervalo início-fim.');return;}
    busy.current=true;setPending(true);setError(null);
    try { const job=await startJob(target.trim());navigate('/discovery/jobs/'+job.id); }
    catch(failure) {
      if(failure instanceof ApiError&&failure.status===401)expire();
      else {setError(failure instanceof ApiError&&failure.status===400?'Alvos inválidos, fora das redes autorizadas ou acima do limite.':errorMessage(failure));setUncertain(!(failure instanceof ApiError)||failure.status===0||failure.status>=500);}
    } finally {busy.current=false;setPending(false);}
  }
  return <><div className="page-heading"><div><p className="eyebrow">OBSERVAÇÕES DE REDE</p><h1>Descoberta</h1>
    <p className="muted">Resultados são candidatos; a adição ao Inventory é sempre manual.</p></div></div>
    {result.status==='loading'&&<Loading/>}
    {result.status==='error'&&<ErrorNotice message={errorMessage(result.error)} retry={retry}/>}
    {result.status==='success'&&(!result.data.config.enabled?<ErrorNotice message="A Descoberta precisa de redes autorizadas e migração preparada pelo administrador."/>:<>
      <section className="surface detail-panel"><h2>Deteção TCP sem credenciais</h2>
        <p>Redes autorizadas: {result.data.config.policy!.networks.join(', ')}. Portas: {result.data.config.policy!.ports.join(', ')}.</p>
        <p className="context-note">Máximo {result.data.config.policy!.max_targets} alvos; {result.data.config.policy!.concurrency} ligações em paralelo; timeout por ligação {result.data.config.policy!.target_timeout}s; execução até {result.data.config.policy!.job_timeout}s.</p>
        {session.user?.roles.includes('inventory_editor')&&<form onSubmit={start}>
          <label htmlFor="discovery-target">Rede IPv4 CIDR ou intervalo IP</label><input id="discovery-target" value={target} maxLength={80} onChange={event=>setTarget(event.target.value)} disabled={pending} placeholder="CIDR ou início-fim"/>
          {error&&<ErrorNotice message={error}/>}
          <div className="page-actions"><button className="button" disabled={pending||uncertain}>{pending?'A iniciar…':'Iniciar descoberta'}</button>
            {uncertain&&<button type="button" className="button button-secondary" onClick={()=>{retry();setError('Consulte as execuções antes de voltar a iniciar.');}}>Consultar execuções</button>}</div>
        </form>}
      </section>
      <section className="surface detail-panel"><h2>Execuções recentes (até 50)</h2>
        {!result.data.jobs.length?<p>Sem execuções.</p>:<ul>{result.data.jobs.map(job=><li key={job.id}><Link to={'/discovery/jobs/'+job.id}>{job.target}</Link> — {statuses[job.status]||job.status} · {job.processed}/{job.total}</li>)}</ul>}
      </section>
    </>)}
    <p className="context-note">Ausência de resposta não significa equipamento desligado ou inexistente. Uma resposta TCP pode provir de equipamento intermédio e não comprova identidade. Não altera o estado administrativo do Inventory.</p>
  </>;
}

export function DiscoveryJobPage() {
  const {jobId=''}=useParams();
  return <DiscoveryJobView key={jobId} jobId={jobId}/>;
}

function DiscoveryJobView({jobId}:{jobId:string}) {
  const {session,expire}=useSession();
  const {data,error:readError,refreshing,refresh}=useDiscoveryJob(jobId);
  const [pending,setPending]=useState(false);const [cancelRequested,setCancelRequested]=useState(false);
  const [error,setError]=useState<string|null>(null);const [filter,setFilter]=useState('detected');const busy=useRef(false);
  async function cancel(){
    if(busy.current||cancelRequested)return;
    busy.current=true;setPending(true);setError(null);
    try{await cancelJob(jobId);setCancelRequested(true);refresh();}
    catch(failure){if(failure instanceof ApiError&&failure.status===401)expire();else setError(errorMessage(failure));}
    finally{busy.current=false;setPending(false);}
  }
  const observations=data?.observations||[];
  const detected=observations.filter(o=>o.outcome==='responded').length;
  const noResponse=observations.filter(o=>o.outcome==='no_response').length;
  const failed=observations.filter(o=>o.outcome==='error').length;
  const visible=observations.filter(o=>filter==='all'||(filter==='detected'?o.outcome==='responded':
    o.outcome!=='responded'||o.evidence.ports.some(p=>p.result!=='connected')));
  return <><Link className="back-link" to="/discovery">← Voltar à Descoberta</Link><h1>Execução de descoberta</h1>
    {error&&<ErrorNotice message={error}/>}
    {readError&&<ErrorNotice message={errorMessage(readError)} retry={refresh}/>}
    {!data&&!readError&&<Loading/>}
    {data&&<section className="surface detail-panel" aria-busy={refreshing}><h2>{data.target}</h2>
      <p role="status">{statuses[data.status]||data.status} · {data.processed}/{data.total} alvos processados</p>
      <progress value={data.processed} max={data.total} aria-label="Progresso da descoberta"/>
      <dl className="discovery-summary" aria-label="Resumo da descoberta">
        <div><dt>Processados/total</dt><dd>{data.processed}/{data.total}</dd></div>
        <div><dt>Detetados</dt><dd>{detected}</dd></div>
        <div><dt>Sem resposta</dt><dd>{noResponse}</dd></div>
        <div><dt>Falhas de deteção</dt><dd>{failed}</dd></div>
      </dl>
      <div className="page-actions">
        {session.user?.roles.includes('inventory_editor')&&['queued','running'].includes(data.status)&&<button className="button button-secondary" disabled={pending||cancelRequested} onClick={()=>void cancel()}>{cancelRequested?'Cancelamento pedido':'Cancelar descoberta'}</button>}
        <button className="button button-secondary" onClick={refresh}>Atualizar resultados</button>
      </div>
      <p className="context-note">O cancelamento interrompe novos alvos; ligações em curso terminam dentro do timeout e a evidência é preservada.</p>
      <label htmlFor="discovery-result-filter">Mostrar resultados</label>
      <select id="discovery-result-filter" value={filter} onChange={event=>setFilter(event.target.value)}>
        <option value="detected">Candidatos detetados</option><option value="all">Todos os resultados</option><option value="diagnostics">Diagnósticos</option>
      </select>
      <p className="context-note">Ordem de chegada; novos resultados são acrescentados no fim. Diagnósticos incluem portas recusadas, timeouts e erros. Os contadores referem-se a alvos.</p>
      <div className="table-scroll"><table className="discovery-results"><caption>Observações e candidatos desta execução</caption>
        <colgroup><col style={{width:160}}/><col style={{width:150}}/><col/><col style={{width:190}}/><col style={{width:170}}/></colgroup>
        <thead><tr><th>IP</th><th>Resultado</th><th>Evidência</th><th>Observado em</th><th>Decisão</th></tr></thead>
        <tbody>{visible.map(o=><tr key={o.id}><td>{o.ip}</td><td>{o.outcome==='responded'?'Candidato':o.outcome==='error'?'Falha de deteção':'Sem resposta'}</td>
          <td><DiscoveryEvidence evidence={o.evidence}/></td><td>{formatDate(o.observed_at)}</td><td>
            {o.decision?<Link to={'/inventory/'+o.decision.resource_id}>Recurso associado</Link>:o.outcome==='responded'?<Link to={'/discovery/candidates/'+o.id}>Rever candidato</Link>:'Sem candidato'}</td></tr>)}</tbody></table></div>
      {!visible.length&&<p role="note">{discoveryActive(data.status)?'Ainda não há resultados para este filtro.':'Nenhum resultado para este filtro.'}</p>}
      <p>Sem resposta não significa desligado/inexistente. Uma porta recusada não é, por si só, falha do alvo. Candidato não é recurso consolidado.</p>
    </section>}
  </>;
}

export function DiscoveryCandidatePage() {
  const {candidateId=''}=useParams();const {session}=useSession();const navigate=useNavigate();
  const load=useCallback((signal:AbortSignal)=>getCandidate(candidateId,signal),[candidateId]);const {result,retry}=useRemote(load);
  const [creating,setCreating]=useState(false);const [distinct,setDistinct]=useState(false);const [resourceId,setResourceId]=useState('');const [pending,setPending]=useState(false);const [error,setError]=useState<string|null>(null);const busy=useRef(false);
  async function associate(id:string){if(busy.current||creating)return;busy.current=true;setPending(true);setError(null);try{const resource=await associateCandidate(candidateId,id);navigate('/inventory/'+resource.id);}catch(failure){setError(errorMessage(failure));retry();}finally{busy.current=false;setPending(false);}}
  if(result.status==='loading')return <Loading/>;
  if(result.status==='error')return <ErrorNotice message={errorMessage(result.error)} retry={retry}/>;
  const candidate=result.data;const canEdit=session.user?.roles.includes('inventory_editor');
  const needsReview=!!(candidate.possible_matches.length||candidate.previous_observations.length||candidate.matches_truncated);
  return <><Link className="back-link" to="/discovery">← Voltar à Descoberta</Link><h1>Rever candidato</h1>
    <section className="surface detail-panel"><h2>Observação: {candidate.ip}</h2><p>Nome: não obtido. Tipo: não determinado.</p>
      <p><DiscoveryEvidence evidence={candidate.evidence}/> · {formatDate(candidate.observed_at)}</p>
      <p>IP isolado não prova identidade. Não é feita fusão, reativação ou sobrescrita automática.</p>
      {candidate.decision?<p>Decisão já registada: <Link to={'/inventory/'+candidate.decision.resource_id}>Consultar recurso consolidado</Link></p>:<>
        <h2>Possíveis correspondências</h2>
        {candidate.possible_matches.length?<ul>{candidate.possible_matches.map(m=><li key={m.id}><Link to={'/inventory/'+m.id}>{m.display_name}</Link> ({m.administrative_state})
          {canEdit&&<button className="button button-secondary button-small" disabled={pending||creating} onClick={()=>void associate(m.id)}>Associar a {m.display_name}</button>}</li>)}</ul>:<p>Nenhuma correspondência indicada; isto não prova que seja uma máquina nova.</p>}
        {candidate.matches_truncated&&<p>Existem mais correspondências. Consulte o Inventory antes de decidir.</p>}
        {!!candidate.previous_observations.length&&<><h2>Observações anteriores deste IP (até 20)</h2><ul>{candidate.previous_observations.map(o=><li key={o.id}><Link to={'/discovery/jobs/'+o.job_id}>{formatDate(o.observed_at)}</Link> — {o.outcome}</li>)}</ul></>}
        {canEdit&&<><label htmlFor="associate-resource">UUID de outro recurso existente (associação manual)</label>
          <input id="associate-resource" value={resourceId} onChange={event=>setResourceId(event.target.value)} disabled={pending||creating}/>
          <button className="button button-secondary" disabled={pending||creating||!resourceId.trim()} onClick={()=>void associate(resourceId.trim())}>Associar ao UUID indicado</button>
          <p className="context-note">A associação conserva o recurso, incluindo o estado administrativo, e não o reativa.</p>
          {needsReview&&<label className="discovery-confirmation"><input type="checkbox" disabled={pending||creating} checked={distinct} onChange={event=>setDistinct(event.target.checked)}/><span>Revi as observações e correspondências e pretendo criar um recurso distinto.</span></label>}</>}
      </>}
      {error&&<ErrorNotice message={error}/>}
    </section>
    {!candidate.decision&&canEdit&&(!needsReview||distinct)&&!pending&&<ResourceForm onPendingChange={setCreating} candidateSave={data=>createFromCandidate(candidateId,data,distinct)}/>}
  </>;
}
