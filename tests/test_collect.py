import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from archive import manifest
from collect import ROOT,DOCUMENTS,parse_xml,diff_units

class ParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m=manifest(ROOT);cls.capture=json.loads((ROOT/'data'/m['captures'][0]['path']).read_text())
    def test_all_live_raw_xml_reparse_to_identical_units(self):
        for spec in DOCUMENTS:
            doc=next(d for d in self.capture['documents'] if d['id']==spec['id'])
            raw=next(s for s in self.capture['sources'] if s['sha256']==doc['raw_sha256'])
            parsed=parse_xml((ROOT/'data'/raw['archive_path']).read_bytes(),spec)
            self.assertEqual(parsed['units'],doc['units']);self.assertGreater(len(parsed['units']),3)
    def test_rejects_html_and_entity_payloads(self):
        for raw in [b'<html><body>TOC</body></html>',b'<!DOCTYPE x [<!ENTITY bad "bad">]><act/>']:
            with self.assertRaises(ValueError):parse_xml(raw,DOCUMENTS[0])
    def test_initial_capture_does_not_claim_additions(self):
        diff=diff_units(None,self.capture['documents'][0]);self.assertEqual(diff['state'],'baseline');self.assertEqual(diff['added'],0);self.assertEqual(diff['changes'],[])
    def test_section_changes_do_not_depend_on_xml_generated_ids(self):
        before={'units':[{'key':'section:1','label':'Section 1','heading':'One','text':'Old','source_id':'d2e1'}]}
        after=copy.deepcopy(before);after['units'][0]['source_id']='d2e999'
        self.assertEqual(diff_units(before,after)['state'],'unchanged')
        after['units'][0]['text']='New';self.assertEqual(diff_units(before,after)['changed'],1)
    def test_pending_effective_metadata_preserved_separately(self):
        reg=next(d for d in self.capture['documents'] if d['id']=='pipa-reg')
        self.assertTrue(any(a['effective']=='2027-08-01' for a in reg['effective_annotations']))
        self.assertFalse(any('effective' in unit for unit in reg['units']))
    def test_raw_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);shutil.copytree(ROOT/'data',root/'data');path=root/'data'/self.capture['sources'][0]['archive_path'];path.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'source hash mismatch'):manifest(root)
