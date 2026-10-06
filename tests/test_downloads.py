import json
import threading
import unittest
import subprocess
import sys
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from cost_analyzer.web import create_server
from tests.test_development import fixture


class DownloadTests(unittest.TestCase):
    def test_native_input_attachment_roundtrips_before_calculation(self):
        server=create_server(0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        def post(body):
            return urlopen(Request(base+'/api/source',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=10)
        inputs={'site_area_m2':'','options':[],'cost_changes_pct':[-10,0,10]}
        body={'filename':'development-inputs.json','content':json.dumps(inputs)}
        try:
            with post(body) as response:link=json.load(response)
            with urlopen(base+link['url'],timeout=10) as response:
                self.assertIn('development-inputs.json',response.headers['Content-Disposition'])
                self.assertEqual(json.load(response),inputs)
            for changes in [{'filename':'../../private.json'},{'content':'NaN'},{'content':'[]'},{'filename':'report.exe'},{'extra':0}]:
                with self.subTest(changes=changes),self.assertRaises(HTTPError) as caught:post({**body,**changes})
                self.assertEqual(caught.exception.code,400)
        finally:server.shutdown();server.server_close();thread.join(timeout=5)

    def test_filtered_benchmark_exports_keep_native_source(self):
        import csv,io
        from zipfile import ZipFile
        from cost_analyzer.benchmarks import generate_scenarios,scenario_csv
        from cost_analyzer.web import prepare_export
        source=scenario_csv(generate_scenarios(20));inputs={'csv':source,'filters':{'building_type':'housing'}}
        request={'tool':'benchmark','inputs':inputs,'language':'en'}
        blob,_,_=prepare_export({**request,'format':'json'})
        self.assertEqual(json.loads(blob)['inputs'],inputs)
        blob,_,_=prepare_export({**request,'format':'zip'})
        self.assertEqual(json.loads(ZipFile(io.BytesIO(blob)).read('inputs.json')),inputs)
        blob,_,_=prepare_export({**request,'format':'csv'})
        rows=list(csv.DictReader(io.StringIO(blob.decode('utf-8-sig'))))
        self.assertEqual(json.loads(next(r['value'] for r in rows if r['section']=='inputs_json')),inputs)

    def test_cli_language_and_complete_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'inputs.json';source.write_text(json.dumps(fixture()),encoding='utf-8')
            run=subprocess.run([sys.executable,'-m','cost_analyzer','development',str(source),'--output',folder,'--language','en'],capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr.decode('utf-8',errors='replace'))
            for suffix in ['xlsx','zip','html','json','csv']:self.assertTrue((Path(folder)/('report.'+suffix)).exists())
            html=(Path(folder)/'report.html').read_text(encoding='utf-8')
            self.assertIn('Option',html);self.assertNotIn('方案比较',html)

    def test_ttl_limits_and_concurrent_unique_tokens(self):
        from cost_analyzer.downloads import DownloadStore
        now=[100.0];store=DownloadStore(ttl=10,max_count=2,max_bytes=6,clock=lambda:now[0])
        a=store.put(b'aaa','report.json','application/json')
        self.assertEqual(store.get(a)[0],b'aaa')
        store.put(b'bbb','report.json','application/json');c=store.put(b'cc','report.json','application/json')
        self.assertIsNone(store.get(a));self.assertEqual(store.get(c)[0],b'cc')
        with self.assertRaises(ValueError):store.put(b'1234567','report.json','application/json')
        now[0]+=11;self.assertIsNone(store.get(c))
        store=DownloadStore(max_count=50)
        with ThreadPoolExecutor(max_workers=8) as pool:
            tokens=list(pool.map(lambda _:store.put(b'1','report.json','application/json'),range(40)))
        self.assertEqual(len(set(tokens)),40)
        self.assertTrue(all(store.get(token) for token in tokens))

    def test_actual_attachment_recalculates_and_validates_request(self):
        server=create_server(0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        def request(body,headers=None):
            return urlopen(Request(base+'/api/export',data=json.dumps(body).encode(),
                headers={'Content-Type':'application/json',**(headers or {})}),timeout=10)
        body={'tool':'development','format':'json','inputs':fixture(),'language':'en'}
        try:
            with request(body) as response:link=json.load(response)
            self.assertEqual(link['expires_in'],600);self.assertTrue(link['url'].startswith('/download/'))
            with urlopen(base+link['url'],timeout=10) as response:
                self.assertIn('attachment',response.headers['Content-Disposition'])
                self.assertEqual(response.headers['Cache-Control'],'no-store')
                self.assertEqual(json.load(response)['options'][0]['total'],174110.10)
            for changes in [{'result':{'total':1}},{'tool':'unknown'},{'format':'exe'},{'language':'fr'},{'inputs':{}}, {'tool':[]}]:
                with self.subTest(changes=changes),self.assertRaises(HTTPError) as caught:request({**body,**changes})
                self.assertEqual(caught.exception.code,400)
            with self.assertRaises(HTTPError) as caught:request(body,{'Origin':'https://bad.example'})
            self.assertEqual(caught.exception.code,403)
            for path in ['/download/not-a-token','/download/../../README.md']:
                with self.assertRaises(HTTPError) as caught:urlopen(base+path,timeout=10)
                self.assertEqual(caught.exception.code,404)
        finally:server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':unittest.main()
