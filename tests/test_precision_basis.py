import unittest
from cost_analyzer.engine import price_boq, early_estimate
from cost_analyzer.benchmarks import benchmark
from cost_analyzer.reporting import report_csv
import csv
import io


class PrecisionBasisTests(unittest.TestCase):
    def test_price_date_uses_same_iso_contract_on_every_python_version(self):
        from cost_analyzer.validation import price_date
        self.assertEqual(price_date('2026-10-06'),'2026-10-06')
        for value in ('20261006','2026-02-30','06/10/2026'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                price_date(value)

    def test_adjusted_rate_rounds_half_up_before_pricing_area(self):
        result=early_estimate({'area_m2':1000000,'base_rate':1,'base_index':100,'target_index':'100.00005'})
        self.assertEqual(result['adjusted_rate'],1.000001)
        self.assertEqual(result['direct_cost'],1000001)

    def test_benchmark_export_retains_normalization_inputs(self):
        from cost_analyzer.benchmarks import generate_scenarios, scenario_csv
        result=benchmark(scenario_csv(generate_scenarios(2,42)),{},100,100)
        rows=list(csv.reader(io.StringIO(report_csv(result))))
        header=next(row for row in rows if row and row[0]=='project_id')
        for key in ('base_index','location_index','actual_cost','floor_area_m2','price_date','index_series','source_ref'):
            self.assertIn(key,header)

    def test_boq_rejects_values_that_cannot_preserve_cents_in_json(self):
        with self.assertRaises(ValueError):
            price_boq([{'item_id':'A','description':'Huge','quantity':1,'rate':'99999999999999.99','currency':'GBP'}],{'currency':'GBP'})

    def test_boq_rejects_more_rate_digits_than_exported_precision(self):
        with self.assertRaisesRegex(ValueError,'6 decimal'):
            price_boq([{'item_id':'A','description':'Fine','quantity':1000000000,'rate':'1.000000499','currency':'GBP'}],{'currency':'GBP'})

    def test_benchmark_rejects_mixed_index_bases_and_series(self):
        header='project_id,building_type,region,currency,floor_area_m2,budget,actual_cost,base_index,location_index,cost_scope,source_type,source_ref,price_date,index_type,index_series,index_base_year\n'
        a='A,office,UK,GBP,1,100,100,110,100,building,observed,owned,2026-01-01,OPI,All new work,2015\n'
        b='B,office,UK,GBP,1,100,100,100,100,building,observed,owned,2026-01-01,OPI,All new work,2026\n'
        with self.assertRaisesRegex(ValueError,'index'):
            benchmark(header+a+b,{},110,100)

if __name__=='__main__':unittest.main()
