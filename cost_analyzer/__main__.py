"""Run `python -m cost_analyzer --help` for estimation and report commands."""
import argparse
import json
import sys
from decimal import DecimalException
from pathlib import Path
from .engine import early_estimate, price_boq, appraise
from .benchmarks import benchmark, read_boq_csv, generate_scenarios, scenario_csv
from .examples import example
from .reporting import export_report


def read_json(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict):raise ValueError('Input JSON must be an object')
    return data


def main(argv=None):
    parser=argparse.ArgumentParser(description='Construction cost estimation, measurement and appraisal / 建筑计量计价')
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ('estimate','appraise'):
        p=sub.add_parser(command);p.add_argument('input',type=Path);p.add_argument('--output',type=Path,default=Path('outputs')/command)
    p=sub.add_parser('boq');p.add_argument('--input',type=Path,required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,default=Path('outputs/boq'))
    p=sub.add_parser('benchmark');p.add_argument('--input',type=Path,default=Path(__file__).resolve().parents[1]/'data/synthetic_projects.csv')
    for key in ('currency','building-type','region','cost-scope','source-type'):p.add_argument('--'+key)
    p.add_argument('--target-index',default='100');p.add_argument('--target-location-index',default='100');p.add_argument('--output',type=Path,default=Path('outputs/benchmark'))
    p=sub.add_parser('demo');p.add_argument('--output',type=Path,default=Path('outputs/demo'))
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=8765)
    p=sub.add_parser('generate');p.add_argument('--count',type=int,default=500);p.add_argument('--seed',type=int,default=42);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='serve':
            from .web import create_server
            server=create_server(args.port)
            print(f'Construction Cost Analyzer: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)',flush=True)
            try:server.serve_forever()
            except KeyboardInterrupt:pass
            finally:server.server_close()
            return 0
        if args.command=='generate':
            content=scenario_csv(generate_scenarios(args.count,args.seed))
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(content,encoding='utf-8',newline='\n')
            print(f'Generated {args.count} synthetic scenarios (seed={args.seed}): {args.output}')
            return 0
        if args.command=='demo':
            inputs=example(); reports={'early':early_estimate(inputs['early']),
                'boq':price_boq(read_boq_csv(inputs['boq']['csv']),inputs['boq']['project']),
                'appraisal':appraise(inputs['appraise']),
                'benchmark':benchmark(scenario_csv(generate_scenarios()),{'currency':'GBP','cost_scope':'building'},100,100)}
            result={name:export_report(value,args.output,name) for name,value in reports.items()}
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        if args.command=='estimate':result=early_estimate(read_json(args.input))
        elif args.command=='appraise':result=appraise(read_json(args.input))
        elif args.command=='boq':result=price_boq(read_boq_csv(args.input.read_text(encoding='utf-8-sig')),read_json(args.project))
        else:
            filters={key:getattr(args,key) for key in ('currency','building_type','region','cost_scope','source_type') if getattr(args,key)}
            result=benchmark(args.input.read_text(encoding='utf-8-sig'),filters,args.target_index,args.target_location_index)
        paths=export_report(result,args.output)
        print(json.dumps({'result':result,'files':paths},ensure_ascii=False,indent=2,allow_nan=False));return 0
    except (ValueError,OSError,DecimalException,TypeError) as exc:
        print(f'Error: {exc}',file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
