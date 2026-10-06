#!/usr/bin/env python3
"""Compatibility entry for the original 18 illustrative CNY records."""
import argparse
import csv
import io
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cost_analyzer.benchmarks import benchmark, scenario_csv
from cost_analyzer.validation import number
from cost_analyzer.reporting import export_report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'data/construction_projects.csv')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/legacy')
    args=parser.parse_args()
    try:
        rows=[]
        for i,row in enumerate(csv.DictReader(io.StringIO(args.input.read_text(encoding='utf-8-sig'))),1):
            rows.append({'project_id':f'LEGACY-{i:02d}','building_type':row['结构类型'],'region':row['地区'],'currency':'CNY',
                         'floor_area_m2':str(number(row['建筑面积_平米'],'floor area',positive=True)),
                         'budget':str(number(row['预算_万元'],'budget',positive=True)*10000),
                         'actual_cost':str(number(row['实际成本_万元'],'actual cost',positive=True)*10000),
                         'base_index':100,'location_index':100,'cost_scope':'original_example_unspecified',
                         'source_type':'illustrative','source_ref':'Original repository CSV (unverified illustrative costs)',
                         'price_date':row['竣工日期']})
        result=benchmark(scenario_csv(rows),{'currency':'CNY','source_type':'illustrative'},100,100)
        result['warnings'].append('Original costs have no verified price-index or cost-scope basis. Indexes stay at 100 (no adjustment); completion date is a proxy label, not a verified rate price date.')
        print(f'Original illustrative records: {result["sample_count"]}; derived over-budget count: {result["over_budget_count"]}')
        export_report(result,args.output)
        return 0
    except (ValueError,OSError,KeyError) as exc:
        print(f'Error: {exc}',file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
