import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from cost_analyzer.web import dispatch, prepare_export


ROOT = Path(__file__).resolve().parents[1]


def sample():
    return {
        'project': {'currency': 'GBP', 'overheads_profit_pct': 20, 'contingency_pct': 7},
        'quantity_places': 0,
        'items': [
            {'item_id': 'F01', 'description': 'Strip concrete', 'unit': 'm3', 'rate': '120.50'},
            {'item_id': 'PC01', 'description': 'Specialist works', 'unit': 'item',
             'kind': 'pc_sum', 'quantity': 1, 'rate': 100},
            {'item_id': 'D01', 'description': 'General operative', 'unit': 'h',
             'kind': 'daywork_rate', 'rate': 25},
        ],
        'measurements': [
            {'measurement_id': 'M01', 'item_id': 'F01', 'drawing_ref': 'SK-01 Rev A',
             'timesing': 2, 'dimensions': ['4.2', '0.6', '0.3']},
            {'measurement_id': 'M02', 'item_id': 'F01', 'drawing_ref': 'SK-01 Rev A',
             'operation': 'deduct', 'dimensions': ['0.4', '0.6', '0.3'],
             'note': 'Junction overlap'},
        ],
    }


class MeasuredBoQTests(unittest.TestCase):
    def test_square_and_abstract_before_rounding_then_apply_additions(self):
        result = dispatch('/api/measured-boq', sample())
        self.assertEqual(result['taking_off'][0]['drawing_ref'], 'SK-01 Rev A')
        self.assertEqual(result['squaring'][0]['squared_quantity'], '1.512')
        self.assertEqual(result['squaring'][1]['squared_quantity'], '-0.072')
        self.assertEqual(result['abstract'][0]['net_quantity'], '1.44')
        self.assertEqual(result['abstract'][0]['quantity'], 1)
        self.assertEqual([row['total'] for row in result['items']], [120.50, 100])
        self.assertEqual(result['daywork_rates'][0]['rate'], 25)
        self.assertEqual(result['overheads_profit'], 44.10)
        self.assertEqual(result['contingency'], 18.52)
        self.assertEqual(result['total'], 283.12)

    def test_upstream_dimension_change_flows_through_to_the_bill(self):
        data = sample()
        data['measurements'][0]['dimensions'][0] = '4.5'
        result = dispatch('/api/measured-boq', data)
        self.assertEqual(result['abstract'][0]['net_quantity'], '1.548')
        self.assertEqual(result['items'][0]['quantity'], 2)
        self.assertEqual(result['total'], 437.84)

    def test_invalid_measurement_links_counts_and_deductions(self):
        for field, value, expected in [
            ('measurement_id', 'M01', 'duplicated'),
            ('item_id', 'PC01', 'measured item'),
            ('dimensions', ['0.4', '0.6'], '3 dimensions'),
            ('dimensions', ['9', '0.6', '0.3'], 'deductions exceed'),
            ('timesing', '0.5', 'whole number'),
            ('drawing_ref', '', 'drawing_ref'),
        ]:
            with self.subTest(field=field, value=value):
                data = sample()
                data['measurements'][1][field] = value
                with self.assertRaisesRegex(ValueError, expected):
                    dispatch('/api/measured-boq', data)

    def test_cannot_override_a_measured_quantity_or_extend_rate_only_dayworks(self):
        for index in (0, 2):
            with self.subTest(index=index):
                data = sample()
                data['items'][index]['quantity'] = 1
                with self.assertRaisesRegex(ValueError, 'quantity'):
                    dispatch('/api/measured-boq', data)

    def test_misspelled_addition_does_not_silently_default_to_zero(self):
        data = sample()
        data['project']['contingecy_pct'] = data['project'].pop('contingency_pct')
        with self.assertRaisesRegex(ValueError, 'contingecy_pct'):
            dispatch('/api/measured-boq', data)

    def test_export_keeps_a_separate_schedule_per_stage_and_replayable_inputs(self):
        original = sample()
        content, _, _ = prepare_export({
            'tool': 'measured-boq', 'format': 'zip', 'inputs': original, 'language': 'en',
        })
        with ZipFile(io.BytesIO(content)) as archive:
            for stage in ('taking_off', 'squaring', 'abstract', 'items', 'daywork_rates'):
                self.assertIn(f'tables/{stage}.csv', archive.namelist())
            self.assertEqual(json.loads(archive.read('inputs.json')), original)
            xlsx_name = next(name for name in archive.namelist() if name.endswith('.xlsx'))
            with ZipFile(io.BytesIO(archive.read(xlsx_name))) as workbook:
                xml = workbook.read('xl/workbook.xml').decode()
                for sheet in ('Taking off', 'Squaring', 'Abstract', 'BOQ', 'Daywork rates'):
                    self.assertIn(f'name="{sheet}"', xml)
                sheets = [workbook.read(name).decode() for name in workbook.namelist()
                          if name.startswith('xl/worksheets/sheet') and name.endswith('.xml')]
                checks = next(sheet for sheet in sheets if 'Rounded abstract quantity minus bill quantity' in sheet)
                self.assertRegex(checks, r'<f>Abstract![A-Z]+5-BOQ![A-Z]+5</f>')
                self.assertRegex(checks, r'<f>ROUND\(BOQ![A-Z]+5\*BOQ![A-Z]+5,2\)-BOQ![A-Z]+5</f>')

    def test_cli_runs_the_same_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.json'
            source.write_text(json.dumps(sample()), encoding='utf-8')
            completed = subprocess.run(
                [sys.executable, '-m', 'cost_analyzer', 'measured-boq', str(source),
                 '--output', directory], cwd=ROOT, capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode('utf-8'))
            self.assertEqual(json.loads(completed.stdout)['result']['total'], 283.12)
