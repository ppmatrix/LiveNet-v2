import { screen,within,waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe,it,expect } from 'vitest';
import { mockHttp,json,failure,resource,user } from '../test/http';
import { renderApp } from '../test/renderApp';
const first={id:'first-observation',job_id:'first-job',ip:'10.42.0.160',hostname:null,outcome:'responded',observed_at:'2026-11-10T10:00:00Z',
  evidence:{method:'tcp_connect',ports:[{port:22,result:'connected'},{port:445,result:'refused',code:'ECONNREFUSED',errno:111}]},
  decision:{mode:'create',resource_id:resource.id,decided_at:'2026-11-10T11:00:00Z'}};
const second={...first,id:'second-observation',job_id:'second-job',ip:'10.42.0.161',observed_at:'2026-11-10T12:00:00Z',
  decision:{...first.decision,mode:'associate',decided_at:'2026-11-10T13:00:00Z'}};
function history(items:unknown[]=[second,first],total=items.length,page=1){return {resource_id:resource.id,items,total,page,per_page:20};}
function http(handler:(url:URL)=>Response){
  return mockHttp((url)=>{
    if(url.pathname.endsWith('/auth/me'))return json({user});
    if(url.pathname.endsWith('/auth/csrf'))return json({csrf_token:'test-resource-history'});
    if(url.pathname.endsWith('/inventory/resources/'+resource.id))return json({...resource,display_name:'ecEng',resource_type:'container'});
    return handler(url);
  });
}
describe('Descoberta no detalhe do recurso',()=>{
  it('mostra IP histórico, datas, evidência, tipos de decisão e ligação à execução',async()=>{
    const mock=http(url=>url.pathname.endsWith('/history')?json(history()):json({id:'second-job',target:'10.42.0.161/32',status:'completed',processed:1,total:1,observations:[]}));
    renderApp('/inventory/'+resource.id);
    await screen.findByRole('heading',{name:'ecEng'});
    const section=await screen.findByRole('region',{name:'Descoberta'});
    await within(section).findByRole('table');
    expect(within(section).getByText(/não uma identidade permanente/)).toBeInTheDocument();
    expect(within(section).getByText(/disponibilidade atual/)).toBeInTheDocument();
    expect(within(section).getByText(first.ip)).toBeInTheDocument();expect(within(section).getByText(second.ip)).toBeInTheDocument();
    expect(within(section).getByText('Adicionado')).toBeInTheDocument();expect(within(section).getByText('Associado')).toBeInTheDocument();
    expect(section.querySelector('time[datetime="'+first.observed_at+'"]')).not.toBeNull();
    expect(section.querySelector('time[datetime="'+second.decision.decided_at+'"]')).not.toBeNull();
    expect(within(section).getAllByText(/445: ligação recusada \(ECONNREFUSED/)).toHaveLength(2);
    const links=within(section).getAllByRole('link',{name:'Ver execução'});
    expect(links[0]).toHaveAttribute('href','/discovery/jobs/second-job');
    await userEvent.click(links[0]!);await screen.findByRole('heading',{name:'Execução de descoberta'});
    expect(mock.mock.calls.every(call=>call[1]?.method==='GET')).toBe(true);
  });
  it('mantém o detalhe normal quando não há histórico',async()=>{
    http(()=>json(history([])));renderApp('/inventory/'+resource.id);
    await screen.findByText('Sem observações de Descoberta associadas a este recurso.');
    expect(screen.getByRole('heading',{name:'ecEng'})).toBeInTheDocument();
    expect(screen.getByText('Contentor')).toBeInTheDocument();expect(screen.getByText('Versão do registo')).toBeInTheDocument();
    expect(screen.queryByRole('link',{name:'Ver execução'})).not.toBeInTheDocument();
  });
  it('falha do histórico não remove o detalhe e permite repetir só a leitura',async()=>{
    let available=false;http(()=>available?json(history()):failure(503,'discovery_unavailable'));
    renderApp('/inventory/'+resource.id);
    expect(await screen.findByRole('alert')).toHaveTextContent('histórico de Descoberta');
    expect(screen.getByRole('heading',{name:'ecEng'})).toBeInTheDocument();expect(screen.queryByText(/Texto interno/)).not.toBeInTheDocument();
    available=true;await userEvent.click(screen.getByRole('button',{name:'Tentar novamente'}));
    await screen.findByText(first.ip);
  });
  it('pagina sem ocultar ou truncar silenciosamente observações anteriores',async()=>{
    const mock=http(url=>json(url.searchParams.get('page')==='2'?history([first],21,2):history([second],21,1)));
    renderApp('/inventory/'+resource.id);await screen.findByText(second.ip);
    await userEvent.click(screen.getByRole('button',{name:'Observações seguintes'}));
    await screen.findByText(first.ip);
    expect(screen.getByRole('button',{name:'Observações seguintes'})).toBeDisabled();
    expect(screen.getByRole('button',{name:'Observações anteriores'})).toBeEnabled();
    expect(new URL(String(mock.mock.calls.at(-1)![0])).searchParams.get('page')).toBe('2');
  });
  it('não solicita histórico de recurso inacessível',async()=>{
    const mock=mockHttp(url=>url.pathname.endsWith('/auth/me')?json({user}):url.pathname.endsWith('/auth/csrf')?json({csrf_token:'test'}):failure(404,'not_found'));
    renderApp('/inventory/'+resource.id);await screen.findByRole('alert');
    expect(mock.mock.calls.some(call=>String(call[0]).includes('/history'))).toBe(false);
    expect(screen.queryByRole('region',{name:'Descoberta'})).not.toBeInTheDocument();
  });
  it('recusa uma resposta de histórico ligada a outro recurso',async()=>{
    http(()=>json(history([{...first,decision:{...first.decision,resource_id:'outro-recurso'}}])));
    renderApp('/inventory/'+resource.id);
    await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('resposta incompatível'));
    expect(screen.queryByText(first.ip)).not.toBeInTheDocument();
  });
});
