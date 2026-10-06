import csv
import hashlib
import io
import json
import re
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from cost_analyzer import reporting
from cost_analyzer.development import development
from cost_analyzer.examples import development_example

NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

class ProfessionalExportTests(unittest.TestCase):
    def test_large_valid_development_uses_compact_check_formulas(self):
        from copy import deepcopy
        data=development_example()
        template=data['options'][0]
        data['options']=[{**deepcopy(template),'name':f'Option {i}',
                         'units':[deepcopy(template['units'][0]) for _ in range(200)]} for i in range(20)]
        archive=self.xlsx_parts(development(data))
        formulas=[c.text for c in ET.fromstring(archive.read('xl/worksheets/sheet7.xml')).findall('.//s:f',NS)]
        self.assertTrue(all(len(f)<=8192 for f in formulas),max(map(len,formulas)))
        self.assertTrue(any('SUMPRODUCT(' in f for f in formulas))

    def test_units_follow_measurement_and_rate_basis(self):
        from cost_analyzer.engine import takeoff,unit_rate
        result=unit_rate({'unit':'m2','materials':[{'name':'Mortar','consumption':2,'pack_price':10,'pack_size':1}]})
        records=list(reporting.long_records(result))
        row=next(r for r in records if r['section']=='materials' and r['field']=='cost_per_unit')
        self.assertEqual(row['unit'],'money/m2')
        for result,key,expected in [(result,'quoted_rate','money/m2'),
            (takeoff({'method':'volume','length':2,'width':3,'height':4}),'quantity','m3')]:
            archive=self.xlsx_parts(result)
            xml=ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
            rows=xml.findall('.//s:row',NS)
            target=next(r for r in rows if any(c.find('s:is/s:t',NS) is not None and c.find('s:is/s:t',NS).text==key for c in r))
            self.assertIn(expected,[c.find('s:is/s:t',NS).text for c in target if c.find('s:is/s:t',NS) is not None])

    def test_large_csv_source_is_retained_but_not_one_excel_cell(self):
        from cost_analyzer.benchmarks import benchmark,scenario_csv,generate_scenarios
        source=scenario_csv(generate_scenarios(500))
        result=benchmark(source,{'building_type':'housing'})
        bundle=ZipFile(io.BytesIO(reporting.report_bundle(result)))
        self.assertEqual(json.loads(bundle.read('inputs.json'))['csv'],source)
        book=ZipFile(io.BytesIO(bundle.read('estimate.xlsx')))
        for name in book.namelist():
            if name.startswith('xl/worksheets/'):
                for cell in ET.fromstring(book.read(name)).findall('.//s:t',NS):
                    self.assertLessEqual(len(cell.text or ''),32767)

    def setUp(self):
        self.result=development(development_example())

    def xlsx_parts(self,result=None):
        self.assertTrue(hasattr(reporting,'report_xlsx'),'Native workbook export is missing')
        blob=reporting.report_xlsx(result or self.result)
        return ZipFile(io.BytesIO(blob))

    def test_long_csv_has_single_uniform_header_and_stable_ids(self):
        rows=list(csv.reader(io.StringIO(reporting.report_csv(self.result))))
        self.assertEqual(rows[0],['section','row_id','option_id','field','value','unit','currency','source_ref'])
        self.assertTrue(all(len(r)==8 for r in rows))
        records=list(csv.DictReader(io.StringIO(reporting.report_csv(self.result))))
        profit=next(r for r in records if r['option_id']=='O001' and r['section']=='option_comparison' and r['field']=='profit')
        self.assertEqual(float(profit['value']),self.result['options'][0]['profit'])
        self.assertEqual(profit['unit'],'money')
        area=next(r for r in records if r['option_id']=='O001' and r['section']=='housing' and r['field']=='gifa_m2')
        self.assertEqual(area['unit'],'m2')
        self.assertEqual(json.loads(next(r['value'] for r in records if r['section']=='inputs_json')),self.result['inputs'])
        ids={r['row_id'] for r in records if r['section']=='cashflows'}
        self.assertEqual(len(ids),18)

    def test_xlsx_typed_values_percent_dates_and_literal_strings(self):
        self.result['options'][0]['name']='=HYPERLINK("x")\x01'
        archive=self.xlsx_parts()
        for name in archive.namelist():
            if name.endswith('.xml'):ET.fromstring(archive.read(name))
        summary=ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        cells=summary.findall('.//s:c',NS)
        self.assertTrue(any(c.get('t')=='inlineStr' and '=HYPERLINK' in ''.join(c.itertext()) for c in cells))
        self.assertTrue(any(c.get('t')=='b' for c in cells))
        self.assertTrue(any(c.find('s:v',NS) is not None and c.find('s:v',NS).text==str(self.result['options'][0]['total']) for c in cells))
        pct=self.result['options'][0]['return_on_cost_pct']/100
        self.assertTrue(any(c.find('s:v',NS) is not None and abs(float(c.find('s:v',NS).text)-pct)<1e-12 for c in cells if c.get('t') not in ('inlineStr','b')))
        cash=ET.fromstring(archive.read('xl/worksheets/sheet4.xml'))
        self.assertTrue(any(c.get('s')=='5' for c in cash.findall('.//s:c',NS)))
        self.assertIsNotNone(cash.find('s:autoFilter',NS))
        self.assertIsNotNone(cash.find('.//s:pane',NS))
        workbook=ET.fromstring(archive.read('xl/workbook.xml'))
        self.assertEqual([s.get('name') for s in workbook.findall('s:sheets/s:sheet',NS)],['Summary','Cost plan','Housing','Cashflow','Sensitivity','Inputs','Checks'])
        self.assertNotIn('xl/vbaProject.bin',archive.namelist())
        self.assertFalse(any('externalLink' in p for p in archive.namelist()))

    def test_checks_reconcile_and_expose_corrupted_output(self):
        archive=self.xlsx_parts()
        checks=ET.fromstring(archive.read('xl/worksheets/sheet7.xml'))
        formulas=checks.findall('.//s:c[s:f]',NS)
        self.assertGreaterEqual(len(formulas),18)
        self.assertTrue(any('Housing!' in c.find('s:f',NS).text for c in formulas))
        self.assertTrue(any('Cashflow!' in c.find('s:f',NS).text for c in formulas))
        self.assertTrue(all(c.find('s:v',NS) is not None for c in formulas))
        self.assertTrue(all(abs(float(c.find('s:v',NS).text))<.2 for c in formulas))
        self.result['options'][0]['gifa_m2']+=100
        corrupt=ET.fromstring(self.xlsx_parts().read('xl/worksheets/sheet7.xml'))
        self.assertTrue(any(abs(float(c.find('s:v',NS).text))==100 for c in corrupt.findall('.//s:c[s:f]',NS)))

    def test_zip_is_complete_deterministic_hashed_and_all_detail_rows_survive(self):
        self.assertTrue(hasattr(reporting,'report_bundle'),'ZIP export is missing')
        blob=reporting.report_bundle(self.result)
        self.assertEqual(blob,reporting.report_bundle(self.result))
        archive=ZipFile(io.BytesIO(blob))
        self.assertTrue({'report.html','estimate.xlsx','inputs.json','result.json','manifest.json'}<=set(archive.namelist()))
        manifest=json.loads(archive.read('manifest.json'))
        self.assertEqual(set(manifest['members']),set(archive.namelist())-{'manifest.json'})
        for name,info in manifest['members'].items():
            content=archive.read(name)
            self.assertEqual(info['sha256'],hashlib.sha256(content).hexdigest())
            self.assertEqual(info['byte_length'],len(content))
        rows=list(csv.DictReader(io.StringIO(archive.read('tables/cashflows.csv').decode('utf-8-sig'))))
        self.assertEqual(len(rows),18)
        self.assertEqual(rows[0]['option_id'],'O001')
        self.assertIn('source_ref',rows[0])
        sensitivities=list(csv.DictReader(io.StringIO(archive.read('tables/sensitivity.csv').decode('utf-8-sig'))))
        self.assertEqual(len(sensitivities),27)
        self.assertTrue(archive.read('tables/housing.csv').startswith(b'\xef\xbb\xbf'))

    def test_language_snapshot_and_unknown_settings_render_without_raw_json_body(self):
        self.result['effective_settings']={'loan_share_pct':0,'cost_changes_pct':[-10,0,20],'future_control':{'flag':False}}
        english=reporting.report_html(self.result,language='en')
        chinese=reporting.report_html(self.result,language='zh')
        self.assertIn('Option comparison',english)
        self.assertNotIn('方案比较',english)
        self.assertIn('方案比较',chinese)
        self.assertNotIn('Option comparison',chinese)
        self.assertIn('Recalculate',english)
        self.assertNotIn('<pre',english)
        self.assertIn('future_control.flag',english)
        self.assertIn('Self-authored',english)
        self.assertIn('O001',english)
        with self.assertRaises(ValueError):reporting.report_html(self.result,language='fr')

    def test_export_writes_five_deliverables_and_non_development_relevant_sheets(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=reporting.export_report({'currency':'GBP','total':12.34,'inputs':{'rate':-2}},tmp,'sample',language='en')
            self.assertEqual(set(paths),{'json','csv','html','xlsx','zip'})
            self.assertTrue(all(Path(p).stat().st_size for p in paths.values()))
        archive=self.xlsx_parts({'currency':'GBP','total':12.34})
        workbook=ET.fromstring(archive.read('xl/workbook.xml'))
        self.assertEqual([s.get('name') for s in workbook.findall('s:sheets/s:sheet',NS)],['Summary','Checks'])
        summary=ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        self.assertTrue(any(c.get('s')=='3' and c.find('s:v',NS) is not None and c.find('s:v',NS).text=='12.34' for c in summary.findall('.//s:c',NS)))


    def test_money_area_and_adopted_percent_units_are_unambiguous(self):
        records=list(csv.DictReader(io.StringIO(reporting.report_csv(self.result))))
        expected={'cost_per_m2':'money/m2','cost_per_unit':'money/dwelling','adjusted_rate':'money/m2'}
        for field,unit in expected.items():
            found=[r for r in records if r['field']==field]
            self.assertTrue(found,field)
            self.assertTrue(all(r['unit']==unit for r in found),field)
        land_base=next(r for r in records if r['section']=='breakdown' and r['option_id']=='O001' and r['field']=='label' and r['value']=='land_cost')
        self.assertEqual(next(r['unit'] for r in records if r['row_id']==land_base['row_id'] and r['field']=='base'),'m2')

    def test_non_development_standard_warning_is_translated(self):
        from cost_analyzer.engine import early_estimate
        result=early_estimate({'area_m2':10,'base_rate':10})
        chinese=reporting.report_html(result,'zh')
        self.assertNotIn('Record the rate source and price date',chinese)
        self.assertIn('来源',chinese)

    def test_formulas_recompute_from_saved_cross_sheet_numeric_cells(self):
        import re
        archive=self.xlsx_parts()
        names=['Summary','Cost plan','Housing','Cashflow','Sensitivity','Inputs','Checks']
        values={}
        for i,name in enumerate(names,1):
            root=ET.fromstring(archive.read(f'xl/worksheets/sheet{i}.xml'))
            for c in root.findall('.//s:c',NS):
                v=c.find('s:v',NS)
                if v is not None:values[(name,c.get('r'))]=float(v.text)
        checks=ET.fromstring(archive.read('xl/worksheets/sheet7.xml'))
        for c in checks.findall('.//s:c[s:f]',NS):
            expr=c.find('s:f',NS).text
            def product(match):
                ranges=[]
                for token in match.group(1).split(','):
                    sheet,start,end=re.fullmatch(r'([A-Za-z]+)!([A-Z]+[0-9]+):([A-Z]+[0-9]+)',token).groups()
                    col,start_row=re.fullmatch(r'([A-Z]+)([0-9]+)',start).groups()
                    end_row=int(re.search(r'[0-9]+',end).group())
                    ranges.append([values[(sheet,col+str(i))] for i in range(int(start_row),end_row+1)])
                import math
                return str(sum(math.prod(items) for items in zip(*ranges)))
            expr=re.sub(r'SUMPRODUCT\(([^()]*)\)',product,expr)
            expr=re.sub(r"(?:'([^']+)'|([A-Za-z]+))!([A-Z]+[0-9]+)",lambda m:str(values[(m.group(1) or m.group(2),m.group(3))]),expr)
            expr=re.sub(r'SUM\(([^()]*)\)',lambda m:'('+m.group(1).replace(',', '+')+')',expr)
            self.assertIsNotNone(re.fullmatch(r'[0-9.eE+*/()\s-]+',expr))
            recomputed=eval(expr,{'__builtins__':{}},{})
            self.assertAlmostEqual(recomputed,float(c.find('s:v',NS).text),places=6)


    def test_identity_from_source_inputs_leads_report_and_manifest(self):
        self.result['inputs'].update(report_reference='JOB-27',revision='B',estimate_date='2026-10-06',prepared_by='Estimator',client_name='Client')
        html=reporting.report_html(self.result,'en')
        self.assertLess(html.index('JOB-27'),html.index('Option comparison'))
        archive=ZipFile(io.BytesIO(reporting.report_bundle(self.result,'en')))
        manifest=json.loads(archive.read('manifest.json'))
        self.assertEqual(manifest['metadata']['report_reference'],'JOB-27')
        self.assertEqual(manifest['metadata']['estimate_date'],'2026-10-06')
        summary=ET.fromstring(self.xlsx_parts().read('xl/worksheets/sheet1.xml'))
        self.assertIn('JOB-27',''.join(summary.itertext()))

    def test_browser_numeric_source_strings_become_typed_cells_without_changing_json(self):
        self.result['inputs'].update(loan_share_pct='12.5',site_area_m2='600.123456',price_date='2026-10-06',source_ref='=HYPERLINK("bad")')
        archive=self.xlsx_parts()
        inputs=ET.fromstring(archive.read('xl/worksheets/sheet6.xml'))
        matched={}
        for r in inputs.findall('s:sheetData/s:row',NS):
            cells={re.sub(r'\d+','',c.get('r')):c for c in r.findall('s:c',NS)}
            field=cells.get('D');value=cells.get('E')
            if field is not None and value is not None:matched[''.join(field.itertext())]=value
        self.assertIsNotNone(matched['loan_share_pct'].find('s:v',NS),'Browser percentage input is saved as text instead of a native number')
        self.assertEqual(matched['loan_share_pct'].find('s:v',NS).text,'0.125')
        self.assertEqual(matched['site_area_m2'].find('s:v',NS).text,'600.123456')
        self.assertEqual(matched['price_date'].get('s'),'5')
        self.assertEqual(matched['source_ref'].get('t'),'inlineStr')
        self.assertIsNone(matched['source_ref'].find('s:f',NS))
        self.assertEqual(self.result['inputs']['loan_share_pct'],'12.5')
        html=reporting.report_html(self.result,'en')
        self.assertIn('<td>12.5%</td>',html)

if __name__=='__main__':unittest.main()
