import { useCallback,useRef,useState } from 'react';
import { Link } from 'react-router';
import { useSession } from '../auth/SessionProvider';
import { useRemote } from '../api/useRemote';
import { ApiError,errorMessage } from '../api/client';
import { addIdentifier,closeIdentifier,getIdentifiers,coincidences } from '../api/identifiers';
import type { Coincidences,Identifier } from '../api/identifiers';
import { ErrorNotice,Loading } from './Feedback';
import { formatDate } from './ResourceState';

export function ResourceIdentifiersSection({resourceId,archived,resourceRefreshing=false,onChanged}:{resourceId:string;archived:boolean;resourceRefreshing?:boolean;onChanged:()=>void}) {
  const {session,expire}=useSession();const [state,setState]=useState('active');const [page,setPage]=useState(1);
  const load=useCallback((signal:AbortSignal)=>getIdentifiers(resourceId,state,page,signal),[resourceId,state,page]);
  const {result,retry}=useRemote(load);const data=result.status==='success'?result.data:null;
  const [value,setValue]=useState('');const [namespace,setNamespace]=useState('');const [conflict,setConflict]=useState<Coincidences|null>(null);
  const [closing,setClosing]=useState<Identifier|null>(null);const [error,setError]=useState<string|null>(null);
  const [pending,setPending]=useState(false);const [uncertain,setUncertain]=useState(false);const busy=useRef(false);
  const editor=session.user?.roles.includes('inventory_editor')&&!archived;
  async function mutate(close=false,confirm:Coincidences|null=null) {
    if(busy.current||!data||uncertain||resourceRefreshing)return;busy.current=true;setPending(true);setError(null);
    try {
      if(close&&closing)await closeIdentifier(resourceId,closing.id,data.resource_row_version);
      else await addIdentifier(resourceId,value,namespace,data.resource_row_version,confirm);
      setValue('');setConflict(null);setClosing(null);retry();onChanged();
    } catch(failure) {
      if(failure instanceof ApiError&&failure.status===401)expire();
      setError(errorMessage(failure));setConflict(coincidences(failure));
      const unknown=!(failure instanceof ApiError)||failure.status===0||failure.status>=500;
      setUncertain(unknown);
      if(failure instanceof ApiError&&['version_conflict','conflict_changed'].includes(failure.code)) {setConflict(null);retry();}
    } finally {busy.current=false;setPending(false);}
  }
  function view(next:string){setState(next);setPage(1);}
  async function review() {
    if(busy.current)return;busy.current=true;setPending(true);
    try {
      await getIdentifiers(resourceId,'all',1);
      setUncertain(false);setClosing(null);setConflict(null);setError('Leitura atualizada. Reveja as associações antes de uma nova ação.');
      view('active');retry();onChanged();
    } catch(failure){setError(errorMessage(failure));}
    finally{busy.current=false;setPending(false);}
  }
  return <section className="surface detail-panel attributes-panel" aria-labelledby="resource-identifiers-title">
    <h2 id="resource-identifiers-title">Identificadores</h2>
    <p>IPv4 declarados manualmente não comprovam identidade exclusiva ou disponibilidade. Não é efetuado contacto de rede.</p>
    <div className="page-actions"><button type="button" className="button button-secondary" onClick={()=>view('active')} disabled={pending}>IPv4 ativos</button>
      <button type="button" className="button button-secondary" onClick={()=>view('closed')} disabled={pending}>Histórico de identificadores</button></div>
    {result.status==='loading'&&<Loading label="A carregar identificadores…"/>}
    {result.status==='error'&&<ErrorNotice message={errorMessage(result.error)} retry={retry}/>}
    {data&&<>{!data.items.length?<p>{state==='active'?'Sem IPv4 ativos.':'Sem associações encerradas.'}</p>:<div className="table-scroll"><table><caption>{state==='active'?'IPv4 ativos':'Associações encerradas'}</caption>
      <thead><tr><th>IPv4</th><th>Namespace</th><th>Proveniência</th><th>Validade</th><th>Ação</th></tr></thead>
      <tbody>{data.items.map(item=><tr key={item.id}><td>{item.normalized_value}{item.identifier_value!==item.normalized_value&&<p>Original: {item.identifier_value}</p>}</td>
        <td>{item.namespace??'Sem contexto declarado'}</td><td>{item.source_type==='manual'?'Declaração manual':item.source_type}</td>
        <td>{formatDate(item.valid_from)} — {item.valid_until?formatDate(item.valid_until):'Em aberto'}</td>
        <td>{editor&&item.source_type==='manual'&&item.state==='active'&&<button type="button" className="button button-secondary" disabled={pending||uncertain||resourceRefreshing} onClick={()=>setClosing(item)}>Encerrar {item.normalized_value}</button>}</td></tr>)}</tbody>
    </table></div>}
    <div className="pagination"><p>Página {data.page} · {data.total} identificadores</p><div>
      <button type="button" className="button button-secondary" disabled={pending||data.page<=1} onClick={()=>setPage(page-1)}>Identificadores anteriores</button>
      <button type="button" className="button button-secondary" disabled={pending||data.page*data.per_page>=data.total} onClick={()=>setPage(page+1)}>Identificadores seguintes</button></div></div></>}
    {error&&<ErrorNotice message={error}/>}
    {uncertain&&<p role="status">Resultado incerto. Consulte os identificadores antes de qualquer nova ação. A escrita não será repetida automaticamente.</p>}
    {uncertain&&<button type="button" className="button button-secondary" disabled={pending} onClick={()=>void review()}>Consultar identificadores atuais</button>}
    {editor&&<form onSubmit={e=>{e.preventDefault();void mutate();}}>
      <label htmlFor="identifier-ipv4">Endereço IPv4</label><input id="identifier-ipv4" value={value} maxLength={64} disabled={pending||uncertain||resourceRefreshing} onChange={e=>{setValue(e.target.value);setConflict(null);}}/>
      <label htmlFor="identifier-namespace">Namespace lógico</label><input id="identifier-namespace" value={namespace} maxLength={255} disabled={pending||uncertain||resourceRefreshing} onChange={e=>{setNamespace(e.target.value);setConflict(null);}}/>
      <button className="button" disabled={!data||pending||uncertain||resourceRefreshing||!value||!namespace}>Adicionar IPv4</button>
    </form>}
    {conflict&&editor&&<div role="group" aria-label="Revisão da coincidência"><p>Existem associações coincidentes. Não ocorrerá fusão ou transferência.</p>
      <p>{conflict.visible_total} coincidências autorizadas; {conflict.conflicts.length} apresentadas.</p>
      {conflict.truncated&&<p role="status">Lista parcial: existem mais coincidências autorizadas do que as 20 apresentadas. A confirmação abrange a revisão integral das associações.</p>}
      <ul>{conflict.conflicts.map(c=><li key={c.identifier_id}><Link to={'/inventory/'+encodeURIComponent(c.resource_id)}>Consultar recurso coincidente</Link></li>)}</ul>
      <button type="button" className="button" disabled={pending||uncertain||resourceRefreshing||!data} onClick={()=>void mutate(false,conflict)}>Confirmo a coexistência neste namespace</button></div>}
    {closing&&editor&&<div role="group" aria-label="Confirmação de encerramento"><p>Encerrar {closing.normalized_value} em {closing.namespace}? O histórico será preservado.</p>
      <button type="button" className="button" disabled={pending||uncertain||resourceRefreshing||!data} onClick={()=>void mutate(true)}>Confirmar encerramento</button>
      <button type="button" className="button button-secondary" disabled={pending} onClick={()=>setClosing(null)}>Cancelar encerramento</button></div>}
  </section>;
}
