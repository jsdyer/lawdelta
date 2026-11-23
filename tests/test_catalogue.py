import sys
import unittest
import tempfile
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_catalogue import parse_page
from collect_catalogue import collect
from archive import digest
class CatalogueTests(unittest.TestCase):
    def test_metadata_retains_kind_and_safe_source_link(self):
        raw=b'<results totalhits="1"><doc><CIVIX_DOCUMENT_TITLE>Point in Time - Privacy Act</CIVIX_DOCUMENT_TITLE><CIVIX_DOCUMENT_ID>privacy_pit</CIVIX_DOCUMENT_ID><CIVIX_INDEX_ID>statreg</CIVIX_INDEX_ID></doc></results>'
        count,rows=parse_page(raw)
        self.assertEqual(count,1)
        self.assertEqual(rows[0]['kind'],'Historical / point in time')
        self.assertTrue(rows[0]['url'].endswith('/statreg/privacy_pit'))
    def test_rejects_incomplete_records(self):
        with self.assertRaises(ValueError):parse_page(b'<results totalhits="1"><doc/></results>')
    def test_failed_pagination_preserves_previous_catalogue(self):
        def provider(url,*args):
            start=int(parse_qs(urlsplit(url).query)['s'][0])
            # A changing catalogue repeats one earlier identifier in its next page.
            ids=range(20) if start else range(20)
            raw=('<results totalhits="100">'+''.join(f'<doc><CIVIX_DOCUMENT_TITLE>Act {i}</CIVIX_DOCUMENT_TITLE><CIVIX_DOCUMENT_ID>{i}</CIVIX_DOCUMENT_ID><CIVIX_INDEX_ID>statreg</CIVIX_INDEX_ID></doc>' for i in ids)+'</results>').encode()
            return raw,{'url':url,'sha256':digest(raw),'retrieved_at':'2026-11-23T00:00:00Z'}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir();target=root/'data/catalogue.json';target.write_text('previous validated catalogue')
            with patch('collect_catalogue.fetch',provider),patch('collect_catalogue.time.sleep',lambda _:None):
                with self.assertRaisesRegex(ValueError,'Duplicate'):collect(root)
            self.assertEqual(target.read_text(),'previous validated catalogue')
    def test_same_document_under_distinct_source_parents_is_one_result(self):
        def provider(url,*args):
            start=int(parse_qs(urlsplit(url).query)['s'][0])
            entries=[]
            for i in range(start,start+20):
                ident=0 if i==99 else i
                entries.append(f'<doc><CIVIX_DOCUMENT_TITLE>Act {ident}</CIVIX_DOCUMENT_TITLE><CIVIX_DOCUMENT_ID>{ident}</CIVIX_DOCUMENT_ID><CIVIX_INDEX_ID>statreg</CIVIX_INDEX_ID><CIVIX_DOCUMENT_PARENT>{i}</CIVIX_DOCUMENT_PARENT></doc>')
            raw=('<results totalhits="100">'+''.join(entries)+'</results>').encode()
            return raw,{'url':url,'sha256':digest(raw),'retrieved_at':'2026-11-23T00:00:00Z'}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir()
            with patch('collect_catalogue.fetch',provider),patch('collect_catalogue.time.sleep',lambda _:None):collect(root)
            import json
            data=json.loads((root/'data/catalogue.json').read_text())
            self.assertEqual(data['source_hits'],100)
            self.assertEqual(data['merged_aliases'],1)
            self.assertEqual(len(data['records']),99)
            self.assertEqual(set(next(r for r in data['records'] if r['id']=='0')['parents']),{'0','99'})
