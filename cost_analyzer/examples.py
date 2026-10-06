"""Self-authored inputs demonstrating explicit measurement and pricing bases."""
def example():
    return {
        'development':development_example(),
        'early':{'project_name':'Community workspace','currency':'GBP','area_m2':1000,'base_rate':1000,
                 'base_index':100,'target_index':120,'base_location_index':100,'target_location_index':105,
                 'preliminaries_pct':10,'overheads_profit_pct':5,'contingency_pct':0,'fees_pct':0,'vat_pct':0,
                 'rate_includes_preliminaries':False,'rate_includes_ohp':False,'cost_scope':'building',
                 'source_ref':'Self-authored arithmetic example (not market rates)','price_date':'2026-01-01'},
        'takeoff':{'method':'strip_foundation','length':10,'width':8,'wall_thickness':.3,'trench_width':.8,
                   'trench_depth':1.2,'concrete_width':.6,'concrete_depth':.3},
        'rate':{'unit':'m2','currency':'GBP','materials':[
            {'name':'Brick','consumption':60,'pack_price':240,'pack_size':500,'waste_pct':5},
            {'name':'Mortar','consumption':.036,'pack_price':80,'pack_size':1,'waste_pct':0}],
            'crew_hourly_cost':48,'crew_output_per_hour':2,'plant_hourly_cost':0,'plant_output_per_hour':1,
            'subcontract_per_unit':0,'markup_pct':10},
        'boq':{'csv':'item_id,description,element,unit,quantity,rate,currency,source_ref,price_date,included_preliminaries,included_ohp\n'
                    'SUB-01,Strip excavation,Substructure,m3,33.408,18.5,GBP,self-authored,2026-01-01,false,false\n'
                    'SUB-02,Foundation concrete,Substructure,m3,6.264,140,GBP,self-authored,2026-01-01,false,false\n'
                    'SUB-03,Natural backfill,Substructure,m3,27.144,12,GBP,self-authored,2026-01-01,false,false\n'
                    'WALL-01,Brick wall,Walls,m2,100,62.832,GBP,self-authored,2026-01-01,false,true\n',
               'project':{'project_name':'Measured substructure and wall package','currency':'GBP','preliminaries_pct':10,
                          'overheads_profit_pct':0,'contingency_pct':5,'fees_pct':0,'vat_pct':0}},
        'appraise':{'cashflows':[-100000,30000,30000,30000,30000],'discount_rate_pct':8,'currency':'GBP',
                    'gdv':1000000,'non_land_cost':700000,'target_profit_pct':20,'profit_basis':'gdv'}}


def development_example():
    """Original arithmetic inputs, separate from licensed coursework sources."""
    return {'project_name':'Residential alternatives','currency':'GBP','site_area_m2':600,'land_rate':125,
            'site_clearance_rate':1,'facilitating_cost':35000,'external_works_pct':8,
            'preliminaries_pct':10,'overheads_profit_pct':12,'fees_pct':5,'marketing_pct':3,
            'rate_includes_preliminaries':False,'embedded_preliminaries_pct':0,'rate_includes_ohp':False,
            'base_index':100,'target_index':112,'base_location_index':100,'target_location_index':105,
            'price_basis':'estimate_plus_inflation','risk_scope':'all_in','risk_design_pct':1,
            'risk_construction_pct':2,'risk_employer_change_pct':1,'risk_other_pct':1,
            'tender_inflation_pct':2,'construction_inflation_pct':2,'duration_months':5,
            'prep_months':1,'prep_spend_pct':10,'loan_share_pct':50,'loan_interest_pct':8,'loan_fee_pct':2,
            'hurdle_pct':10,'discount_rate_pct':10,'sensitivity_pct':10,'start_date':'2026-10-01',
            'price_date':'2025-01-01','source_ref':'Self-authored arithmetic example, not market rates',
            'index_source_ref':'Self-authored index assumptions, not BCIS or ONS',
            'options':[
                {'name':'Courtyard houses','units':[{'name':'Detached house','count':3,'area_m2':140,'base_rate':1800,'sale_price':450000,'source_ref':'Self-authored','area_source_ref':'Assumed internal floor area'}]},
                {'name':'Garden pairs','units':[{'name':'Semi-detached house','count':5,'area_m2':95,'base_rate':1400,'sale_price':300000,'source_ref':'Self-authored','area_source_ref':'Assumed internal floor area'}]},
                {'name':'Terrace homes','units':[{'name':'Terraced house','count':8,'area_m2':68,'base_rate':1350,'sale_price':220000,'source_ref':'Self-authored','area_source_ref':'Assumed internal floor area'}]}]}
