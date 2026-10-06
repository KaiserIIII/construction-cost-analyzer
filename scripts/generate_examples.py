"""Regenerate original examples, a schema template and the seeded demo data."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cost_analyzer.benchmarks import generate_scenarios, scenario_csv, PROJECT_FIELDS
from cost_analyzer.examples import example


def main():
    directory=ROOT/'examples';directory.mkdir(exist_ok=True)
    inputs=example()
    for name,key in [('early-estimate','early'),('unit-rate','rate'),('strip-foundation','takeoff'),('appraisal','appraise'),('development','development')]:
        (directory/f'{name}.json').write_text(json.dumps(inputs[key],ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    (directory/'boq.csv').write_text(inputs['boq']['csv'],encoding='utf-8',newline='\n')
    (directory/'project.json').write_text(json.dumps(inputs['boq']['project'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    (directory/'project-history-template.csv').write_text(','.join(PROJECT_FIELDS+('index_type','index_series','index_base_year'))+'\n',encoding='utf-8',newline='\n')
    content=scenario_csv(generate_scenarios(500,42)).encode('utf-8')
    data=ROOT/'data/synthetic_projects.csv';data.write_bytes(content)
    metadata={'schema_version':1,'source_type':'synthetic','source_ref':'scenario-generator-v1-seed-42','sample_count':500,'seed':42,
              'generator':'cost_analyzer.benchmarks.generate_scenarios','currency':'GBP','cost_scope':'building','sha256':hashlib.sha256(content).hexdigest(),
              'building_functions':['housing','office','school','warehouse','healthcare'],'region_levels':['reference','metro','regional','remote'],
              'assumptions':{'illustrative_base_rates':{'housing':1400,'office':2000,'school':1800,'warehouse':1000,'healthcare':2600},
                             'floor_area_range_m2':[200,25000],'arbitrary_price_index_range':[90,145],'specification_multiplier_range':[0.85,1.15],
                             'actual_budget_multiplier_range':[0.88,1.24]},
              'licence':'MIT (self-authored generated examples)','limitations':['Not calibrated to actual projects','No empirical market or causal inference','Dates and indexes are arbitrary scenario labels, not official market observations']}
    (ROOT/'data/synthetic_projects.metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Generated 500 labeled scenarios and 8 example/template files.')


if __name__=='__main__':main()
