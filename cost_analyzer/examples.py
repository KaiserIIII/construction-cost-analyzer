"""Self-authored inputs demonstrating explicit measurement and pricing bases."""
def example():
    return {
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
