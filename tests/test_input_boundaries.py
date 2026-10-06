import json
import unittest
from cost_analyzer.engine import early_estimate, takeoff, unit_rate, price_boq, appraise
from cost_analyzer.validation import number


class InputBoundaryTests(unittest.TestCase):
    def test_number_rejects_extreme_exponents_before_arithmetic(self):
        for value in ['1e-9999999','1e-100','1'+'0'*200,'0.'+'0'*100+'1']:
            with self.subTest(value=value),self.assertRaises(ValueError):number(value,'amount')

    def test_functions_reject_non_object_inputs_consistently(self):
        for function in [early_estimate,takeoff,unit_rate,appraise]:
            for bad in [None,[],1,'bad']:
                with self.subTest(function=function.__name__),self.assertRaises(ValueError):function(bad)

    def test_report_has_original_inputs_without_aliasing(self):
        data={'area_m2':100,'base_rate':'12.3456','source_ref':'supplier-1','price_date':'2026-01-01','index_source':{'series':'demo','period':'2026-01'}}
        result=early_estimate(data)
        self.assertEqual(result['inputs'],data)
        data['index_source']['period']='changed'
        self.assertEqual(result['inputs']['index_source']['period'],'2026-01')

    def test_boq_requires_work_description(self):
        with self.assertRaises(ValueError):
            price_boq([dict(item_id='A',description='',quantity=1,rate=2,currency='GBP')],{'currency':'GBP'})

if __name__=='__main__':unittest.main()
