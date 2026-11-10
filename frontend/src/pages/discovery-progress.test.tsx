import { act,screen,within } from '@testing-library/react';
import { afterEach,describe,it,expect,vi } from 'vitest';
import { mockHttp,json,failure,user } from '../test/http';
import { renderApp } from '../test/renderApp';
import type { Handler } from '../test/http';

const one={id:'a1',ip:'10.42.0.10',hostname:null,outcome:'responded',observed_at:'2026-11-10T10:00:01Z',evidence:{method:'tcp_connect',ports:[{port:22,result:'connected'}]},decision:null};
const late={...one,id:'a2',ip:'10.42.0.2',observed_at:'2026-11-10T10:00:00Z'};
const noResponse={...one,id:'n1',ip:'10.42.0.11',outcome:'no_response',evidence:{method:'tcp_connect',ports:[{port:22,result:'timeout'}]}};
const error={...one,id:'e1',ip:'10.42.0.12',outcome:'error',evidence:{method:'tcp_connect',ports:[{port:445,result:'error'}]}};
const base={id:'job',target:'10.42.0.0/24',status:'running',processed:1,total:4,observations:[one]};
function http(handler:Handler) {
  return mockHttp((url,options)=>{
    if(url.pathname.endsWith('/auth/me'))return json({user:{...user,roles:['inventory_editor']}});
    if(url.pathname.endsWith('/auth/csrf'))return json({csrf_token:'test-progress-csrf'});
    return handler(url,options);
  });
}
async function open(){await act(async()=>{renderApp('/discovery/jobs/job');});}
async function tick(ms=1000){await act(async()=>{await vi.advanceTimersByTimeAsync(ms);});}
afterEach(()=>vi.useRealTimers());

describe('resultados e polling da Descoberta',()=>{
  it('mostra candidatos por defeito, contadores completos e filtros sem mutações',async()=>{
    const httpMock=http(()=>json({...base,status:'completed',processed:3,observations:[one,noResponse,error]}));
    await open();
    const table=screen.getByRole('table');
    expect(within(table).getByText(one.ip)).toBeInTheDocument();
    expect(within(table).queryByText(noResponse.ip)).not.toBeInTheDocument();
    const summaries=screen.getByLabelText('Resumo da descoberta');
    expect(summaries).toHaveTextContent('Processados/total3/4');
    expect(summaries).toHaveTextContent('Detetados1');expect(summaries).toHaveTextContent('Sem resposta1');expect(summaries).toHaveTextContent('Falhas de deteção1');
    const filter=screen.getByLabelText('Mostrar resultados') as HTMLSelectElement;
    await act(async()=>{filter.value='all';filter.dispatchEvent(new Event('change',{bubbles:true}));});
    expect(within(table).getByText(noResponse.ip)).toBeInTheDocument();
    expect(within(table).getByText(error.ip)).toBeInTheDocument();
    expect(within(table).getByText(/445: erro \(causa não preservada\)/)).toBeInTheDocument();
    await act(async()=>{filter.value='diagnostics';filter.dispatchEvent(new Event('change',{bubbles:true}));});
    expect(within(table).queryByText(one.ip)).not.toBeInTheDocument();
    expect(within(table).getByText(error.ip)).toBeInTheDocument();
    expect(httpMock.mock.calls.every(call=>call[1]?.method==='GET')).toBe(true);
  });

  it('mantém DOM, foco, scroll e ordem enquanto acrescenta resultados sem loading global',async()=>{
    vi.useFakeTimers();let reads=0;let finish!:(response:Response)=>void;
    http(()=>{reads++;return reads===1?json(base):new Promise<Response>(resolve=>{finish=resolve;});});
    await open();
    const table=screen.getByRole('table');const scroll=table.parentElement!;const filter=screen.getByLabelText('Mostrar resultados');
    const original=within(table).getByText(one.ip).closest('tr');scroll.scrollTop=63;scroll.scrollLeft=27;filter.focus();
    await tick();
    expect(screen.getByRole('table')).toBe(table);expect(screen.queryByText('A carregar…')).not.toBeInTheDocument();expect(filter).toHaveFocus();
    await act(async()=>{finish(json({...base,processed:2,observations:[late,one]}));});
    expect(screen.getByRole('table')).toBe(table);expect(within(table).getByText(one.ip).closest('tr')).toBe(original);
    expect([...table.querySelectorAll('tbody tr')].map(row=>row.firstChild?.textContent)).toEqual([one.ip,late.ip]);
    expect(filter).toHaveFocus();expect(scroll.scrollTop).toBe(63);expect(scroll.scrollLeft).toBe(27);
  });

  it('serializa GETs lentos e agrega pedidos manuais de atualização',async()=>{
    vi.useFakeTimers();let reads=0;let finish!:(response:Response)=>void;
    http(()=>{reads++;return reads===1?json(base):reads===2?new Promise<Response>(resolve=>{finish=resolve;}):json({...base,status:'completed'});});
    await open();await tick();expect(reads).toBe(2);
    await tick(10000);expect(reads).toBe(2);
    await act(async()=>{screen.getByRole('button',{name:'Atualizar resultados'}).click();screen.getByRole('button',{name:'Atualizar resultados'}).click();});
    expect(reads).toBe(2);
    await act(async()=>{finish(json({...base,processed:2}));});
    expect(reads).toBe(3);
    await tick(1);expect(reads).toBe(4); // one final read after the terminal response
    await tick(10000);expect(reads).toBe(4);
  });

  it('faz uma atualização final na transição terminal e depois para',async()=>{
    vi.useFakeTimers();let reads=0;
    http(()=>{reads++;return json(reads===1?base:reads===2?{...base,status:'completed'}:{...base,status:'completed',processed:2,observations:[one,late]});});
    await open();await tick();await tick(1);
    expect(reads).toBe(3);expect(screen.getByRole('status')).toHaveTextContent('Concluída');
    expect(within(screen.getByRole('table')).getByText(late.ip)).toBeInTheDocument();
    await tick(10000);expect(reads).toBe(3);
  });

  it('cancelar durante um GET lento agenda atualização sem sobrepor leituras',async()=>{
    vi.useFakeTimers();let reads=0,posts=0;let finish!:(response:Response)=>void;
    http((_,options)=>{
      if(options.method==='POST'){posts++;return json({...base,status:'cancelling'});}
      reads++;return reads===1?json(base):reads===2?new Promise<Response>(resolve=>{finish=resolve;}):json({...base,status:'cancelled'});
    });
    await open();const table=screen.getByRole('table');await tick();
    await act(async()=>{screen.getByRole('button',{name:'Cancelar descoberta'}).click();});
    expect(posts).toBe(1);expect(reads).toBe(2);
    expect(screen.getByRole('button',{name:'Cancelamento pedido'})).toBeDisabled();
    await act(async()=>{finish(json(base));});await tick(1);
    expect(reads).toBe(4);expect(screen.getByRole('status')).toHaveTextContent('Cancelada');
    expect(screen.getByRole('table')).toBe(table);
    await tick(10000);expect(reads).toBe(4);
  });

  it('abrir execução terminal não inicia polling desnecessário',async()=>{
    vi.useFakeTimers();let reads=0;http(()=>{reads++;return json({...base,status:'completed'});});
    await open();await tick(10000);expect(reads).toBe(1);
  });

  it('erro de atualização conserva resultados e exige retry explícito',async()=>{
    vi.useFakeTimers();let reads=0;
    http(()=>{reads++;return reads===1?json(base):reads===2?failure(503,'discovery_unavailable'):json({...base,status:'completed'});});
    await open();const table=screen.getByRole('table');await tick();
    expect(screen.getByRole('alert')).toHaveTextContent('indisponível');expect(screen.getByRole('table')).toBe(table);
    await tick(10000);expect(reads).toBe(2);
    await act(async()=>{screen.getByRole('button',{name:'Tentar novamente'}).click();});
    await tick(1);expect(screen.queryByRole('alert')).not.toBeInTheDocument();expect(screen.getByRole('table')).toBe(table);
  });

  it('mostra códigos futuros seguros e porta recusada como candidato',async()=>{
    const evidence={method:'tcp_connect',ports:[{port:22,result:'refused',code:'ECONNREFUSED',errno:111},{port:445,result:'local_error',code:'EACCES',errno:13},{port:443,result:'unreachable',code:'EHOSTUNREACH',errno:113}]};
    http(()=>json({...base,status:'completed',observations:[{...one,evidence}]}));
    await open();expect(screen.getByText('Candidato')).toBeInTheDocument();
    expect(screen.getByText(/445: erro local \(EACCES, errno 13\)/)).toBeInTheDocument();
    expect(screen.getByText(/443: inalcançável \(EHOSTUNREACH, errno 113\)/)).toBeInTheDocument();
  });
});
