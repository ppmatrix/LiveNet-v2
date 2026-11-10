import { getCsrf } from './auth';
import { invalidResponse,isRecord,request } from './client';
import { parseResource } from './inventory';
import type { ResourceInput } from './inventory';
import type { Resource } from './contracts';

export interface DiscoveryPolicy { networks:string[]; ports:number[]; max_targets:number; concurrency:number; target_timeout:number; job_timeout:number; max_jobs:number }
export interface DiscoveryConfig { enabled:boolean; policy:DiscoveryPolicy|null }
export interface Observation {
  id:string; ip:string; hostname:null; outcome:'responded'|'no_response'|'error'; observed_at:string;
  evidence:{ method:string; ports:{port:number; result:string; code?:string; errno?:number}[] };
  decision:{mode:string; resource_id:string; decided_at:string}|null;
}
export interface DiscoveryJob { id:string; target:string; status:string; total:number; processed:number; observations?:Observation[] }
export interface Candidate extends Observation {
  possible_matches:{id:string; display_name:string; administrative_state:string}[];
  matches_truncated:boolean; previous_observations:{id:string; job_id:string; observed_at:string; outcome:string}[];
}
function observation(data:unknown):Observation {
  if (!isRecord(data) || typeof data.id!=='string' || typeof data.ip!=='string' || data.hostname!==null
      || !['responded','no_response','error'].includes(String(data.outcome)) || typeof data.observed_at!=='string'
      || !isRecord(data.evidence) || data.evidence.method!=='tcp_connect' || !Array.isArray(data.evidence.ports)
      || !data.evidence.ports.every(p=>isRecord(p)&&Number.isInteger(p.port)&&typeof p.result==='string'&&(p.code===undefined||typeof p.code==='string')&&(p.errno===undefined||Number.isInteger(p.errno)))
      || !(data.decision===null || (isRecord(data.decision)&&typeof data.decision.resource_id==='string'&&typeof data.decision.mode==='string'))) return invalidResponse();
  return data as unknown as Observation;
}
function job(data:unknown):DiscoveryJob {
  if (!isRecord(data)||typeof data.id!=='string'||typeof data.target!=='string'||typeof data.status!=='string'
      ||!Number.isInteger(data.total)||!Number.isInteger(data.processed)) return invalidResponse();
  if (data.observations!==undefined) {
    if (!Array.isArray(data.observations)) return invalidResponse();
    data.observations=data.observations.map(observation);
  }
  return data as unknown as DiscoveryJob;
}
export async function getDiscoveryConfig(signal?:AbortSignal):Promise<DiscoveryConfig> {
  const data=await request('/discovery/config',{signal});
  if (!isRecord(data)||typeof data.enabled!=='boolean'||(data.enabled&&!isRecord(data.policy))) return invalidResponse();
  if (data.enabled) {
    const p=data.policy;
    if (!isRecord(p)||!Array.isArray(p.networks)||!p.networks.every(n=>typeof n==='string')
        ||!Array.isArray(p.ports)||!p.ports.every(n=>Number.isInteger(n))||!['max_targets','concurrency','target_timeout','job_timeout','max_jobs'].every(k=>typeof p[k]==='number'&&Number(p[k])>0)) return invalidResponse();
  }
  return data as unknown as DiscoveryConfig;
}
export async function getJobs(signal?:AbortSignal):Promise<DiscoveryJob[]> {
  const data=await request('/discovery/jobs',{signal});
  if (!isRecord(data)||!Array.isArray(data.items)) return invalidResponse();
  return data.items.map(job);
}
export async function getJob(id:string,signal?:AbortSignal):Promise<DiscoveryJob> { return job(await request('/discovery/jobs/'+encodeURIComponent(id),{signal})); }
export async function startJob(target:string):Promise<DiscoveryJob> { return job(await request('/discovery/jobs',{method:'POST',body:{target},csrf:await getCsrf()})); }
export async function cancelJob(id:string):Promise<DiscoveryJob> { return job(await request('/discovery/jobs/'+encodeURIComponent(id)+'/cancel',{method:'POST',csrf:await getCsrf()})); }
export async function getCandidate(id:string,signal?:AbortSignal):Promise<Candidate> {
  const data=await request('/discovery/candidates/'+encodeURIComponent(id),{signal});observation(data);
  if (!isRecord(data)||!Array.isArray(data.possible_matches)||!data.possible_matches.every(m=>isRecord(m)&&typeof m.id==='string'&&typeof m.display_name==='string'&&typeof m.administrative_state==='string')
      ||typeof data.matches_truncated!=='boolean'||!Array.isArray(data.previous_observations)||!data.previous_observations.every(o=>isRecord(o)&&typeof o.id==='string'&&typeof o.job_id==='string'&&typeof o.observed_at==='string'&&typeof o.outcome==='string')) return invalidResponse();
  return data as unknown as Candidate;
}
async function decide(id:string,body:unknown):Promise<Resource> {
  const data=await request('/discovery/candidates/'+encodeURIComponent(id)+'/decision',{method:'POST',body,csrf:await getCsrf()});
  if (!isRecord(data)||typeof data.already_decided!=='boolean') return invalidResponse();
  return parseResource(data.resource);
}
export function createFromCandidate(id:string,resource:ResourceInput,confirmDistinct:boolean) { return decide(id,{mode:'create',resource,confirm_distinct:confirmDistinct}); }
export function associateCandidate(id:string,resourceId:string) { return decide(id,{mode:'associate',resource_id:resourceId}); }

export interface ResourceDiscoveryEntry extends Observation {
  job_id:string;
  decision:NonNullable<Observation['decision']>;
}
export interface ResourceDiscoveryHistory {
  resource_id:string;
  items:ResourceDiscoveryEntry[];
  total:number;
  page:number;
  per_page:number;
}
export async function getResourceDiscoveryHistory(id:string,page=1,signal?:AbortSignal):Promise<ResourceDiscoveryHistory> {
  const data=await request('/discovery/resources/'+encodeURIComponent(id)+'/history',{
    signal,query:new URLSearchParams({page:String(page),per_page:'20'}),
  });
  if(!isRecord(data)||data.resource_id!==id||!Array.isArray(data.items)
      ||!Number.isSafeInteger(data.total)||Number(data.total)<0||!Number.isSafeInteger(data.page)||Number(data.page)<1
      ||!Number.isSafeInteger(data.per_page)||Number(data.per_page)<1||Number(data.per_page)>100)return invalidResponse();
  for(const item of data.items) {
    const o=observation(item);
    if(!isRecord(item)||typeof item.job_id!=='string'||!item.job_id||!o.decision
        ||!['create','associate'].includes(o.decision.mode)||o.decision.resource_id!==id
        ||typeof o.decision.decided_at!=='string')return invalidResponse();
  }
  return data as unknown as ResourceDiscoveryHistory;
}
