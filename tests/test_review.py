"""Input completeness is distinct from arithmetic validity and source verification."""
import copy
import importlib
import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def documented():
    return {
        'project_name': 'Synthetic review example', 'currency': 'GBP',
        'site_area_m2': 100, 'land_rate': 100, 'site_clearance_rate': 0,
        'facilitating_cost': 0, 'external_works_pct': 0, 'preliminaries_pct': 0,
        'overheads_profit_pct': 0, 'fees_pct': 0, 'marketing_pct': 3,
        'risk_design_pct': 0, 'risk_construction_pct': 0,
        'risk_employer_change_pct': 0, 'risk_other_pct': 0,
        'tender_inflation_pct': 0, 'construction_inflation_pct': 0,
        'rate_includes_preliminaries': False, 'rate_includes_ohp': False,
        'price_basis': 'estimate_plus_inflation', 'risk_scope': 'works_only',
        'base_index': 100, 'target_index': 100,
        'base_location_index': 100, 'target_location_index': 100,
        'loan_share_pct': 0, 'duration_months': 2, 'prep_months': 0,
        'hurdle_pct': 10, 'discount_rate_pct': 8,
        'prep_spend_pct': 0, 'start_date': '2026-11-01',
        'price_date': '2026-09-01', 'estimate_date': '2026-10-01',
        'index_source_ref': 'Self-authored constant-index example',
        'source_ref': 'Self-authored construction rate example',
        'options': [{'name': 'Synthetic option', 'units': [{
            'name': 'House', 'count': 1, 'area_m2': 100, 'base_rate': 1000,
            'sale_price': 180000, 'area_source_ref': 'Self-authored 10m x 10m envelope',
            'sale_source_ref': 'Self-authored price record; not actual market evidence',
            'sale_price_date': '2026-09-01', 'sale_basis': 'sold',
        }]}],
    }


class ReviewTests(unittest.TestCase):
    def review(self, data):
        self.assertIsNotNone(importlib.util.find_spec('cost_analyzer.review'),
                             'Development input review has not been implemented')
        return importlib.import_module('cost_analyzer.review').review_development(data)

    def test_explicit_zero_is_documented_but_absent_cost_is_blocking(self):
        data = documented()
        self.assertEqual(self.review(data)['status'], 'documented')
        del data['facilitating_cost']
        result = self.review(data)
        self.assertEqual(result['status'], 'incomplete')
        self.assertTrue(any(i['code'] == 'missing_explicit_input' and
                            i['path'] == 'facilitating_cost' for i in result['issues']))

    def test_cost_reference_does_not_satisfy_sales_evidence(self):
        data = documented()
        del data['options'][0]['units'][0]['sale_source_ref']
        result = self.review(data)
        self.assertEqual(result['status'], 'incomplete')
        self.assertTrue(any(i['path'].endswith('.sale_source_ref') for i in result['issues']))

    def test_option_override_satisfies_explicit_value_and_funding_is_conditional(self):
        data = documented()
        del data['marketing_pct']
        data['options'][0]['settings'] = {'marketing_pct': 0}
        self.assertEqual(self.review(data)['status'], 'documented')
        data['options'][0]['settings']['loan_share_pct'] = 50
        issues = self.review(data)['issues']
        self.assertTrue(any(i['path'].endswith('loan_interest_pct') for i in issues))
        self.assertTrue(any(i['path'].endswith('loan_fee_pct') for i in issues))

    def test_missing_funding_share_cannot_silently_mean_all_equity(self):
        data = documented()
        del data['loan_share_pct']
        self.assertEqual(self.review(data)['status'], 'incomplete')

    def test_metadata_is_retained_in_engine_and_export_sources(self):
        from cost_analyzer.development import development
        from cost_analyzer.reporting import report_tables
        data = documented()
        result = development(data)
        house = result['options'][0]['housing'][0]
        self.assertEqual(house.get('sale_source_ref'), data['options'][0]['units'][0]['sale_source_ref'])
        self.assertEqual(house.get('sale_price_date'), '2026-09-01')
        self.assertEqual(house.get('sale_basis'), 'sold')
        self.assertEqual(result['options'][0]['total'], 115400)
        self.assertTrue(any(r['path'].endswith('sale_source_ref') for r in report_tables(result)['sources']))

    def test_assumed_and_asking_prices_require_review_without_false_verification(self):
        for basis in ('asking', 'assumed'):
            data = documented()
            data['options'][0]['units'][0]['sale_basis'] = basis
            result = self.review(data)
            self.assertEqual(result['status'], 'review_required')
            self.assertTrue(any(i['code'] == 'sales_basis' for i in result['issues']))

    def test_future_sales_evidence_is_warned_against_estimate_date(self):
        data = documented()
        data['options'][0]['units'][0]['sale_price_date'] = '2026-10-02'
        self.assertTrue(any(i['code'] == 'evidence_after_estimate' for i in self.review(data)['issues']))

    def test_programme_records_option_dates_and_month_end(self):
        data = documented()
        data['options'][0]['settings'] = {'start_date': '2027-01-31', 'duration_months': 1}
        result = self.review(data)
        self.assertEqual(result['programmes'][0]['completion_date'], '2027-02-28')
        self.assertEqual(result['programmes'][0]['duration_months'], 1)

    def test_embedded_preliminaries_are_an_assumption_to_check(self):
        data = documented()
        data.update(rate_includes_preliminaries=True, embedded_preliminaries_pct=11)
        self.assertTrue(any(i['code'] == 'embedded_preliminaries_proxy' for i in self.review(data)['issues']))

    def test_invalid_numeric_input_is_a_structured_error(self):
        data = documented()
        data['options'][0]['units'][0]['sale_price'] = None
        result = self.review(data)
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual(result['issues'][0]['severity'], 'error')

    def test_invalid_sales_date_and_unrecognised_basis_are_rejected(self):
        from cost_analyzer.development import development
        for field, value in [('sale_price_date', '2026-02-30'), ('sale_basis', 'guess')]:
            data = documented()
            data['options'][0]['units'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                development(data)

    def test_hash_is_repeatable_key_order_independent_and_input_is_not_mutated(self):
        data = documented()
        before = copy.deepcopy(data)
        first = self.review(data)
        second = self.review(dict(reversed(list(data.items()))))
        self.assertEqual(first['input_sha256'], second['input_sha256'])
        self.assertEqual(len(first['input_sha256']), 64)
        self.assertEqual(data, before)

    def test_cli_exit_status_and_saved_review(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input.json'
            output = Path(temp) / 'review.json'
            for missing, code in [(False, 0), (True, 1)]:
                data = documented()
                if missing:
                    del data['land_rate']
                path.write_text(json.dumps(data), encoding='utf-8')
                run = subprocess.run([sys.executable, '-m', 'cost_analyzer', 'review', str(path),
                                      '--output', str(output)], cwd=ROOT, capture_output=True, encoding='utf-8')
                self.assertEqual(run.returncode, code, run.stderr)
                result = json.loads(output.read_text(encoding='utf-8'))
                self.assertEqual(json.loads(run.stdout), result)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for browser CSV roundtrip')
    def test_browser_retains_sales_evidence_and_still_accepts_legacy_csv(self):
        script = r'''
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const options = [{name:'Example', units:[{name:'House',count:1,area_m2:100,base_rate:1000,sale_price:180000,
 source_ref:'Cost record',area_source_ref:'Drawing',sale_source_ref:'Separate sales record',
 sale_price_date:'2026-09-01',sale_basis:'sold'}]}];
const csv = ui.developmentOptionsCSV(options, false);
assert.deepEqual(ui.parseDevelopmentCSV(csv), options);
const legacy = 'option,name,count,area_m2,base_rate,sale_price,source_ref,area_source_ref\nExample,House,1,100,1000,180000,Cost record,Drawing\n';
assert.equal(ui.parseDevelopmentCSV(legacy)[0].units[0].sale_price,180000);
assert.throws(()=>ui.parseDevelopmentCSV(csv.replace('sold','guess')), /sale_basis/);
'''
        run = subprocess.run(['node', '-e', script, str(ROOT / 'cost_analyzer/static/app.js')],
                             capture_output=True, encoding='utf-8')
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_download_preserves_optional_sales_columns(self):
        from cost_analyzer.web import prepare_source
        csv = ('option,name,count,area_m2,base_rate,sale_price,source_ref,area_source_ref,sale_source_ref,sale_price_date,sale_basis\n'
               'Example,House,1,100,1000,180000,Cost record,Drawing,Sales record,2026-09-01,sold\n')
        content, _, _ = prepare_source({'filename': 'development-housing.csv', 'content': csv})
        self.assertIn('Sales record,2026-09-01,sold', content.decode('utf-8-sig'))

    def test_review_output_cannot_overwrite_original_input(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input.json'
            original = json.dumps(documented()).encode('utf-8')
            path.write_bytes(original)
            run = subprocess.run([sys.executable, '-m', 'cost_analyzer', 'review', str(path),
                                  '--output', str(path)], cwd=ROOT, capture_output=True, encoding='utf-8')
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
