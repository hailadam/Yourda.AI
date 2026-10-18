/** Pure financial UI helpers. Missing real data is always displayed as unavailable. */
export const money = value => typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(value) : '—';
export const percent = value => typeof value === 'number' && Number.isFinite(value) ? `${value>0?'+':''}${value.toFixed(2)}%` : '—';
export function dailyChange(instrument){ if(!instrument||!instrument.previous_close||!instrument.price) return null;return ((instrument.price-instrument.previous_close)/instrument.previous_close)*100; }
export const marketStatusLabel = status => ({live_iex:'Recent IEX observations',end_of_day:'Latest available / may be closed',live:'Live (provider reported)',delayed:'Delayed',stale:'Stale',unknown:'Session unknown'})[status]||'Unavailable';
export const normalise = points => Array.isArray(points) ? points.filter(p=>Number.isFinite(Number(p.close)) && Number(p.close)>0).map(p=>({x:p.time||p.t, value:Number(p.close),volume:Number(p.volume||0)})) : [];
export const formatDate = v => {if (!v) return '—';const d=new Date(v);return Number.isFinite(d.valueOf()) ? d.toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}) : String(v);};
