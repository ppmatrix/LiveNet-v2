import { useCallback,useEffect,useRef,useState } from 'react';
import { ApiError,isAbort } from './client';
import { getJob } from './discovery';
import type { DiscoveryJob,Observation } from './discovery';
import { useSession } from '../auth/SessionProvider';

export const discoveryActive=(status:string)=>['queued','running','cancelling'].includes(status);

// One GET at a time. Timers start after completion, never on a fixed interval.
// Refreshes preserve data/DOM; a transition to terminal gets one final read.
export function useDiscoveryJob(id:string) {
  const {expire}=useSession();
  const [state,setState]=useState<{id:string;data:DiscoveryJob|null;error:unknown;refreshing:boolean}>({id,data:null,error:null,refreshing:true});
  const refreshRef=useRef<()=>void>(()=>{});
  const refresh=useCallback(()=>refreshRef.current(),[]);
  useEffect(()=>{
    const controller=new AbortController();
    let stopped=false,inFlight=false,requested=false,sawActive=false,finalRead=false,finished=false;
    let timer:ReturnType<typeof setTimeout>|undefined;
    const observations=new Map<string,Observation>();
    setState({id,data:null,error:null,refreshing:true});
    async function run() {
      if(stopped||inFlight)return;
      inFlight=true;
      let delay:number|null=null;
      setState(previous=>({...previous,refreshing:true}));
      try {
        const job=await getJob(id,controller.signal);
        if(stopped)return;
        const incoming=job.observations||[];
        // Existing positions never change. New batches have deterministic order.
        const added=incoming.filter(o=>!observations.has(o.id)).sort((a,b)=>a.observed_at.localeCompare(b.observed_at)||a.id.localeCompare(b.id));
        for(const o of incoming)if(observations.has(o.id))observations.set(o.id,o);
        for(const o of added)observations.set(o.id,o);
        setState({id,data:{...job,observations:[...observations.values()]},error:null,refreshing:false});
        if(!finished) {
          if(finalRead)finished=true;
          else if(discoveryActive(job.status)){sawActive=true;delay=1000;}
          else if(sawActive){finalRead=true;delay=0;}
          else finished=true; // Opening an already terminal job needs just one GET.
        }
      } catch(error) {
        if(stopped||isAbort(error))return;
        if(error instanceof ApiError&&error.status===401)expire();
        else setState(previous=>({...previous,error,refreshing:false}));
        // Preserve results, stop automatic polling on failure; retry is explicit.
      } finally {
        inFlight=false;
        if(!stopped) {
          setState(previous=>({...previous,refreshing:false}));
          if(requested){requested=false;void run();}
          else if(delay!==null)timer=setTimeout(()=>void run(),delay);
        }
      }
    }
    function requestRefresh() {
      if(stopped)return;
      clearTimeout(timer);
      if(inFlight)requested=true;
      else void run();
    }
    refreshRef.current=requestRefresh;
    void run();
    return()=>{stopped=true;controller.abort();clearTimeout(timer);if(refreshRef.current===requestRefresh)refreshRef.current=()=>{};};
  },[id,expire]);
  return {data:state.id===id?state.data:null,error:state.id===id?state.error:null,refreshing:state.id!==id||state.refreshing,refresh};
}
