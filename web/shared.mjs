export const $=selector=>document.querySelector(selector);
export function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined&&text!==null)n.textContent=String(text);if(cls)n.className=cls;return n;}
export function link(text,href){const n=el('a',text);const u=new URL(href,location.href);if(u.protocol==='https:'||u.origin===location.origin){n.href=u.href;n.rel='noreferrer';}return n;}
export function formatDate(value){if(!value)return 'Not supplied';const d=new Date(value);return Number.isNaN(d.getTime())?'Invalid source date':d.toLocaleString('en-CA',{timeZone:'UTC',year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false})+' UTC';}
export async function getJSON(path){const r=await fetch(path);if(!r.ok)throw Error(`Could not load dated data (${r.status}). Please try again later.`);return r.json();}
export function capturePath(path){if(!/^history\/[0-9TZ-]+\.json$/.test(path))throw Error('Invalid capture path');return './data/'+path;}
export function download(text,name){const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
export function stat(value,label){const n=el('div',null,'stat');n.append(el('strong',value),el('span',label));return n;}
export function evidence(rows){const d=el('dl');for(const [key,value] of rows){d.append(el('dt',key));const val=el('dd');val.append(value instanceof Node?value:document.createTextNode(String(value??'Not supplied')));d.append(val);}return d;}
export function fail(error){$('#error').style.display='block';$('#error').textContent=error.message;}
