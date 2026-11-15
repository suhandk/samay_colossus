import {apiFetch} from './api';
import {Outlook} from './Outlook';
import {Results,readResults,Result} from './Results';
import React,{useEffect,useState,lazy,Suspense} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter,NavLink,useLocation,useNavigate} from 'react-router-dom';
import {QueryClient,QueryClientProvider,useQuery} from '@tanstack/react-query';
import {House,Sprout,Store,Bookmark,Settings} from 'lucide-react';
import {Lang,Key,tr,dateText} from './i18n';
import {Planner,Catalog} from './Planner';
import {readDrafts,Draft} from './drafts';
import {catalogSchema} from './catalog';
import './style.css';
const MarketPrices=lazy(()=>import('./MarketPrices').then(m=>({default:m.MarketPrices})));
function App(){
 const [lang,setLang]=useState<Lang>(()=>{try{return localStorage.getItem('language')==='kn'?'kn':'en'}catch{return 'en'}});
 const [chosen,setChosen]=useState(()=>{try{return !!localStorage.getItem('language')}catch{return false}});
 const [online,setOnline]=useState(navigator.onLine);const [drafts,setDrafts]=useState(readDrafts);const [initial,setInitial]=useState<Draft>();const [previous,setPrevious]=useState<Result>();const [version,setVersion]=useState(0);const [notice,setNotice]=useState<Key|null>(null);
 const models=useQuery<{items:unknown[]}>({queryKey:['models'],queryFn:async({signal})=>{const r=await apiFetch('/api/v1/models/availability',{signal});if(!r.ok)throw Error();return r.json()},retry:1});
 const path=useLocation().pathname;const navigate=useNavigate();const t=(k:Key)=>tr(lang,k);
 const catalog=useQuery<Catalog>({queryKey:['catalog'],queryFn:async({signal})=>{const r=await apiFetch('/api/catalog',{signal});if(!r.ok)throw Error();return catalogSchema.parse(await r.json())},retry:1});
 useEffect(()=>{const change=()=>setOnline(navigator.onLine);addEventListener('online',change);addEventListener('offline',change);return()=>{removeEventListener('online',change);removeEventListener('offline',change)}},[]);
 useEffect(()=>{document.documentElement.lang=lang},[lang]);useEffect(()=>{setDrafts(readDrafts());setNotice(null);window.scrollTo(0,0)},[path]);
 function language(value:Lang){setLang(value);setChosen(true);try{localStorage.setItem('language',value)}catch{setNotice('storageError')}}
 function listen(){const voices=window.speechSynthesis?.getVoices()??[];const voice=voices.find(v=>v.lang.toLowerCase().startsWith(lang==='kn'?'kn':'en'));if(!voice){setNotice('speechUnavailable');return}speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(document.querySelector('main')?.innerText??'');utterance.voice=voice;utterance.lang=voice.lang;speechSynthesis.speak(utterance)}
 if(!chosen)return <main className="language-screen"><Sprout size={48}/><h1>SAMAY</h1><h2>ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ</h2><p>Choose your language</p><button className="primary" onClick={()=>language('kn')}>ಕನ್ನಡ</button><button onClick={()=>language('en')}>English</button></main>;
 const nav=[['/','home',House],['/plan','sell',Sprout],['/prices','prices',Store],['/plans','plans',Bookmark]] as const;
 return <><a className="skip" href="#content">{t('next')}</a><header><NavLink to="/" className="brand"><Sprout/>SAMAY</NavLink><NavLink to="/settings" aria-label={t('settings')}><Settings/></NavLink></header><div className={online?'connection':'connection warning'} role="status">{t(online?'online':'offline')}</div><main id="content"><button className="read-aloud" onClick={listen}>{t('listen')}</button><h1>{t(path==='/settings'?'settings':path==='/outlook'?'outlook':nav.find(n=>n[0]===path)?.[1]??'home')}</h1>
 {catalog.isPending&&<p role="status">{t('loading')}</p>}{catalog.isError&&<aside role="alert">{t('error')}<button onClick={()=>catalog.refetch()}>{t('retry')}</button></aside>}
 {path==='/'&&<><section className="hero"><p className="eyebrow">{lang==='kn'?'ಕನ್ನಡ':'English'}</p><h2>{t('welcome')}</h2><p>{t('intro')}</p><NavLink className="primary button" to="/plan">{t('plan')}</NavLink></section><section className="card"><h2>{t('observed')}</h2>{!catalog.data?.observed_pairs.length?<p>{t('empty')}</p>:catalog.data.observed_pairs.map(p=><p key={p.crop_id+p.market_id}>{catalog.data?.crops.find(c=>c.id===p.crop_id)?.names[lang]} · {catalog.data?.markets.find(m=>m.id===p.market_id)?.names[lang]}</p>)}<NavLink to="/prices">{t('prices')}</NavLink></section>{drafts.length>0&&<section className="card"><h2>{t('plans')}</h2><p>{t('draft')} · {dateText(drafts[0].at,lang)}</p><NavLink to="/plans">{t('open')}</NavLink></section>}<NavLink to="/outlook">{t('outlook')}</NavLink></>}
 {path==='/plan'&&<Planner key={version} lang={lang} catalog={catalog.isError?undefined:catalog.data} initial={initial} online={online} previous={previous}/>}
 {path==='/prices'&&<Suspense fallback={<p>{t('loading')}</p>}><MarketPrices lang={lang} crops={catalog.data?.crops??[]} markets={catalog.data?.markets??[]}/></Suspense>}
 {path==='/plans'&&<>{readResults().map(r=><Results key={r.id} result={r} lang={lang} saved edit={d=>{setPrevious(r);setInitial(d);setVersion(v=>v+1);navigate('/plan')}}/>)}<p>{t('privacy')}</p>{!drafts.length&&<p>{t('noPlans')}</p>}{drafts.map(d=><article className="card" key={d.id}><h2>{t('draft')}</h2><p>{dateText(d.at,lang)}</p><button onClick={()=>{setPrevious(undefined);setInitial(d.data);setVersion(v=>v+1);navigate('/plan')}}>{t('open')}</button><button onClick={()=>{try{const next=drafts.filter(x=>x.id!==d.id);localStorage.setItem('samay-drafts',JSON.stringify(next));setDrafts(next)}catch{setNotice('storageError')}}}>{t('remove')}</button></article>)}</>}
 {path==='/outlook'&&<Outlook lang={lang} catalog={catalog.data}/>}
 {path==='/settings'&&<><label>{t('language')}<select value={lang} onChange={e=>language(e.target.value as Lang)}><option value="kn">ಕನ್ನಡ</option><option value="en">English</option></select></label><p>{t('privacy')}</p></>}
 {notice&&<p role="status">{t(notice)}</p>}</main><nav className="bottom-nav" aria-label={t('home')}>{nav.map(([url,key,Icon])=><NavLink key={url} to={url} end><Icon aria-hidden="true"/><span>{t(key)}</span></NavLink>)}</nav></>;
}
createRoot(document.getElementById('root')!).render(<QueryClientProvider client={new QueryClient()}><BrowserRouter><App/></BrowserRouter></QueryClientProvider>);
if('serviceWorker' in navigator&&import.meta.env.PROD)navigator.serviceWorker.register('/sw.js').catch(()=>{});
