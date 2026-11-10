import type { Observation } from '../api/discovery';

const labels:Record<string,string>={connected:'ligação estabelecida',refused:'ligação recusada',timeout:'tempo esgotado',unreachable:'inalcançável',local_error:'erro local',error:'erro'};
const safeCodes=new Set(['ECONNREFUSED','ETIMEDOUT','EAGAIN','SOCKET_TIMEOUT','ENETUNREACH','EHOSTUNREACH','ENETDOWN','EHOSTDOWN',
  'EACCES','EPERM','EADDRNOTAVAIL','EADDRINUSE','EMFILE','ENFILE','ENOBUFS','ENOMEM','EAFNOSUPPORT','EINVAL',
  'UNCLASSIFIED_CONNECT_ERROR','OS_ERROR_WITHOUT_ERRNO']);

export function DiscoveryEvidence({evidence}:{evidence:Observation['evidence']}) {
  return <>TCP connect: {evidence.ports.length?evidence.ports.map(p=>{
    const label=labels[p.result]||'resultado desconhecido';
    const code=p.code&&safeCodes.has(p.code)?p.code:undefined;
    const detail=code?` (${code}${p.errno===undefined?'':`, errno ${p.errno}`})`:p.result==='error'?' (causa não preservada)':'';
    return `${p.port}: ${label}${detail}`;
  }).join(', '):'Sem resposta TCP obtida'}</>;
}
