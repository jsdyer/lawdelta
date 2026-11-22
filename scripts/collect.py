#!/usr/bin/env python3
"""Fetch only four documented CiviX XML document resources; never crawl the site."""
import argparse
import json
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET
from archive import canonical, digest, fetch, manifest, save, timestamp, utcnow

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/'
LICENCE = 'https://www.bclaws.gov.bc.ca/standards/Licence.html'
DOCUMENTS = [
    {'id':'foippa','document_id':'96165_00_multi','title':'Freedom of Information and Protection of Privacy Act','kind':'Act'},
    {'id':'pipa','document_id':'03063_01','title':'Personal Information Protection Act','kind':'Act'},
    {'id':'foippa-reg','document_id':'155_2012','title':'Freedom of Information and Protection of Privacy Regulation','kind':'Regulation'},
    {'id':'pipa-reg','document_id':'473_2003','title':'Personal Information Protection Act Regulations','kind':'Regulation'},
]
BLOCKS = {'section','subsection','paragraph','subparagraph','clause','subclause','definition','text','marginalnote','hnote','trow','line','scheduletitle','lefttext','centertext','entry'}

def local(tag):
    return tag.split('}')[-1]

def norm(text):
    return ' '.join(text.split())

def plain(node):
    return norm(''.join(node.itertext()))

def child(node, tag):
    return next((plain(n) for n in node if local(n.tag) == tag), '')

def block_text(node):
    def walk(e):
        if local(e.tag) in BLOCKS:
            yield '\n'
        if e.text:
            yield e.text
        for n in e:
            yield from walk(n)
            if n.tail:
                yield n.tail
        if local(e.tag) == 'num':
            yield ' '
        if local(e.tag) in BLOCKS:
            yield '\n'
    return '\n'.join(norm(line) for line in ''.join(walk(node)).splitlines() if norm(line))

def parse_xml(raw, spec):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('DTD/entity documents are not accepted')
    root = ET.fromstring(raw)
    if local(root.tag) not in {'act','regulation'}:
        raise ValueError('Expected legislative XML, not a table of contents or HTML')
    title = child(root,'title')
    if title != spec['title']:
        raise ValueError('Unexpected document title: '+title)
    parents = {n:parent for parent in root.iter() for n in parent}
    def in_schedule(node):
        while node in parents:
            node=parents[node]
            if local(node.tag)=='schedule': return True
        return False
    units=[]
    for n in root.iter():
        tag=local(n.tag)
        if tag=='section' and not in_schedule(n):
            number=child(n,'num')
            if not number: raise ValueError('Unnumbered section')
            units.append({'key':'section:'+number,'label':'Section '+number,'heading':child(n,'marginalnote'),
                          'source_id':n.get('id'), 'text':block_text(n)})
        elif tag=='schedule':
            heading=child(n,'scheduletitle') or child(n,'title')
            if not heading: raise ValueError('Unlabelled schedule')
            units.append({'key':'schedule:'+heading,'label':heading,'heading':heading,'source_id':n.get('id'),'text':block_text(n)})
    keys=[u['key'] for u in units]
    if len(keys)<3 or len(keys)!=len(set(keys)) or any(not u['text'] for u in units):
        raise ValueError('Missing, duplicate or empty legislative units')
    annotations=[]
    for n in root:
        if local(n.tag)=='amend' and n.get('effective'):
            value=n.attrib['effective']
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value): raise ValueError('Invalid effective-date annotation')
            annotations.append({'effective':value,'regulation':n.get('regnum'),'added':n.get('added'),
                                'bulletin':n.get('bullId'), 'scope':'Document amendment metadata; not a section commencement determination'})
    metadata={k:child(root,k) or None for k in ['chapter','yearenacted','assentedto','regnum','deposited','effective','amsincluded']}
    return {**spec,'source_url':BASE+spec['document_id']+'/xml', 'official_url':BASE+spec['document_id'],
            'licence_url':LICENCE,'source_metadata':metadata,'effective_annotations':annotations,'units':units,
            'normalized_sha256':digest(canonical(units))}

def diff_units(before, after):
    if before is None: return {'state':'baseline','added':0,'removed':0,'changed':0,'changes':[]}
    old={u['key']:u for u in before['units']}; new={u['key']:u for u in after['units']}
    changes=[]
    for key in dict.fromkeys([*old,*new]):
        a=old.get(key);b=new.get(key)
        state='added' if a is None else 'removed' if b is None else 'changed' if a['text']!=b['text'] else None
        if state: changes.append({'key':key,'state':state,'label':(b or a)['label'],'heading':(b or a)['heading']})
    return {'state':'changed' if changes else 'unchanged', **{s:sum(c['state']==s for c in changes) for s in ['added','removed','changed']},'changes':changes}

def collect(root=ROOT):
    existing=manifest(root)
    previous=json.loads((root/'data'/existing['captures'][-1]['path']).read_text()) if existing['captures'] else None
    prev={d['id']:d for d in previous['documents']} if previous else {}
    staged=[]; docs=[]
    # The published REST API explicitly authorizes finite XML document retrieval. robots.txt
    # disallows generic crawlers; this collector does not crawl or discover links.
    for i,spec in enumerate(DOCUMENTS):
        if i: time.sleep(2)
        url=BASE+spec['document_id']+'/xml'
        raw,meta=fetch(url,'lawdelta')
        doc=parse_xml(raw,spec)
        doc['retrieved_at']=meta['retrieved_at'];doc['raw_sha256']=meta['sha256'];doc['changes']=diff_units(prev.get(spec['id']),doc)
        staged.append((raw,'xml',meta));docs.append(doc)
    capture={'schema_version':1,'captured_at':utcnow(),'previous_capture':existing['captures'][-1]['captured_at'] if existing['captures'] else None,'documents':docs}
    summary={'tool':'lawdelta','title':'Law Delta','status':'ok','record_count':sum(len(d['units']) for d in docs),'document_count':len(docs),
             'baseline':previous is None,'change_count':sum(len(d['changes']['changes']) for d in docs),'source':'BC Laws CiviX XML','licence_url':LICENCE,
             'coverage':'Two BC privacy Acts and their regulations; section and schedule text only, captured snapshots rather than complete legislative history.',
             'documents':[{'id':d['id'],'title':d['title'],'kind':d['kind'],'units':len(d['units']),'state':d['changes']['state']} for d in docs]}
    save(root,capture,staged,summary)
    print(f"Saved {len(docs)} documents / {summary['record_count']} units; {summary['change_count']} observed changes")

if __name__=='__main__':
    try: collect()
    except Exception as exc: raise SystemExit('Collection failed; previous published data retained: '+str(exc))
