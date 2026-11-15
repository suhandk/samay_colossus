import type {components} from './api-contracts';
export type ApiDraft=components['schemas']['Draft'];
export function apiFetch(path:string,options:RequestInit={}){
 const timeout=AbortSignal.timeout(20000);
 return fetch(path,{...options,cache:'no-store',signal:options.signal?AbortSignal.any([options.signal,timeout]):timeout});
}

export type PlannerResponse=components['schemas']['PlannerResponse'];
