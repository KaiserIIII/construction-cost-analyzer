import csv
import io
import unittest
from cost_analyzer.benchmarks import benchmark, generate_scenarios, read_boq_csv, scenario_csv

FIELDS='project_id,building_type,region,currency,floor_area_m2,budget,actual_cost,base_index,location_index,cost_scope,source_type,source_ref,price_date'


class BenchmarkTests(unittest.TestCase):
    def test_index_and_location_normalization_on_comparable_subset(self):
        text=FIELDS+'\nA,office,UK,GBP,100,10000,12000,100,100,building,observed,internal,2024-01-01\nB,office,UK,GBP,100,15000,24000,120,105,building,observed,internal,2024-01-01\n'
        r=benchmark(text,{'currency':'GBP','cost_scope':'building','source_type':'observed'},120,105)
        self.assertEqual(r['sample_count'],2)
        self.assertEqual(r['median_cost_per_m2'],195.6)
        self.assertEqual(r['mean_deviation_pct'],40)
        self.assertEqual(r['over_budget_count'],2)

    def test_source_types_scopes_and_currency_not_silently_mixed(self):
        row='A,office,UK,GBP,100,10000,12000,100,100,building,observed,internal,2024-01-01\n'
        for changed in [row.replace('A,','B,').replace('GBP','CNY'),row.replace('A,','B,').replace('building,','all-in,'),row.replace('A,','B,').replace('observed','synthetic')]:
            with self.assertRaises(ValueError):
                benchmark(FIELDS+'\n'+row+changed,{},100,100)

    def test_invalid_csv_rows_rejected_with_row_context(self):
        for row in ['A,office,UK,GBP,0,100,120,100,100,building,observed,internal,2024-01-01',
                    'A,office,UK,GBP,100,0,120,100,100,building,observed,internal,2024-01-01',
                    'A,office,UK,GBP,100,100,nan,100,100,building,observed,internal,2024-01-01']:
            with self.assertRaisesRegex(ValueError,'row 2'):
                benchmark(FIELDS+'\n'+row,{},100,100)

    def test_500_deterministic_cases_with_provenance(self):
        a=generate_scenarios(500,42)
        self.assertEqual(a,generate_scenarios(500,42))
        self.assertNotEqual(a,generate_scenarios(500,43))
        self.assertEqual(len(a),500)
        self.assertEqual(len({r['project_id'] for r in a}),500)
        self.assertTrue(all(r['source_type']=='synthetic' for r in a))
        r=benchmark(scenario_csv(a),{'currency':'GBP','cost_scope':'building'},100,100)
        self.assertEqual(r['sample_count'],500)
        self.assertTrue(r['warnings'])

    def test_empty_selected_subset_returns_explicit_error(self):
        with self.assertRaisesRegex(ValueError,'No comparable'):
            benchmark(scenario_csv(generate_scenarios(5,42)),{'currency':'CNY'},100,100)

    def test_boq_csv_preserves_price_precision_and_validates_schema(self):
        rows=read_boq_csv('item_id,description,element,unit,quantity,rate,currency,source_ref,price_date\nA,Wall,Walls,m2,100,62.832,GBP,self-authored,2026-01-01\n')
        self.assertEqual(rows[0]['rate'],'62.832')
        with self.assertRaises(ValueError):
            read_boq_csv('name,cost\nX,100\n')


if __name__=='__main__':
    unittest.main()
