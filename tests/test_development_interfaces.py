import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from cost_analyzer.development import development
from cost_analyzer.reporting import report_csv, report_html
from cost_analyzer.web import dispatch, create_server
from test_development import fixture

ROOT=Path(__file__).resolve().parents[1]


class DevelopmentInterfaceTests(unittest.TestCase):
    def test_actual_http_development_and_unknown_field_rejection(self):
        server=create_server(0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        endpoint=f'http://127.0.0.1:{server.server_port}/api/development'
        def request(data):return Request(endpoint,data=json.dumps(data).encode('utf-8'),headers={'Content-Type':'application/json'})
        try:
            with urlopen(request(fixture()),timeout=5) as response:
                result=json.load(response)
                self.assertEqual(result['options'][0]['total'],174110.10)
            bad=fixture();bad['overhead_profit_pct']=bad.pop('overheads_profit_pct')
            with self.assertRaises(HTTPError) as caught:urlopen(request(bad),timeout=5)
            self.assertEqual(caught.exception.code,400)
            self.assertIn('overhead_profit_pct',json.load(caught.exception)['error'])
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)

    def test_development_api_and_example_share_calculation(self):
        try:actual=dispatch('/api/development',fixture())
        except KeyError:self.fail('Development endpoint is missing')
        self.assertEqual(actual['options'][0]['total'],174110.10)
        from cost_analyzer.examples import example
        self.assertIn('development',example())
        self.assertEqual(len(dispatch('/api/development',example()['development'])['options']),3)

    def test_development_cli_exports_comparison_and_each_cashflow(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'input.json';p.write_text(json.dumps(fixture()),encoding='utf-8')
            run=subprocess.run([sys.executable,'-m','cost_analyzer','development',str(p),'--output',temp],cwd=ROOT,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr.decode('utf-8',errors='replace'))
            self.assertEqual(json.loads(run.stdout.decode('utf-8'))['result']['options'][0]['total'],174110.10)
            result=json.loads((Path(temp)/'report.json').read_text(encoding='utf-8'))
            self.assertEqual(result['options'][0]['total'],174110.10)
            self.assertIn('loan_repayment',(Path(temp)/'report.csv').read_text(encoding='utf-8-sig'))

    def test_nested_report_safety_and_completeness(self):
        d=fixture();d['options'][0]['name']='=formula';d['options'][0]['units'][0]['name']='<script>bad</script>'
        r=development(d);html=report_html(r);csv_text=report_csv(r)
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;',html)
        self.assertNotIn('<script>bad</script>',html)
        self.assertIn('Loan repayment',html)
        self.assertIn('Cost change',html)
        self.assertIn('adjusted_rate',csv_text)
        self.assertIn('equity_cashflow',csv_text)
        self.assertIn('cost_change_pct',csv_text)
        rows=list(csv.reader(io.StringIO(csv_text)))
        self.assertTrue(any("'=formula" in row for row in rows))
        self.assertTrue(any(row and row[0]=='inputs_json' for row in rows))


if __name__=='__main__':unittest.main()
