import csv
import io
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from cost_analyzer.reporting import report_html, report_csv, export_report
from cost_analyzer.web import create_server

ROOT=Path(__file__).resolve().parents[1]


class ReportTests(unittest.TestCase):
    def test_untrusted_html_and_csv_formula_text_escaped(self):
        r={'project_name':'<script>alert(1)</script>','currency':'GBP','total':10,
           'items':[dict(item_id='@cmd',description='=HYPERLINK("bad")',element='Wall',unit='m2',quantity=1,rate=10,total=10)]}
        html=report_html(r)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)
        rows=list(csv.reader(io.StringIO(report_csv(r))))
        self.assertTrue(any("'=HYPERLINK" in cell for row in rows for cell in row))

    def test_report_outputs_reconcile_and_preserve_json_values(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=export_report({'currency':'GBP','total':12.34},Path(directory),'test')
            self.assertEqual(set(paths),{'json','csv','html','xlsx','zip'})
            self.assertEqual(json.loads(Path(paths['json']).read_text(encoding='utf-8'))['total'],12.34)
            self.assertTrue(all(Path(p).stat().st_size>0 for p in paths.values()))

    def test_real_cli_demo_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            result=subprocess.run([sys.executable,'-m','cost_analyzer','demo','--output',directory],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads((Path(directory)/'early.json').read_text(encoding='utf-8'))
            self.assertEqual(data['total'],1455300)
            self.assertTrue((Path(directory)/'boq.csv').exists())
            bad=Path(directory)/'bad.json';bad.write_text('{"area_m2":0,"base_rate":100}',encoding='utf-8')
            failed=subprocess.run([sys.executable,'-m','cost_analyzer','estimate',str(bad)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(failed.returncode,2)
            self.assertIn('area_m2',failed.stderr)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=create_server(port=0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5)

    def request(self,path,data=None,headers=None):
        body=json.dumps(data).encode() if data is not None else None
        request=Request(self.base+path,data=body,headers={'Content-Type':'application/json',**(headers or {})})
        return urlopen(request,timeout=5)

    def test_actual_api_calculation_and_example_and_dataset(self):
        with self.request('/api/example') as response:
            example=json.load(response)
        with self.request('/api/early',example['early']) as response:
            self.assertEqual(json.load(response)['total'],1455300)
        with self.request('/api/boq',example['boq']) as response:
            result=json.load(response)
        self.assertEqual(result['total'],sum(row['amount'] for row in result['breakdown']))
        with self.request('/api/dataset') as response:
            self.assertEqual(json.load(response)['metadata']['sample_count'],500)

    def test_validation_errors_and_foreign_origin(self):
        for data,headers,expected in [({'area_m2':0,'base_rate':100},{},400),
                                      ({'area_m2':100,'base_rate':100},{'Origin':'https://unrelated.example'},403)]:
            with self.assertRaises(HTTPError) as ctx:
                self.request('/api/early',data,headers)
            self.assertEqual(ctx.exception.code,expected)
        with self.assertRaises(HTTPError) as ctx:
            urlopen(Request(self.base+'/api/early',data=b'not-json',headers={'Content-Type':'application/json'}))
        self.assertEqual(ctx.exception.code,400)

    def test_only_known_static_routes_and_no_local_file_access(self):
        for path in ['/../README.md','/api/files?path=README.md','/unknown']:
            with self.assertRaises(HTTPError) as ctx:
                self.request(path)
            self.assertEqual(ctx.exception.code,404)


if __name__=='__main__':unittest.main()
