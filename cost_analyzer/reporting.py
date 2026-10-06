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

LABELS.update(name='方案或户型 / Option or type',gifa_m2='总内部楼面面积 / GIFA m²',
              units_count='住宅数量 / Dwellings',gdv='销售总值 / GDV',profit='利润或亏损 / Profit or loss',
              return_on_cost_pct='总成本回报 % / Return on cost %',meets_hurdle='达到目标 / Meets hurdle',
              loan_repayment='贷款偿还 / Loan repayment',cost_change_pct='非销售成本变化 % / Cost change %',
              value_change_pct='售价变化 % / Value change %',equity_cashflow='权益现金流 / Equity cashflow',
              budget_cashflow='预算现金流 / Budget cashflow',month='月份 / Month',date='日期 / Date',
              loan_draw='贷款提取 / Loan draw',loan_balance='期末贷款余额 / Loan balance',
              interest='利息 / Interest',arrangement_fee='贷款安排费 / Loan arrangement fee',
              sales='销售收入 / Sales',marketing='营销费 / Marketing',land_payment='土地付款 / Land payment',
              works_payment='工程及准备金付款 / Works and reserve payments',
              present_value='预算现金流现值 / Budget present value',spend_fraction='支出比例 / Spending fraction',
              adjusted_rate='调整后单价 / Adjusted rate',area_m2='每户 GIFA m² / GIFA per dwelling',
              cost='金额 / Cost',count='数量 / Count',target_gdv='目标销售总值 / Target GDV',
              building_works='房屋工程 / Housing works',external_works='外部工程 / External works',
              building_estimate='建筑及外部工程 / Building and external works',site_clearance='场地清理 / Site clearance',
              facilitating_works='前期工程 / Facilitating works',contract_subtotal='承包费前小计 / Contract subtotal',
              works_total='工程合计 / Works total',works_and_fees='工程及设计费 / Works and design fees',
              land_cost='土地费用 / Land package',base_cost='风险前开发成本 / Pre-risk development cost',
              risk_design='设计风险 / Design development risk',risk_construction='施工风险 / Construction risk',
              risk_employer_change='业主变更风险 / Employer change risk',risk_other='其他风险 / Other employer risk',
              after_risk='含风险小计 / Subtotal with risk',tender_inflation='招标价格上涨 / Tender inflation',
              after_tender='含招标上涨小计 / Subtotal with tender inflation',construction_inflation='施工价格上涨 / Construction inflation')


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
    if result.get('options'):
        fields=('name','gifa_m2','units_count','total','gdv','profit','return_on_cost_pct','meets_hurdle',
                'target_gdv','residual_land_value','budget_npv','equity_npv','budget_irr_annual_pct','equity_irr_annual_pct')
        row(['section','option_comparison']);row(fields)
        for option in result['options']:row([option.get(key,'') for key in fields])
        for option in result['options']:
            row([]);row(['option',option['name']])
            for section in ('housing','breakdown','cashflows','sensitivity'):
                records=option.get(section,[])
                if records:
                    fields=tuple(records[0]);row(['section',section]);row(fields)
                    for record in records:row([record.get(key,'') for key in fields])
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
        body=''.join('<tr>'+''.join(f'<td>{cell(LABELS.get(row.get(key,""),row.get(key,"")) if key=="label" else row.get(key,""))}</td>' for key in fields)+'</tr>' for row in rows)
        return f'<div class="scroll"><table><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table></div>'
    scalar=[{'metric':LABELS.get(key,key),'value':value} for key,value in result.items() if not isinstance(value,(dict,list))]
    content=table(scalar,['metric','value'])
    if result.get('options'):
        content+='<h2>方案比较 / Option comparison</h2>'+table(result['options'],['name','gifa_m2','units_count','total','gdv','profit','return_on_cost_pct','meets_hurdle','target_gdv','residual_land_value'])
        for option in result['options']:
            content+='<h2>'+cell(option['name'])+'</h2>'
            content+=table([{'metric':LABELS.get(key,key),'value':value} for key,value in option.items() if not isinstance(value,(list,dict))],['metric','value'])
            for section,title in [('housing','户型计价 / Housing mix'),('breakdown','费用基数 / Cost bases'),('cashflows','月度融资与现金流 / Monthly finance and cashflows'),('sensitivity','成本与售价敏感性 / Cost/value sensitivity')]:
                records=option.get(section,[])
                if records:content+='<h3>'+title+'</h3>'+table(records,tuple(records[0]))
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
