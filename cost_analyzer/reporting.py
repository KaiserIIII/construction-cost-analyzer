"""Portable UTF-8 reports with safe HTML and spreadsheet text."""
import csv
import io
import json
from html import escape
from pathlib import Path

LABELS={
    'direct_cost':'本体 / Direct works','preliminaries':'现场费用 / Preliminaries',
    'overheads_profit':'总部费与利润 / OH&P','contingency':'风险准备 / Contingency',
    'fees':'顾问费 / Fees','vat':'增值税 / VAT','total':'合计 / Total','base':'基数 / Base',
    'percent':'比例 / Percent','amount':'金额 / Amount','item_id':'编号 / Item',
    'description':'项目说明 / Description','element':'分部 / Element','unit':'单位 / Unit',
    'quantity':'净工程量 / Net quantity','rate':'单价 / Rate','source_ref':'来源 / Source',
    'price_date':'价格日期 / Price date','npv':'净现值 / NPV','irr_pct':'内部收益率% / IRR%',
    'payback_period':'回收期 / Payback periods','residual_land_value':'土地余额 / Residual land value'}


def csv_safe(value):
    if value is None:return ''
    if isinstance(value,(float,int)) and not isinstance(value,bool):return value
    result=str(value)
    if result.lstrip().startswith(('=','+','-','@')) or result.startswith(('\t','\r','\n')):
        return "'"+result
    return result


def report_csv(result):
    stream=io.StringIO(newline='')
    writer=csv.writer(stream,lineterminator='\n')
    def row(values):writer.writerow([csv_safe(value) for value in values])
    row(['project_name',result.get('project_name','Construction cost report')])
    row(['currency',result.get('currency','')])
    if result.get('items'):
        fields=('item_id','description','element','unit','quantity','rate','total','currency','source_ref','price_date','included_preliminaries','included_ohp')
        row(fields)
        for item in result['items']:row([item.get(key,'') for key in fields])
        row([])
    if result.get('projects'):
        fields=tuple(result['projects'][0])
        row(fields)
        for item in result['projects']:row([item.get(key,'') for key in fields])
        row([])
    if 'breakdown' in result:
        row(['label','base','percent','amount'])
        for item in result['breakdown']:row([item[key] for key in ('label','base','percent','amount')])
        row(['total','','',result['total']])
    else:
        row(['metric','value'])
        for key,value in result.items():
            if not isinstance(value,(list,dict)):row([key,value])
    for warning in result.get('warnings',[]):row(['note',warning])
    if 'inputs' in result:
        row(['inputs_json',json.dumps(result['inputs'],ensure_ascii=False,allow_nan=False)])
    return stream.getvalue()


def report_html(result):
    def cell(value):return escape(str('—' if value is None else value))
    def table(rows,fields):
        headers=''.join(f'<th>{cell(LABELS.get(key,key))}</th>' for key in fields)
        body=''.join('<tr>'+''.join(f'<td>{cell(row.get(key,""))}</td>' for key in fields)+'</tr>' for row in rows)
        return f'<div class="scroll"><table><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table></div>'
    scalar=[{'metric':LABELS.get(key,key),'value':value} for key,value in result.items() if not isinstance(value,(dict,list))]
    content=table(scalar,['metric','value'])
    if 'items' in result:content+='<h2>工程量清单 / Bill of quantities</h2>'+table(result['items'],['item_id','description','element','unit','quantity','rate','total','source_ref','price_date'])
    if 'breakdown' in result:content+='<h2>费用组成 / Cost build-up</h2>'+table(result['breakdown'],['label','base','percent','amount'])
    if 'projects' in result:content+='<h2>可比样本 / Comparable records</h2>'+table(result['projects'],['project_id','normalized_cost_per_m2','cost_deviation_pct','source_type','source_ref'])
    if 'adjustments' in result:content+='<h2>调整依据 / Adjustment basis</h2>'+table([{'metric':key,'value':value} for key,value in result['adjustments'].items()],['metric','value'])
    if 'element_totals' in result:content+='<h2>分部汇总 / Element totals</h2>'+table([{'element':key,'total':value} for key,value in result['element_totals'].items()],['element','total'])
    if 'discounted_cashflows' in result:content+='<h2>折现现金流 / Discounted cashflows</h2>'+table([{'period':i,'present_value':value} for i,value in enumerate(result['discounted_cashflows'])],['period','present_value'])
    if result.get('warnings'):content+='<h2>使用条件 / Notes</h2><ul>'+''.join('<li>'+cell(value)+'</li>' for value in result['warnings'])+'</ul>'
    if 'inputs' in result:content+='<h2>输入与来源 / Inputs and sources</h2><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+cell(json.dumps(result['inputs'],ensure_ascii=False,indent=2,allow_nan=False))+'</pre>'
    # The source JSON accompanies each rendered report for audit/reconciliation.
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Construction cost report</title><style>body{font:15px/1.6 system-ui,sans-serif;color:#1c3144;background:#f3f6f8;margin:0}main{max-width:1100px;margin:32px auto;padding:32px;background:white;border-top:5px solid #166b65}h1{font-size:26px}h2{font-size:19px;margin-top:32px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px 12px;border-bottom:1px solid #dce5e8}th{background:#eef4f4}td{overflow-wrap:anywhere}footer{margin-top:32px;color:#536672}@media print{body{background:white}main{margin:0;padding:12px}tr{break-inside:avoid}}@media(max-width:600px){main{margin:0;padding:16px}}</style><main><h1>'+cell(result.get('project_name','Construction Cost Analyzer'))+'</h1><p>估价与核对报告 / Estimate and review report · '+cell(result.get('currency',''))+'</p>'+content+'<footer>Construction Cost Analyzer · Decimal calculations, explicit cost bases. JSON retains the calculation results; CSV is available for spreadsheet review.</footer></main></html>'


def export_report(result,directory,name='report'):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if not name.replace('-','').replace('_','').isalnum():
        raise ValueError('Report name: letters, numbers, hyphen or underscore only')
    contents={'json':json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n','csv':report_csv(result),'html':report_html(result)}
    paths={}
    for extension,content in contents.items():
        path=directory/f'{name}.{extension}'
        path.write_text(content,encoding='utf-8-sig' if extension=='csv' else 'utf-8',newline='\n')
        paths[extension]=str(path)
    return paths
