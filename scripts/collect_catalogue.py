#!/usr/bin/env python3
"""Capture the documented CiviX search catalogue; never fetch law text in bulk."""
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode, quote
from archive import fetch, utcnow, digest

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://www.bclaws.gov.bc.ca/civix/search/complete/fullsearch'

def parse_page(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Unexpected XML entities')
    root = ET.fromstring(raw)
    if root.tag != 'results':
        raise ValueError('Expected CiviX search results')
    count = int(root.attrib['totalhits'])
    records = []
    for doc in root.findall('doc'):
        fields = {c.tag: ' '.join(''.join(c.itertext()).split()) for c in doc}
        title, ident, index = (fields.get(k, '') for k in ['CIVIX_DOCUMENT_TITLE','CIVIX_DOCUMENT_ID','CIVIX_INDEX_ID'])
        if not title or not ident or not index:
            raise ValueError('Incomplete catalogue record')
        location = fields.get('CIVIX_DOCUMENT_LOC', '')
        kind = 'Historical / point in time' if 'point in time' in (title+' '+location).lower() else 'Legislative change table' if 'tlc' in title.lower() or 'legislative changes' in location.lower() else 'Document'
        records.append({'title': title, 'id': ident, 'index': index, 'kind': kind,
                        'parents': [fields['CIVIX_DOCUMENT_PARENT']] if fields.get('CIVIX_DOCUMENT_PARENT') else [],
                        'location': location, 'url': 'https://www.bclaws.gov.bc.ca/civix/document/id/complete/'+quote(index,safe='')+'/'+quote(ident,safe='')})
    return count, records

def collect(root=ROOT):
    started = utcnow()
    records, pages = {}, []
    # Cache individual pages so a transient failure can resume within this UTC day.
    cache = root/'.cache'/'catalogue'/started[:10]
    cache.mkdir(parents=True, exist_ok=True)
    lock, stop = threading.Lock(), threading.Event()
    next_start = [0.0]
    def page(offset):
        url = ENDPOINT+'?'+urlencode({'q':'CIVIX_DOCUMENT_TYPE:document','s':offset,'e':offset+20,'nFrag':1,'lFrag':50})
        raw_path, meta_path = cache/f'{offset}.xml', cache/f'{offset}.json'
        if raw_path.exists() and meta_path.exists():
            raw, meta = raw_path.read_bytes(), json.loads(meta_path.read_text())
            if meta.get('sha256') != digest(raw) or meta.get('url') != url:
                raise ValueError('Cached catalogue page failed its integrity check')
        else:
            for attempt in range(3):
                with lock:
                    if stop.is_set(): raise RuntimeError('Collection stopped after a failed page')
                    delay = max(0,next_start[0]-time.monotonic())
                    if delay: time.sleep(delay)
                    next_start[0] = time.monotonic()+1
                try:
                    raw, meta = fetch(url,'lawdelta')
                    break
                except (HTTPError, URLError) as exc:
                    if isinstance(exc,HTTPError) and exc.code < 500: raise
                    if attempt == 2: raise
                    time.sleep(2**(attempt+1))
            parse_page(raw)
            raw_path.write_bytes(raw)
            meta_path.write_text(json.dumps(meta))
        found, batch = parse_page(raw)
        if not 100 <= found <= 20000 or not batch or len(batch)>20:
            raise ValueError('Unexpected catalogue page size')
        return offset, found, batch, {'url':url,'sha256':meta['sha256'],'retrieved_at':meta['retrieved_at'],'records':len(batch)}
    first = page(0)
    total = first[1]
    def accept(result):
        offset, found, batch, meta = result
        if found != total: raise ValueError('Catalogue count changed during capture')
        for item in batch:
            key = item['index']+'/'+item['id']
            if key in records:
                previous = records[key]
                # CiviX can index one document under different statutory parents.
                # Merge only exact document metadata with distinct source parents;
                # a repeated page or conflicting record must still fail closed.
                comparable = lambda row: {k:v for k,v in row.items() if k != 'parents'}
                if (not previous['parents'] or not item['parents']
                        or set(previous['parents']) & set(item['parents'])
                        or comparable(previous) != comparable(item)):
                    raise ValueError('Duplicate or conflicting catalogue record across pages')
                previous['parents'].extend(item['parents'])
            else:
                records[key] = item
        pages.append((offset,meta))
        print(f'Catalogue: {len(records)}/{total}',flush=True)
    accept(first)
    pool = ThreadPoolExecutor(max_workers=4)
    pending = [pool.submit(page,offset) for offset in range(20,total,20)]
    try:
        for result in as_completed(pending): accept(result.result())
    except Exception:
        stop.set()
        for future in pending: future.cancel()
        raise
    finally: pool.shutdown(wait=True,cancel_futures=True)
    pages = [meta for _,meta in sorted(pages)]
    if sum(page['records'] for page in pages) != total: raise ValueError('Incomplete catalogue')
    data = {'schema_version':1,'started_at':started,'captured_at':utcnow(),'source':ENDPOINT,
            'scope':'Document titles and catalogue paths, including historical versions and change tables. Full text and change history are available only for the four-law watchlist.',
            'source_hits':total,'merged_aliases':total-len(records),
            'pages':pages,'records':sorted(records.values(),key=lambda x:(x['title'].casefold(),x['id']))}
    target = root/'data/catalogue.json'
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    temp.replace(target)
    print(f'Saved {len(records)} catalogue records')

if __name__ == '__main__':
    try: collect()
    except Exception as exc: raise SystemExit('Catalogue refresh failed; previous catalogue retained: '+str(exc))
