import { act,screen,within,waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe,it,expect } from 'vitest';
import { mockHttp,json,failure,resource,user } from '../test/http';
import type { Handler } from '../test/http';
import { renderApp } from '../test/renderApp';

const item={id:'d75fc632-e507-4cfa-9ca3-0fc9d9b48c05',resource_id:resource.id,identifier_value:'10.42.0.1',normalized_value:'10.42.0.1',
  namespace:'lab',source_type:'manual',source_instance:user.id,state:'active',valid_from:'2026-11-18T10:00:00Z',valid_until:null};
function page(items:unknown[]=[item],version=1,number=1,total=items.length){return {items,total,page:number,per_page:20,resource_row_version:version};}
function http(handler:Handler,roles=['inventory_editor'],archived=false,getVersion=()=>1,parentLoad?:()=>Response|Promise<Response>){
  return mockHttp((url,options)=>{
    if(url.pathname.endsWith('/auth/me'))return json({user:{...user,roles}});
    if(url.pathname.endsWith('/auth/csrf'))return json({csrf_token:'identifier-csrf'});
    if(url.pathname.endsWith('/inventory/resources/'+resource.id))return parentLoad?parentLoad():json({...resource,row_version:getVersion(),administrative_state:archived?'archived':'active'});
    if(url.pathname.endsWith('/history'))return json({resource_id:resource.id,items:[],total:0,page:1,per_page:20});
    return handler(url,options);
  });
}
async function fill(){
  await userEvent.type(await screen.findByLabelText('Endereço IPv4'),'10.42.0.1');
  await userEvent.type(screen.getByLabelText('Namespace lógico'),'lab');
}
describe('Identificadores manuais',()=>{
  it('adiciona com CSRF, atualiza versão e não executa deteção',async()=>{
    let saved=false,version=1;const writes:RequestInit[]=[];
    const mock=http((_url,options)=>{
      if(options.method==='POST'){writes.push(options);expect(options.headers).toMatchObject({'X-CSRF-Token':'identifier-csrf'});expect(JSON.parse(String(options.body))).toMatchObject({row_version:1,confirm_shared:false});saved=true;version=2;return json({identifier:item,changed:true,resource_row_version:2},201);}
      return json(page(saved?[item]:[],version));
    },['inventory_editor'],false,()=>version);
    renderApp('/inventory/'+resource.id);await fill();await userEvent.click(screen.getByRole('button',{name:'Adicionar IPv4'}));
    expect(await screen.findByRole('button',{name:'Encerrar 10.42.0.1'})).toBeEnabled();
    expect(screen.getByText('Versão do registo').nextElementSibling).toHaveTextContent('2');
    expect(writes).toHaveLength(1);expect(mock.mock.calls.some(c=>String(c[0]).includes('/discovery/jobs'))).toBe(false);
  });
  it('exige confirmação atualizada de coincidência',async()=>{
    let writes=0;
    http((_url,options)=>{
      if(options.method==='POST'){
        writes++;const body=JSON.parse(String(options.body));
        if(writes===1)return json({error:{code:'identifier_conflict'},details:{conflict_revision:'a'.repeat(64),conflicts:[{resource_id:'peer',identifier_id:'peer-id'}],visible_total:1,truncated:false}},409);
        expect(body).toMatchObject({confirm_shared:true,conflict_revision:'a'.repeat(64)});
        return json({error:{code:'conflict_changed'},details:{conflict_revision:'b'.repeat(64),conflicts:[],visible_total:0,truncated:false}},409);
      }
      return json(page([]));
    });
    renderApp('/inventory/'+resource.id);await fill();await userEvent.click(screen.getByRole('button',{name:'Adicionar IPv4'}));
    await userEvent.click(await screen.findByRole('button',{name:'Confirmo a coexistência neste namespace'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('mudaram');
    expect(screen.queryByRole('button',{name:'Confirmo a coexistência neste namespace'})).not.toBeInTheDocument();expect(writes).toBe(2);
  });
  it('encerra apenas após confirmação e mostra histórico paginado',async()=>{
    let writes=0;http((url,options)=>{
      if(options.method==='POST'){writes++;return json({identifier:{...item,state:'closed',valid_until:'2026-11-18T11:00:00Z'},resource_row_version:2,changed:true});}
      return json(url.searchParams.get('state')==='closed'?page([{...item,state:'closed',valid_until:'2026-11-18T11:00:00Z'}],2,Number(url.searchParams.get('page')),21):page());
    });
    renderApp('/inventory/'+resource.id);await userEvent.click(await screen.findByRole('button',{name:'Encerrar 10.42.0.1'}));expect(writes).toBe(0);
    await userEvent.click(screen.getByRole('button',{name:'Cancelar encerramento'}));expect(writes).toBe(0);
    await userEvent.click(screen.getByRole('button',{name:'Encerrar 10.42.0.1'}));await userEvent.click(screen.getByRole('button',{name:'Confirmar encerramento'}));
    await waitFor(()=>expect(writes).toBe(1));await userEvent.click(await screen.findByRole('button',{name:'Histórico de identificadores'}));
    await userEvent.click(await screen.findByRole('button',{name:'Identificadores seguintes'}));
    await waitFor(()=>expect(within(screen.getByRole('region',{name:'Identificadores'})).getByText('Página 2 · 21 identificadores')).toBeInTheDocument());
  });
  it.each([['reader',['inventory_reader'],false],['archived',['inventory_editor'],true]] as const)('não permite escrita %s',async(_,roles,archived)=>{
    const mock=http(()=>json(page()),[...roles],archived);renderApp('/inventory/'+resource.id);
    await screen.findByText('10.42.0.1');expect(screen.queryByLabelText('Endereço IPv4')).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:'Encerrar 10.42.0.1'})).not.toBeInTheDocument();expect(mock.mock.calls.every(c=>c[1]?.method==='GET')).toBe(true);
  });
  it.each([409,503])('preserva formulário e não repete POST após %s',async(status)=>{
    let writes=0;http((_url,options)=>{if(options.method==='POST'){writes++;return failure(status,status===409?'version_conflict':'internal_error');}return json(page([]));});
    renderApp('/inventory/'+resource.id);await fill();await userEvent.click(screen.getByRole('button',{name:'Adicionar IPv4'}));
    expect(await screen.findByRole('alert')).not.toHaveTextContent('Texto interno');
    expect(screen.getByLabelText('Endereço IPv4')).toHaveValue('10.42.0.1');expect(writes).toBe(1);
    if(status===503){expect(screen.getByRole('button',{name:'Adicionar IPv4'})).toBeDisabled();await userEvent.click(screen.getByRole('button',{name:'Consultar identificadores atuais'}));expect(writes).toBe(1);}
  });
  it('falha de leitura não remove o detalhe normal',async()=>{
    http(()=>failure(503,'internal_error'));renderApp('/inventory/'+resource.id);
    const section=await screen.findByRole('region',{name:'Identificadores'});
    expect(await within(section).findByRole('alert')).not.toHaveTextContent('Texto interno');expect(screen.getByRole('heading',{name:resource.display_name})).toBeInTheDocument();
  });
  it.each(['503','timeout'])('preserva o rascunho durante e depois do recarregamento completo após %s',async(kind)=>{
    let writes=0,reads=0,version=1;let finish!:(response:Response)=>void;
    const refresh=new Promise<Response>(resolve=>{finish=resolve;});
    http((_url,options)=>{
      if(options.method==='POST'){writes++;expect(JSON.parse(String(options.body)).row_version).toBe(1);version=2;if(kind==='timeout')throw new TypeError('constructed timeout');return failure(503,'internal_error');}
      return json(page([],version));
    },['inventory_editor'],false,()=>1,()=>++reads===1?json(resource):refresh);
    renderApp('/inventory/'+resource.id);await fill();
    const input=screen.getByLabelText('Endereço IPv4');
    await userEvent.click(screen.getByRole('button',{name:'Adicionar IPv4'}));
    await userEvent.click(await screen.findByRole('button',{name:'Consultar identificadores atuais'}));
    await screen.findByText('A carregar o recurso…');
    expect(screen.getByLabelText('Endereço IPv4')).toBe(input);
    expect(input).toHaveValue('10.42.0.1');expect(input).toBeDisabled();
    expect(screen.getByLabelText('Namespace lógico')).toHaveValue('lab');expect(writes).toBe(1);
    await act(async()=>{finish(json({...resource,row_version:2}));});
    await waitFor(()=>expect(screen.getByText('Versão do registo').nextElementSibling).toHaveTextContent('2'));
    expect(screen.getByLabelText('Endereço IPv4')).toBe(input);
    expect(input).toHaveValue('10.42.0.1');expect(screen.getByLabelText('Namespace lógico')).toHaveValue('lab');
    expect(screen.getByRole('button',{name:'Adicionar IPv4'})).toBeEnabled();expect(writes).toBe(1);expect(reads).toBe(2);
  });
  it('mudar de recurso elimina o rascunho anterior antes de terminar a leitura nova',async()=>{
    const other='8cad3221-f2cb-41f1-a9af-14d88230adbb';let finish!:(response:Response)=>void;
    const pending=new Promise<Response>(resolve=>{finish=resolve;});
    mockHttp((url,options)=>{
      if(url.pathname.endsWith('/auth/me'))return json({user:{...user,roles:['inventory_editor']}});
      if(url.pathname.endsWith('/auth/csrf'))return json({csrf_token:'identifier-csrf'});
      if(url.pathname.endsWith('/resources/'+resource.id))return json(resource);
      if(url.pathname.endsWith('/resources/'+other))return pending;
      if(url.pathname.endsWith('/history'))return json({resource_id:url.pathname.split('/').at(-2),items:[],total:0,page:1,per_page:20});
      if(options.method==='POST')return json({error:{code:'identifier_conflict'},details:{conflict_revision:'a'.repeat(64),conflicts:[{resource_id:other,identifier_id:'peer'}],visible_total:1,truncated:false}},409);
      return json(page([]));
    });
    renderApp('/inventory/'+resource.id);await fill();await userEvent.click(screen.getByRole('button',{name:'Adicionar IPv4'}));
    await userEvent.click(await screen.findByRole('link',{name:'Consultar recurso coincidente'}));
    expect(screen.queryByLabelText('Endereço IPv4')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading',{name:resource.display_name})).not.toBeInTheDocument();
    await act(async()=>{finish(json({...resource,id:other,display_name:'Outro recurso'}));});
    expect(await screen.findByLabelText('Endereço IPv4')).toHaveValue('');expect(screen.getByLabelText('Namespace lógico')).toHaveValue('');
    expect(screen.getByRole('heading',{name:'Outro recurso'})).toBeInTheDocument();
  });
  it('sinaliza explicitamente mais de 20 coincidências e confirma com a revisão integral',async()=>{
    const conflicts=Array.from({length:20},(_,i)=>({resource_id:'peer-'+i,identifier_id:'identifier-'+i}));let writes=0;
    http((_url,options)=>{
      if(options.method==='POST'){
        writes++;
        if(writes===1)return json({error:{code:'identifier_conflict'},details:{conflict_revision:'c'.repeat(64),conflicts,visible_total:23,truncated:true}},409);
        expect(JSON.parse(String(options.body))).toMatchObject({confirm_shared:true,conflict_revision:'c'.repeat(64)});
        return json({identifier:item,resource_row_version:2,changed:true},201);
      }
      return json(page([]));
    });
    renderApp('/inventory/'+resource.id);await fill();await userEvent.click(screen.getByRole('button',{name:'Adicionar IPv4'}));
    expect(await screen.findByText('23 coincidências autorizadas; 20 apresentadas.')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Lista parcial');
    expect(screen.getAllByRole('link',{name:'Consultar recurso coincidente'})).toHaveLength(20);
    await userEvent.click(screen.getByRole('button',{name:'Confirmo a coexistência neste namespace'}));
    await waitFor(()=>expect(writes).toBe(2));
  });
});
