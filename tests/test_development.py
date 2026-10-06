"""Independent arithmetic, cash conservation and boundary checks."""
import copy
import importlib
import importlib.util
import unittest


def fixture():
    return {'project_name':'Hand calculation','currency':'GBP','site_area_m2':100,'land_rate':100,
            'facilitating_cost':1000,'external_works_pct':10,'preliminaries_pct':10,
            'overheads_profit_pct':20,'fees_pct':5,'marketing_pct':3,
            'duration_months':2,'prep_months':1,'prep_spend_pct':50,
            'loan_share_pct':50,'loan_interest_pct':12,'loan_fee_pct':2,
            'hurdle_pct':10,'discount_rate_pct':12,'sensitivity_pct':10,
            'options':[{'name':'One dwelling','units':[{'name':'House','count':1,'area_m2':100,
                         'base_rate':1000,'sale_price':250000,'source_ref':'Original arithmetic example'}]}]}


class DevelopmentTests(unittest.TestCase):
    def calculate(self,data):
        self.assertIsNotNone(importlib.util.find_spec('cost_analyzer.development'),
                             'The multi-option development engine is missing')
        return importlib.import_module('cost_analyzer.development').development(data)

    def test_hand_oce_and_staged_interest_reconcile(self):
        result=self.calculate(fixture());r=result['options'][0]
        self.assertEqual(r['works_and_fees'],153720)
        self.assertEqual(r['interest'],1252.90)
        self.assertEqual(r['arrangement_fee'],1637.20)
        self.assertEqual(r['total'],174110.10)
        self.assertEqual(r['profit'],75889.90)
        self.assertEqual(r['loan_principal'],81860)
        self.assertEqual(r['cashflows'][0]['loan_draw'],43430)
        self.assertEqual(r['cashflows'][0]['interest'],434.30)
        self.assertEqual(r['cashflows'][1]['interest'],818.60)
        self.assertEqual(r['cashflows'][-1]['loan_repayment'],81860)
        self.assertAlmostEqual(sum(c['equity_cashflow'] for c in r['cashflows']),r['profit'],places=2)
        self.assertEqual(result['recommended_option'],'One dwelling')

    def test_months_discount_annual_rate_and_single_change_irr(self):
        d=fixture();d.update(loan_share_pct=0,loan_fee_pct=0,discount_rate_pct=12)
        r=self.calculate(d)['options'][0]
        flows=[c['budget_cashflow'] for c in r['cashflows']]
        expected=sum(v/1.12**(i/12) for i,v in enumerate(flows))
        self.assertAlmostEqual(r['budget_npv'],expected,places=2)
        annual=r['budget_irr_annual_pct']/100
        self.assertAlmostEqual(sum(v/(1+annual)**(i/12) for i,v in enumerate(flows)),0,delta=.05)

    def test_land_feedback_and_marketing_target_solutions(self):
        d=fixture();r=self.calculate(d)['options'][0]
        target=copy.deepcopy(d);target['options'][0]['units'][0]['sale_price']=r['target_gdv']
        self.assertAlmostEqual(self.calculate(target)['options'][0]['return_on_cost_pct'],10,places=4)
        residual=copy.deepcopy(d);residual['land_rate']=r['residual_land_value']/100
        self.assertAlmostEqual(self.calculate(residual)['options'][0]['return_on_cost_pct'],10,places=4)
        d.update(risk_design_pct=1,risk_construction_pct=2,tender_inflation_pct=4,construction_inflation_pct=4)
        r=self.calculate(d)['options'][0]
        target=copy.deepcopy(d);target['options'][0]['units'][0]['sale_price']=r['target_gdv']
        self.assertAlmostEqual(self.calculate(target)['options'][0]['return_on_cost_pct'],10,places=4)

    def test_sensitivity_recalculates_sales_dependent_marketing(self):
        r=self.calculate(fixture())['options'][0]
        self.assertEqual(len(r['sensitivity']),9)
        x=next(s for s in r['sensitivity'] if s['cost_change_pct']==0 and s['value_change_pct']==10)
        self.assertEqual(x['gdv'],275000)
        self.assertEqual(x['total'],174860.10)
        y=next(s for s in r['sensitivity'] if s['cost_change_pct']==-10 and s['value_change_pct']==0)
        self.assertEqual(y['total'],157449.09)

    def test_no_viable_option_and_negative_residual_are_not_recommendations(self):
        d=fixture();d['options'][0]['units'][0]['sale_price']=100000
        r=self.calculate(d)
        self.assertIsNone(r['recommended_option']);self.assertEqual(r['viable_count'],0)
        self.assertLess(r['options'][0]['residual_land_value'],0)

    def test_cost_scope_changes_reserve_base_and_keeps_cash_conserved(self):
        d=fixture();d.update(risk_design_pct=10,tender_inflation_pct=10)
        all_in=self.calculate(d)['options'][0]
        d['risk_scope']='works_only';works=self.calculate(d)['options'][0]
        self.assertAlmostEqual(all_in['total'],174110.10*1.21,places=2)
        self.assertEqual(works['total'],206391.30)
        self.assertAlmostEqual(sum(c['equity_cashflow'] for c in all_in['cashflows']),all_in['profit'],delta=.02)
        self.assertGreater(all_in['total'],works['total'])

    def test_embedded_prelims_are_removed_only_with_explicit_inclusion(self):
        d=fixture();d.update(rate_includes_preliminaries=True,embedded_preliminaries_pct=10)
        d['options'][0]['units'][0]['base_rate']=1100
        r=self.calculate(d)['options'][0]
        self.assertEqual(r['total'],174110.10)
        self.assertTrue(any('proxy' in w for w in self.calculate(d)['warnings']))
        d['rate_includes_preliminaries']=False
        with self.assertRaisesRegex(ValueError,'embedded'):self.calculate(d)

    def test_completion_index_cannot_stack_future_inflation(self):
        d=fixture();d.update(price_basis='completion_index',tender_inflation_pct=4)
        with self.assertRaisesRegex(ValueError,'inflation'):self.calculate(d)

    def test_invalid_schedule_duplicate_options_and_unbounded_inputs(self):
        for changes in [{'duration_months':1.5},{'duration_months':0},{'prep_months':2},
                        {'risk_scope':'arbitrary'},{'site_area_m2':True},{'loan_interest_pct':'NaN'},
                        {'rate_includes_ohp':True},{'marketing_pct':100},{'start_date':'2026-02-30'}]:
            d=fixture();d.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.calculate(d)
        d=fixture();d['options']*=2
        with self.assertRaisesRegex(ValueError,'name'):self.calculate(d)
        d=fixture();d['options'][0]['units'][0]['count']=1.25
        with self.assertRaisesRegex(ValueError,'count'):self.calculate(d)

    def test_unknown_fields_and_wrong_text_types_cannot_silently_change_cost(self):
        d=fixture();d['overhead_profit_pct']=d.pop('overheads_profit_pct')
        with self.assertRaisesRegex(ValueError,'overhead_profit_pct'):self.calculate(d)
        for field,value in [('start_date',[]),('source_ref',{'url':'made up'}),('rate_includes_preliminaries',1)]:
            d=fixture();d[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.calculate(d)
        d=fixture();d['options'][0]['units'][0]['sales_price']=250000
        with self.assertRaisesRegex(ValueError,'sales_price'):self.calculate(d)
        d=fixture();d['options'][0]['name']={'title':'Object'}
        with self.assertRaises(ValueError):self.calculate(d)

    def test_recommendation_uses_unrounded_return(self):
        d={'site_area_m2':1,'duration_months':1,'hurdle_pct':10,'options':[]}
        for name,sales in [('Lower return',600000000000),('Higher return',600000001000)]:
            d['options'].append({'name':name,'units':[{'name':'House','count':1,'area_m2':500000,'base_rate':1000000,'sale_price':sales}]})
        r=self.calculate(d)
        self.assertEqual(r['options'][0]['return_on_cost_pct'],r['options'][1]['return_on_cost_pct'])
        self.assertEqual(r['recommended_option'],'Higher return')


if __name__=='__main__':unittest.main()
