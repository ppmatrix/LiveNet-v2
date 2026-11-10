import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe,it,expect } from 'vitest';
import { mockHttp,json,failure,resource,user } from '../test/http';
import type { Handler } from '../test/http';
import { renderApp } from '../test/renderApp';
const config={enabled:true,policy:{networks:['10.42.0.0/24'],ports:[22,443],max_targets:16,concurrency:2,target_timeout:.2,job_timeout:2,max_jobs:2}};
const observation={id:'710818f5-07aa-4ae0-b198-ed5fa53277ac',ip:'10.42.0.5',hostname:null,outcome:'responded',observed_at:'2026-11-08T12:00:00Z',evidence:{method:'tcp_connect',ports:[{port:22,result:'refused'}]},decision:null};
const job={id:'aa47bc28-853d-41c0-9596-c02cbce6ebce',target:'10.42.0.5/32',status:'completed',total:1,processed:1,observations:[observation]};
const candidate={...observation,possible_matches:[],matches_truncated:false,previous_observations:[]};
function http(handler:Handler,editor=true) {
  return mockHttp((url,options)=>{
    if(url.pathname.endsWith('/auth/me'))return json({user:{...user,roles:editor?['inventory_editor']:['inventory_reader']}});
    if(url.pathname.endsWith('/auth/csrf'))return json({csrf_token:'discovery-test-csrf'});
    if(url.pathname.endsWith('/discovery/config'))return json(config);
    return handler(url,options);
  });
}
describe('Descoberta manual',()=>{
  it('liga rede, execução, revisão e recurso sem inventar nome ou tipo',async()=>{
    const writes:RequestInit[]=[];let saved={...resource};
    http((url,options)=>{
      if(options.method==='POST') {
        writes.push(options);expect(options.headers).toMatchObject({'X-CSRF-Token':'discovery-test-csrf'});
        if(url.pathname.endsWith('/jobs'))return json(job,202);
        const data=JSON.parse(String(options.body));expect(data.mode).toBe('create');expect(data.confirm_distinct).toBe(false);
        saved={...resource,...data.resource};return json({resource:saved,already_decided:false});
      }
      if(url.pathname.endsWith('/discovery/jobs'))return json({items:[]});
      if(url.pathname.includes('/discovery/jobs/'))return json(job);
      if(url.pathname.includes('/discovery/candidates/'))return json(candidate);
      return json(saved);
    });
    renderApp('/discovery');
    await userEvent.type(await screen.findByLabelText('Rede IPv4 CIDR ou intervalo IP'),'10.42.0.5/32');
    await userEvent.click(screen.getByRole('button',{name:'Iniciar descoberta'}));
    expect(await screen.findByRole('progressbar')).toHaveAttribute('value','1');
    await userEvent.click(await screen.findByRole('link',{name:'Rever candidato'}));
    expect(await screen.findByText('Nome: não obtido. Tipo: não determinado.')).toBeInTheDocument();
    expect(screen.getByLabelText('Nome')).toHaveValue('');expect(screen.getByLabelText('Tipo de recurso')).toHaveValue('');
    await userEvent.type(screen.getByLabelText('Nome'),'Máquina revista');
    await userEvent.click(screen.getByRole('button',{name:'Guardar recurso'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Selecione o tipo');expect(writes).toHaveLength(1);
    await userEvent.selectOptions(screen.getByLabelText('Tipo de recurso'),'service');
    await userEvent.click(screen.getByRole('button',{name:'Guardar recurso'}));
    await screen.findByRole('heading',{name:'Máquina revista'});expect(writes).toHaveLength(2);
    expect(JSON.parse(String(writes[1]!.body)).resource).not.toHaveProperty('credentials');
  });
  it('preserva alvos após recusa do servidor',async()=>{
    let writes=0;
    http((_,options)=>{if(options.method==='POST'){writes++;return failure(400,'invalid_request');}return json({items:[]});});
    renderApp('/discovery');
    await userEvent.type(await screen.findByLabelText('Rede IPv4 CIDR ou intervalo IP'),'8.8.8.8/32');
    await userEvent.click(screen.getByRole('button',{name:'Iniciar descoberta'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('fora das redes autorizadas');
    expect(screen.getByLabelText('Rede IPv4 CIDR ou intervalo IP')).toHaveValue('8.8.8.8/32');expect(writes).toBe(1);
  });
  it('cancela a execução e mostra o estado devolvido pelo servidor',async()=>{
    let cancelled=false;let writes=0;
    http((_,options)=>{if(options.method==='POST'){writes++;cancelled=true;}return json({...job,status:cancelled?'cancelled':'running',processed:0,observations:[]});});
    renderApp('/discovery/jobs/'+job.id);
    await userEvent.click(await screen.findByRole('button',{name:'Cancelar descoberta'}));
    expect(await screen.findByRole('status')).toHaveTextContent('Cancelada');
    expect(screen.queryByRole('button',{name:'Cancelar descoberta'})).not.toBeInTheDocument();expect(writes).toBe(1);
  });
  it('associa manualmente uma possível correspondência sem reativar',async()=>{
    let decision:unknown;
    http((url,options)=>{
      if(options.method==='POST'){decision=JSON.parse(String(options.body));return json({resource:{...resource,administrative_state:'archived'},already_decided:false});}
      if(url.pathname.includes('/discovery/'))return json({...candidate,possible_matches:[{id:resource.id,display_name:resource.display_name,administrative_state:'archived'}]});
      return json({...resource,administrative_state:'archived'});
    });
    renderApp('/discovery/candidates/'+candidate.id);await screen.findByRole('heading',{name:'Rever candidato'});
    expect(screen.queryByRole('button',{name:'Guardar recurso'})).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button',{name:'Associar a '+resource.display_name}));
    await screen.findByRole('heading',{name:resource.display_name});expect(decision).toEqual({mode:'associate',resource_id:resource.id});
    expect(screen.queryByRole('link',{name:'Editar'})).not.toBeInTheDocument();
  });
  it('não oferece adição para candidato já decidido ou reader',async()=>{
    const mock=http(()=>json({...candidate,decision:{mode:'create',resource_id:resource.id,decided_at:'2026-11-08T12:00:00Z'}}),false);
    renderApp('/discovery/candidates/'+candidate.id);
    expect(await screen.findByRole('link',{name:'Consultar recurso consolidado'})).toHaveAttribute('href','/inventory/'+resource.id);
    expect(screen.queryByLabelText('Nome')).not.toBeInTheDocument();expect(mock.mock.calls.every(call=>call[1]?.method==='GET')).toBe(true);
  });
  it('não inicia rede sem configuração administrativa',async()=>{
    const mock=mockHttp(url=>url.pathname.endsWith('/auth/me')?json({user}):url.pathname.endsWith('/auth/csrf')?json({csrf_token:'test-csrf'}):json({enabled:false,policy:null}));
    renderApp('/discovery');expect(await screen.findByRole('alert')).toHaveTextContent('redes autorizadas');
    expect(screen.queryByRole('button',{name:'Iniciar descoberta'})).not.toBeInTheDocument();expect(mock.mock.calls.every(call=>call[1]?.method==='GET')).toBe(true);
  });
});
