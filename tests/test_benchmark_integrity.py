"""Benchmark identity and evidence regressions using synthetic arithmetic only."""
import io
import json
from decimal import Decimal
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

from cost_analyzer.benchmarks import benchmark, read_projects, scenario_csv
from cost_analyzer.reporting import report_bundle
from cost_analyzer.web import create_server

ROOT = Path(__file__).resolve().parents[1]


def fixture(project_id='A', building_type='office'):
    return dict(project_id=project_id, building_type=building_type, region='fixture',
                currency='GBP', floor_area_m2=1, budget=1_000_000_000,
                actual_cost=1_000_000_000, base_index=100, location_index=100,
                cost_scope='building', source_type='synthetic',
                source_ref='arithmetic regression fixture, not market data',
                price_date='2026-01-01', index_type='synthetic',
                index_series='arithmetic_fixture', index_base_year='reference_100')


def replay(inputs):
    return benchmark(inputs['csv'], inputs['filters'], inputs['target_index'],
                     inputs['target_location_index'])


class BenchmarkIntegrityTests(unittest.TestCase):
    def test_duplicate_identity_rejected_after_whitespace_normalization(self):
        for identity in (' A ', '\tA', 'A\u3000'):
            with self.subTest(identity=identity):
                with self.assertRaisesRegex(ValueError, r'CSV row 3: project_id duplicated'):
                    read_projects(scenario_csv([fixture('A'), fixture(identity)]))

    def test_normalization_preserves_distinct_case_sensitive_identifiers(self):
        rows = read_projects(scenario_csv([fixture(' A '), fixture('a')]))
        self.assertEqual([row['project_id'] for row in rows], ['A', 'a'])

    def test_none_and_empty_object_keep_all_records(self):
        content = scenario_csv([fixture('A'), fixture('B')])
        for filters in (None, {}):
            with self.subTest(filters=filters):
                self.assertEqual(benchmark(content, filters)['sample_count'], 2)

    def test_falsey_non_object_filters_are_rejected(self):
        for filters in ([], '', False, 0):
            with self.subTest(filters=filters):
                with self.assertRaisesRegex(ValueError, 'filters: use an object'):
                    benchmark(scenario_csv([fixture()]), filters)

    def test_caller_filter_mutation_does_not_rewrite_report_evidence(self):
        filters = {'building_type': 'housing'}
        report = benchmark(scenario_csv([fixture('A', 'housing'), fixture('B')]), filters)
        filters['building_type'] = 'office'
        self.assertEqual(report['inputs']['filters'], {'building_type': 'housing'})
        self.assertEqual(replay(report['inputs'])['projects'], report['projects'])

    def test_report_filter_mutation_does_not_mutate_callers_inputs(self):
        filters = {'building_type': 'housing'}
        report = benchmark(scenario_csv([fixture('A', 'housing')]), filters)
        report['inputs']['filters']['building_type'] = 'office'
        self.assertEqual(filters, {'building_type': 'housing'})

    def test_nested_json_filter_values_are_detached(self):
        # Preserve existing falsey wildcard semantics while copying owned JSON.
        filters = {'region': []}
        report = benchmark(scenario_csv([fixture()]), filters)
        filters['region'].append('changed')
        self.assertEqual(report['inputs']['filters'], {'region': []})

    def test_filter_snapshot_rejects_unserializable_and_nonfinite_values(self):
        for value in (set(), float('nan'), float('inf')):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'filters:'):
                    benchmark(scenario_csv([fixture()]), {'region': value})

    def test_exact_target_snapshot_replays_both_indexes(self):
        for field in ('target_index', 'target_location_index'):
            with self.subTest(field=field):
                result = benchmark(scenario_csv([fixture()]), **{field: '100.0000004'})
                self.assertEqual(result['median_cost_per_m2'], 1_000_000_004.00)
                self.assertEqual(Decimal(str(result['inputs'][field])), Decimal('100.0000004'))
                self.assertEqual(replay(result['inputs']), result)
                self.assertEqual(result[field], 100.0)  # Existing display contract.

    def test_json_snapshot_supports_existing_target_numeric_types(self):
        for value in (100, 100.0000004, '100.0000004', Decimal('100.0000004'), '1.000000004e2'):
            with self.subTest(value=value):
                result = benchmark(scenario_csv([fixture()]), target_index=value)
                saved = json.loads(json.dumps(result['inputs'], allow_nan=False))
                self.assertEqual(replay(saved), result)

    def test_seeded_index_pairs_replay_without_numerical_drift(self):
        rng = random.Random(20261015)
        for _ in range(64):
            target = str(Decimal(rng.randrange(90_000_000_001, 110_000_000_000)) / 1_000_000_000)
            location = str(Decimal(rng.randrange(90_000_000_001, 110_000_000_000)) / 1_000_000_000)
            with self.subTest(target=target, location=location):
                result = benchmark(scenario_csv([fixture()]), target_index=target,
                                   target_location_index=location)
                self.assertEqual(replay(json.loads(json.dumps(result['inputs']))), result)

    def test_library_delivery_bundle_keeps_exact_replay_inputs(self):
        result = benchmark(scenario_csv([fixture()]), target_index='100.0000004')
        with zipfile.ZipFile(io.BytesIO(report_bundle(result))) as archive:
            saved = json.loads(archive.read('inputs.json'))
            self.assertEqual(replay(saved), json.loads(archive.read('result.json')))

    def test_real_cli_bundle_inputs_reproduce_original_result(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.csv'
            source.write_text(scenario_csv([fixture()]), encoding='utf-8')
            process = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cost_analyzer',
                'benchmark', '--input', str(source), '--target-index', '100.0000004',
                '--output', str(Path(directory) / 'delivery')], cwd=ROOT,
                capture_output=True, text=True, encoding='utf-8', timeout=20)
            self.assertEqual(process.returncode, 0, process.stderr)
            output = json.loads(process.stdout)
            with zipfile.ZipFile(output['files']['zip']) as archive:
                saved = json.loads(archive.read('inputs.json'))
                original = json.loads(archive.read('result.json'))
            self.assertEqual(original['median_cost_per_m2'], 1_000_000_004.00)
            self.assertEqual(replay(saved), original)


class BenchmarkHttpIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def post(self, path, data):
        return urlopen(Request(self.base + path, data=json.dumps(data).encode('utf-8'),
                              headers={'Content-Type': 'application/json'}), timeout=10)

    def test_api_returns_replayable_precision_snapshot(self):
        data = {'csv': scenario_csv([fixture()]), 'target_location_index': '100.0000004'}
        with self.post('/api/benchmark', data) as response:
            result = json.load(response)
        self.assertEqual(result['median_cost_per_m2'], 1_000_000_004.00)
        self.assertEqual(replay(result['inputs']), result)

    def test_api_rejects_ambiguous_duplicate_ids_and_invalid_filters(self):
        inputs = [{'csv': scenario_csv([fixture('A'), fixture(' A ')])},
                  {'csv': scenario_csv([fixture()]), 'filters': []}]
        for data in inputs:
            with self.subTest(data=data):
                with self.assertRaises(HTTPError) as caught:
                    self.post('/api/benchmark', data)
                self.assertEqual(caught.exception.code, 400)
                caught.exception.close()

    def test_actual_http_export_retains_original_precise_request_inputs(self):
        inputs = {'csv': scenario_csv([fixture()]), 'filters': {},
                  'target_index': '100.0000004', 'target_location_index': 100}
        with self.post('/api/export', {'tool': 'benchmark', 'format': 'zip',
                                      'inputs': inputs, 'language': 'bilingual'}) as response:
            download = json.load(response)
        with urlopen(self.base + download['url'], timeout=10) as response:
            body = response.read()
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            saved = json.loads(archive.read('inputs.json'))
            original = json.loads(archive.read('result.json'))
        self.assertEqual(saved, inputs)  # Existing export captures request, not display.
        replayed = replay(saved)
        # HTTP export deliberately stores native request types; compare computations.
        original.pop('inputs')
        replayed.pop('inputs')
        self.assertEqual(replayed, original)


if __name__ == '__main__':
    unittest.main()
