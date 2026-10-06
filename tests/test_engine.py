import math
import unittest
from cost_analyzer.engine import early_estimate, takeoff, unit_rate, price_boq, appraise


class EarlyEstimateTests(unittest.TestCase):
    def test_index_adjustment_and_explicit_allowance_bases(self):
        result = early_estimate(dict(area_m2=1000, base_rate=1000, base_index=100, target_index=120,
                                     base_location_index=100, target_location_index=105,
                                     preliminaries_pct=10, overheads_profit_pct=5, currency='GBP'))
        self.assertEqual(result['adjusted_rate'], 1260)
        self.assertEqual(result['direct_cost'], 1260000)
        self.assertEqual(result['preliminaries'], 126000)
        self.assertEqual(result['overheads_profit'], 69300)
        self.assertEqual(result['total'], 1455300)

    def test_zero_index_and_nonfinite_and_boolean_inputs_rejected(self):
        for key, value in [('base_index', 0), ('area_m2', -1), ('base_rate', float('nan')),
                           ('area_m2', True), ('target_index', float('inf')), ('fees_pct', -1)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                early_estimate(dict(area_m2=100, base_rate=100, **{key: value}) if key not in ['area_m2','base_rate'] else {'area_m2':100,'base_rate':100,key:value})

    def test_reject_double_counted_preliminaries_and_ohp(self):
        for flag, percentage in [('rate_includes_preliminaries','preliminaries_pct'),('rate_includes_ohp','overheads_profit_pct')]:
            with self.assertRaises(ValueError):
                early_estimate({'area_m2':100,'base_rate':100,flag:True,percentage:10})

    def test_allowances_reconcile_with_vat_and_fees(self):
        r = early_estimate({'area_m2':10,'base_rate':100,'contingency_pct':10,'fees_pct':5,'vat_pct':20})
        self.assertEqual(r['total'], 1386)
        self.assertEqual(sum(row['amount'] for row in r['breakdown']),r['total'])


class MeasurementTests(unittest.TestCase):
    def test_net_measurement_and_material_waste_are_separate(self):
        self.assertEqual(takeoff({'method':'rectangle','length':10,'width':3,'count':2,'deduction':4})['quantity'],56)
        self.assertEqual(takeoff({'method':'volume','length':10,'width':0.6,'height':0.3})['quantity'],1.8)

    def test_external_dimensions_to_centreline_and_natural_backfill(self):
        r = takeoff({'method':'strip_foundation','length':10,'width':8,'wall_thickness':0.3,
                     'trench_width':0.8,'trench_depth':1.2,'concrete_width':0.6,'concrete_depth':0.3})
        self.assertEqual(r['centreline_m'],34.8)
        self.assertEqual(r['excavation_m3'],33.408)
        self.assertEqual(r['concrete_m3'],6.264)
        self.assertEqual(r['backfill_m3'],27.144)

    def test_invalid_geometry_deductions_and_fractional_count(self):
        for data in [dict(method='rectangle',length=1,width=1,deduction=2),
                     dict(method='centreline',length=1,width=1,wall_thickness=2),
                     dict(method='count',count=1.5),dict(method='circle',length=2),
                     dict(method='volume',length=1,width=1,height=0)]:
            with self.subTest(data=data),self.assertRaises(ValueError):
                takeoff(data)


class UnitRateTests(unittest.TestCase):
    def test_pack_conversion_waste_and_crew_productivity(self):
        r=unit_rate({'unit':'m2','currency':'GBP','materials':[
            {'name':'Brick','consumption':60,'pack_price':240,'pack_size':500,'waste_pct':5},
            {'name':'Mortar','consumption':0.036,'pack_price':80,'pack_size':1,'waste_pct':0}],
            'crew_hourly_cost':48,'crew_output_per_hour':2,'markup_pct':10})
        self.assertEqual(r['material'],33.12)
        self.assertEqual(r['labour'],24)
        self.assertEqual(r['direct_rate'],57.12)
        self.assertEqual(r['quoted_rate'],62.832)

    def test_zero_output_rejected_when_resource_cost_exists(self):
        for data in [{'crew_hourly_cost':1,'crew_output_per_hour':0},
                     {'plant_hourly_cost':10,'plant_output_per_hour':0},
                     {'materials':[{'consumption':1,'pack_price':1,'pack_size':0}]}]:
            with self.assertRaises(ValueError):
                unit_rate(data)


class BoqTests(unittest.TestCase):
    def test_half_up_round_each_line_then_sum_and_percentages(self):
        rows=[dict(item_id=str(i),description='work',element='Structure',unit='m2',quantity=1,rate='1.005',currency='GBP') for i in range(2)]
        r=price_boq(rows,{'currency':'GBP','preliminaries_pct':10})
        self.assertEqual(r['direct_cost'],2.02)
        self.assertEqual(r['total'],2.22)

    def test_mixed_currency_duplicate_ids_negative_quantity_rejected(self):
        row=dict(item_id='A',description='work',element='Structure',unit='m2',quantity=1,rate=1,currency='GBP')
        for rows in [[row,{**row,'currency':'CNY','item_id':'B'}],[row,row],[{**row,'quantity':-1}],[]]:
            with self.assertRaises(ValueError):
                price_boq(rows,{'currency':'GBP'})

    def test_included_oncost_cannot_be_reapplied(self):
        with self.assertRaises(ValueError):
            price_boq([dict(item_id='A',description='work',element='S',unit='m2',quantity=1,rate=10,currency='GBP',included_ohp=True)],{'currency':'GBP','overheads_profit_pct':5})


class AppraisalTests(unittest.TestCase):
    def test_conventional_irr_equal_to_search_boundary_is_reported(self):
        for receipt,irr in [(200,100),(300,200),(500,400),(900,800)]:
            with self.subTest(receipt=receipt):
                self.assertEqual(appraise({'cashflows':[-100,receipt]})['irr_pct'],irr)
    def test_signed_npv_and_conventional_irr(self):
        r=appraise({'cashflows':[-100000,30000,30000,30000,30000],'discount_rate_pct':8})
        self.assertEqual(r['npv'],-636.19)
        self.assertAlmostEqual(r['irr_pct'],7.71385,places=4)
        self.assertAlmostEqual(r['payback_period'],10/3,places=5)
        self.assertIsNone(r['discounted_payback_period'])

    def test_unconventional_irr_not_reported_as_unique_and_margin_basis(self):
        r=appraise({'cashflows':[-100,230,-132],'discount_rate_pct':10,'gdv':1000000,'non_land_cost':700000,'target_profit_pct':20,'profit_basis':'gdv'})
        self.assertIsNone(r['irr_pct'])
        self.assertTrue(r['warnings'])
        self.assertEqual(r['residual_land_value'],100000)
        cost=appraise({'cashflows':[-100,110],'gdv':1000000,'non_land_cost':700000,'target_profit_pct':20,'profit_basis':'cost'})
        self.assertEqual(cost['residual_land_value'],133333.33)

    def test_invalid_cashflow_and_discount(self):
        for data in [{'cashflows':[]},{'cashflows':[-1,math.inf]}, {'cashflows':[-1,2],'discount_rate_pct':-100},
                     {'cashflows':[-1,2],'profit_basis':'whatever'}]:
            with self.assertRaises(ValueError):
                appraise(data)


if __name__=='__main__':
    unittest.main()
