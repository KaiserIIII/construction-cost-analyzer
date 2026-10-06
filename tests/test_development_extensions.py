import copy
import unittest
from cost_analyzer.development import development
from tests.test_development import fixture


class ScenarioExtensionTests(unittest.TestCase):
    def test_overrides_inherit_and_preserve_zero_without_mutating_inputs(self):
        data=fixture();other=copy.deepcopy(data['options'][0]);other['name']='Long programme'
        other['settings']={'duration_months':4,'marketing_pct':0}
        data['options'].append(other);original=copy.deepcopy(data)
        result=development(data);a,b=result['options']
        self.assertEqual(a['total'],174110.10)
        self.assertEqual(b['finance'],4143)
        self.assertEqual(b['total'],167863)
        self.assertEqual(len(b['cashflows']),5)
        self.assertEqual(b['effective_settings']['marketing_pct'],0)
        self.assertEqual(b['effective_settings']['prep_spend_pct'],50)
        self.assertEqual(a['cost_per_m2'],1741.101)
        self.assertEqual(a['cost_per_unit'],174110.10)
        self.assertEqual(data,original);self.assertEqual(result['inputs'],original)

    def test_custom_grids_are_sorted_and_recalculate_marketing(self):
        data=fixture();data.update(cost_changes_pct=[20,0,-20,-10,10],value_changes_pct=[0,10,-10,20,-20])
        result=development(data);rows=result['options'][0]['sensitivity']
        self.assertEqual(len(rows),25)
        self.assertEqual(result['cost_changes_pct'],[-20,-10,0,10,20])
        baseline=next(r for r in rows if r['cost_change_pct']==0 and r['value_change_pct']==0)
        self.assertEqual(baseline['total'],174110.10)
        changed=next(r for r in rows if r['cost_change_pct']==0 and r['value_change_pct']==20)
        self.assertEqual(changed['total'],175610.10)
        data.pop('value_changes_pct');self.assertEqual(len(development(data)['options'][0]['sensitivity']),15)
        data.pop('cost_changes_pct');data['sensitivity_pct']=0
        self.assertEqual(len(development(data)['options'][0]['sensitivity']),1)

    def test_metadata_and_invalid_ranges_and_overrides(self):
        data=fixture();data.update(report_reference='QS-001',revision='P01',estimate_date='2026-10-06',prepared_by='User',client_name='Client')
        self.assertEqual(development(data)['inputs']['report_reference'],'QS-001')
        invalid=[('cost_changes_pct',[]),('cost_changes_pct',[1,2]),('cost_changes_pct',[0,0]),
                 ('cost_changes_pct',[0,True]),('value_changes_pct',[0,101]),('cost_changes_pct','0,10'),
                 ('cost_changes_pct',list(range(8))),('estimate_date','2026-02-30'),('revision',123)]
        for key,value in invalid:
            with self.subTest(key=key,value=value):
                case=copy.deepcopy(data);case[key]=value
                with self.assertRaises(ValueError):development(case)
        for settings in [None,{'unknown':0},{'duration_months':1},{'start_date':123},{'loan_share_pct':101}]:
            case=fixture();case['options'][0]['settings']=settings
            with self.subTest(settings=settings),self.assertRaises(ValueError):development(case)


if __name__=='__main__':unittest.main()
