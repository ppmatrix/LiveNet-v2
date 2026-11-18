import { ApiError, invalidResponse, isRecord, request } from './client';
import { getCsrf } from './auth';

export interface Identifier {
  id:string; resource_id:string; identifier_value:string; normalized_value:string; namespace:string|null;
  source_type:string; source_instance:string|null; state:'active'|'closed'; valid_from:string; valid_until:string|null;
}
export interface IdentifierPage { items:Identifier[];total:number;page:number;per_page:number;resource_row_version:number }
export interface IdentifierResult { identifier:Identifier;resource_row_version:number;changed:boolean }
export interface Coincidences { conflict_revision:string;conflicts:{resource_id:string;identifier_id:string}[];visible_total:number;truncated:boolean }
function identifier(data:unknown,rid:string):Identifier {
  if(!isRecord(data)||data.resource_id!==rid||!['id','identifier_value','normalized_value','source_type','valid_from'].every(k=>typeof data[k]==='string'&&data[k]!==''))return invalidResponse();
  if(!(data.namespace===null||typeof data.namespace==='string')||!(data.source_instance===null||typeof data.source_instance==='string')
    ||!['active','closed'].includes(String(data.state))||!(data.valid_until===null||typeof data.valid_until==='string'))return invalidResponse();
  return data as unknown as Identifier;
}
function version(value:unknown):value is number {return Number.isSafeInteger(value)&&Number(value)>0;}
export function coincidences(error:unknown):Coincidences|null {
  if(!(error instanceof ApiError)||!['identifier_conflict','conflict_changed'].includes(error.code)||!isRecord(error.details))return null;
  const d=error.details;
  if(typeof d.conflict_revision!=='string'||!/^[0-9a-f]{64}$/.test(d.conflict_revision)||!Array.isArray(d.conflicts)||d.conflicts.length>20
    ||!Number.isSafeInteger(d.visible_total)||Number(d.visible_total)<0||d.conflicts.length!==Math.min(20,Number(d.visible_total))
    ||typeof d.truncated!=='boolean'||d.truncated!==(Number(d.visible_total)>d.conflicts.length)
    ||!d.conflicts.every(c=>isRecord(c)&&typeof c.resource_id==='string'&&typeof c.identifier_id==='string'))return null;
  return d as unknown as Coincidences;
}
const base=(rid:string)=>'/inventory/resources/'+encodeURIComponent(rid)+'/identifiers';
export async function getIdentifiers(rid:string,state:string,page:number,signal?:AbortSignal):Promise<IdentifierPage> {
  const d=await request(base(rid),{query:new URLSearchParams({state,page:String(page),per_page:'20'}),signal});
  if(!isRecord(d)||!Array.isArray(d.items)||!Number.isSafeInteger(d.total)||Number(d.total)<0||!version(d.page)||!version(d.per_page)||Number(d.per_page)>100||!version(d.resource_row_version))return invalidResponse();
  return {...d,items:d.items.map(item=>identifier(item,rid))} as unknown as IdentifierPage;
}
async function mutation(rid:string,path:string,body:unknown):Promise<IdentifierResult> {
  const d=await request(base(rid)+path,{method:'POST',body,csrf:await getCsrf()});
  if(!isRecord(d)||!version(d.resource_row_version)||typeof d.changed!=='boolean')return invalidResponse();
  return {identifier:identifier(d.identifier,rid),resource_row_version:d.resource_row_version,changed:d.changed};
}
export const addIdentifier=(rid:string,value:string,namespace:string,row_version:number,confirmation:Coincidences|null)=>
  mutation(rid,'',{identifier_value:value,namespace,row_version,confirm_shared:confirmation!==null,conflict_revision:confirmation?.conflict_revision??null});
export const closeIdentifier=(rid:string,id:string,row_version:number)=>mutation(rid,'/'+encodeURIComponent(id)+'/close',{row_version});
