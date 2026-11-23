const normalized=value=>String(value??'').normalize('NFKC').toLocaleLowerCase('en-CA');
export function searchCatalogue(records,query,kind='all'){
 const terms=normalized(query).trim().split(/\s+/).filter(Boolean);
 if(!terms.length)return [];
 return records.filter(r=>(kind==='all'||r.kind===kind)&&terms.every(t=>normalized(r.title+' '+r.location).includes(t)));
}
export function searchWatchlist(documents,query){
 const terms=normalized(query).trim().split(/\s+/).filter(Boolean);if(!terms.length)return [];
 return documents.flatMap(doc=>doc.units.filter(u=>terms.every(t=>normalized([u.label,u.heading,u.text].join(' ')).includes(t))).map(unit=>({document:doc.id,title:doc.title,official:doc.official_url,unit})));
}
