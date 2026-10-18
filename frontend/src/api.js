/** Yourda V14 FastAPI adapter. Tokens are intentionally in memory only. */
export const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
export const apiUrl = (path) => `${API_ORIGIN}${path}`;
export class ApiError extends Error { constructor(message,status=0){super(message);this.status=status;} }
export async function request(method,path,token=null,body) {
  let response;
  try {
    response = await fetch(apiUrl(path), {method, headers: {
      'Accept':'application/json',...(body!==undefined?{'Content-Type':'application/json'}:{}),
      ...(token?{'Authorization':`Bearer ${token}`}:{})},
      ...(body!==undefined?{body:JSON.stringify(body)}:{}) });
  } catch { throw new ApiError('Backend unavailable. Start FastAPI on port 8000, or browse the frontend preview without live services.'); }
  let data;
  try {data = await response.json();} catch {throw new ApiError(`Unexpected server response (HTTP ${response.status})`,response.status);}
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(d=>d.msg).join('; ') : (data.detail || data.message);
    throw new ApiError(typeof detail==='string'?detail:`Request failed (${response.status})`, response.status);
  }
  return data;
}
export const get = (path,token=null) => request('GET',path,token);
export const post = (path,body={},token=null) => request('POST',path,token,body);
export const rangeValues = ['1D','1W','1M','3M','1Y'];
export const symbols = ['SPY','QQQ','DIA','IWM','VOO','AAPL','NVDA'];
export const symbolDescriptions = {SPY:'S&P 500 ETF proxy',QQQ:'Nasdaq-100 ETF proxy',DIA:'Dow Jones ETF proxy',IWM:'Russell 2000 ETF proxy',VOO:'S&P 500 ETF proxy',AAPL:'Apple stock',NVDA:'NVIDIA stock'};
export { money,percent,dailyChange,marketStatusLabel,normalise,formatDate } from './market-utils.js';
