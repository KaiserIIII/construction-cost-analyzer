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


from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import math
from .workbook import Cell, Formula, Sheet, clean_text, column, deterministic_zip, workbook_bytes

SCHEMA_VERSION='1.0'
LONG_FIELDS=('section','row_id','option_id','field','value','unit','currency','source_ref')
LABELS.update({
    'report_reference':'报告编号 / Report reference','revision':'版本 / Revision',
    'estimate_date':'估价日期 / Estimate date','prepared_by':'编制人 / Prepared by',
    'client_name':'客户 / Client name','label':'费用项目 / Cost item',
    'metric':'指标 / Metric','value':'数值 / Value','field':'原始字段 / Field',
    'option_id':'方案编号 / Option ID','row_id':'行编号 / Row ID','currency':'币种 / Currency',
    'section':'明细分类 / Section','project_name':'项目名称 / Project name','type':'工具 / Tool',
    'option_count':'方案数 / Option count','viable_count':'达到目标方案数 / Viable count',
    'recommended_option':'推荐方案 / Recommended option','price_basis':'价格基准 / Price basis',
    'risk_scope':'风险范围 / Risk scope','rounding_policy':'舍入方式 / Rounding policy',
    'source_ref':'价格或数据来源 / Source reference','area_source_ref':'面积来源 / Area source reference',
    'base_rate':'基础单价 / Base rate','sale_price':'每户售价 / Sale price',
    'cost_per_m2':'每平方米成本 / Cost per m²','cost_per_unit':'单位成本 / Cost per unit',
    'profit_on_gdv_pct':'销售值利润率 / Profit on GDV','finance':'融资成本 / Finance cost',
    'loan_principal':'贷款承诺额 / Loan principal','breakeven_gdv':'盈亏平衡销售值 / Breakeven GDV',
    'affordable_cost':'可承受成本 / Affordable cost','budget_npv':'预算净现值 / Budget NPV',
    'equity_npv':'权益净现值 / Equity NPV','budget_irr_annual_pct':'预算年化内部收益率 / Budget annual IRR',
    'equity_irr_annual_pct':'权益年化内部收益率 / Equity annual IRR',
    'site_area_m2':'场地面积 / Site area','land_rate':'土地每平方米单价 / Land rate per m²',
    'site_clearance_rate':'清理每平方米单价 / Site clearance rate per m²','facilitating_cost':'前期工程费 / Facilitating cost',
    'duration_months':'工期月份 / Duration months','prep_months':'准备期月份 / Preparation months',
    'start_date':'开始日期 / Start date','base_index':'基期指数 / Base index','target_index':'目标指数 / Target index',
    'base_location_index':'基期地区指数 / Base location index','target_location_index':'目标地区指数 / Target location index',
    'index_source_ref':'指数来源 / Index source reference','assumptions':'假设说明 / Assumptions',
    'rate_includes_preliminaries':'单价含现场费 / Rate includes preliminaries',
    'rate_includes_ohp':'单价含总部费与利润 / Rate includes OH&P',
    'cost_changes_pct':'成本变化网格 / Cost changes grid','value_changes_pct':'售价变化网格 / Value changes grid',
    'check':'核对项目 / Check','difference':'差额 / Difference','tolerance':'容许差额 / Tolerance',
    'basis':'核对依据 / Basis','warning':'使用条件 / Note','path':'输入路径 / Input path',
})
for _key,_zh,_en in [
    ('external_works_pct','外部工程比例','External works'),('preliminaries_pct','现场费比例','Preliminaries'),
    ('overheads_profit_pct','总部费与利润比例','OH&P'),('fees_pct','设计费比例','Fees'),
    ('embedded_preliminaries_pct','已含现场费比例','Embedded preliminaries'),('marketing_pct','营销费比例','Marketing'),
    ('risk_design_pct','设计风险比例','Design risk'),('risk_construction_pct','施工风险比例','Construction risk'),
    ('risk_employer_change_pct','业主变更风险比例','Employer change risk'),('risk_other_pct','其他风险比例','Other risk'),
    ('tender_inflation_pct','招标上涨比例','Tender inflation'),('construction_inflation_pct','施工上涨比例','Construction inflation'),
    ('loan_share_pct','贷款比例','Loan share'),('loan_interest_pct','贷款年利率','Loan annual interest'),
    ('loan_fee_pct','贷款安排费比例','Loan fee'),('hurdle_pct','目标回报比例','Hurdle'),
    ('discount_rate_pct','折现年利率','Discount rate'),('sensitivity_pct','敏感性范围','Sensitivity range'),
    ('prep_spend_pct','准备期支出比例','Preparation spend')]:LABELS[_key]=f'{_zh} / {_en}'

TITLES={
    'summary':'项目概况 / Project summary','option_comparison':'方案比较 / Option comparison',
    'housing':'户型计价与来源 / Housing and sources','breakdown':'费用组成与基数 / Cost plan and bases',
    'cashflows':'月度现金流 / Monthly cashflow','sensitivity':'成本与售价敏感性 / Cost/value sensitivity',
    'inputs':'原始输入与来源 / Source inputs and references','effective_settings':'实际采用设置 / Adopted settings',
    'option_settings':'方案采用设置 / Option adopted settings','warnings':'使用条件 / Conditions',
    'items':'工程量清单 / Bill of quantities','projects':'可比样本 / Comparable records',
    'adjustments':'调整依据 / Adjustment basis','element_totals':'分部汇总 / Element totals',
    'discounted_cashflows':'折现现金流 / Discounted cashflows','materials':'材料成本 / Material costs',
    'sources':'资料来源 / Source references','checks':'结果核对 / Reconciliation checks',
}
SNAPSHOT='计算结果快照。修改假设后须在应用内重新计算并重新导出。核对公式仅用于检查。 / Calculation snapshot. Recalculate in the app and export again after changing assumptions. Check formulas are for review only.'
METHOD='内部使用 Decimal；金额展示两位小数，数量与单价最多六位。采用项目输入的费用顺序与基数。 / Decimal calculation; money displayed to 2 decimals, quantities/rates up to 6. Uses adopted project cost sequence and bases.'


def language_check(language):
    if language not in ('zh','en','bilingual'):raise ValueError('language: zh, en or bilingual')


def translated(value,language):
    if language=='bilingual' or ' / ' not in value:return value
    zh,en=value.split(' / ',1)
    return zh if language=='zh' else en


def label(key,language):
    return translated(LABELS.get(key,TITLES.get(key,key)),language)


def json_text(value,pretty=False):
    return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2 if pretty else None)


def csv_safe(value):
    if value is None:return ''
    if isinstance(value,(float,int,Decimal)) and not isinstance(value,bool):return value
    result=str(value)
    if result.lstrip().startswith(('=','+','-','@')) or result.startswith(('\t','\r','\n')):return "'"+result
    return result


MONEY_FIELDS={'total','cost','amount','base','gdv','profit','target_gdv','residual_land_value','building_works',
 'preliminaries','overheads_profit','contingency','fees','vat','budget','actual_cost',
 'loan_repayment','equity_cashflow','budget_cashflow','loan_draw','loan_balance','interest','arrangement_fee',
 'sales','marketing','land_payment','works_payment','present_value','land_cost','works_and_fees','finance',
 'loan_principal','breakeven_gdv','affordable_cost','budget_npv','equity_npv','npv','material','labour','plant',
 'subcontract','facilitating_cost','normalized_cost','cost_deviation','nominal_cost'}
RATE_FIELDS={'rate','base_rate','adjusted_rate','direct_rate','quoted_rate','cost_per_unit','cost_per_m2',
 'cost_per_dwelling','normalized_cost_per_m2','land_rate','site_clearance_rate','cost_per_m2_mean','cost_per_m2_median',
 'cost_per_unit','pack_price','crew_hourly_cost','plant_hourly_cost','subcontract_per_unit','cost_per_unit'}


def field_unit(key,row=None):
    raw_key=key
    key=key.rsplit('.',1)[-1].split('[',1)[0]
    if key=='value' and (row or {}).get('unit'):return row['unit']
    if key=='base' and (row or {}).get('label')=='land_cost':return 'm2'
    if key in ('adjusted_rate','base_rate','land_rate','site_clearance_rate') or 'cost_per_m2' in key:return 'money/m2'
    if key=='cost_per_dwelling' or (key=='cost_per_unit' and ((row or {}).get('option_id') or 'units_count' in (row or {}))):return 'money/dwelling'
    if key.endswith('_pct') or key=='percent':return 'percent'
    if key.endswith('_fraction') or key=='spend_fraction':return 'fraction'
    if key.endswith('_m2') or key=='area_m2':return 'm2'
    if key.endswith('_m3'):return 'm3'
    if key.endswith('_m'):return 'm'
    if key in ('length','width','height','wall_thickness','trench_width','trench_depth','concrete_width','concrete_depth'):return 'm'
    if key=='other_displaced_volume':return 'm3'
    if key in ('pack_size','quality_factor','crew_output_per_hour','plant_output_per_hour'):return 'number'
    if key=='cashflows':return 'money'
    if key in ('cost_per_m2','normalized_cost_per_m2','land_rate','site_clearance_rate','cost_per_m2_mean','cost_per_m2_median'):return 'money/m2'
    if key in RATE_FIELDS:return 'money/'+str((row or {}).get('unit','unit'))
    if key=='sale_price':return 'money/dwelling'
    if key in MONEY_FIELDS or key.endswith('_cost'):return 'money'
    if key.endswith('_date') or key=='date':return 'date'
    if key in ('count','units_count','option_count','viable_count','period'):return 'count'
    if key in ('duration_months','prep_months','month'):return 'month'
    if key.endswith('index'):return 'index'
    if key in ('quantity','gross_quantity','deduction','consumption','purchased_consumption'):return str((row or {}).get('unit','quantity'))
    if key in ('meets_hurdle','rate_includes_preliminaries','rate_includes_ohp','included_preliminaries','included_ohp'):return 'boolean'
    value=(row or {}).get(raw_key,(row or {}).get(key,(row or {}).get('value')))
    if isinstance(value,bool):return 'boolean'
    return 'text' if not isinstance(value,(float,int,Decimal)) else 'number'


def typed_source_value(value,unit):
    """Type validated numeric source strings without changing the input snapshot."""
    if not isinstance(value,str):return value
    if unit=='boolean' and value.strip().lower() in ('true','false'):
        return value.strip().lower()=='true'
    numeric=unit.startswith('money') or unit in ('percent','fraction','m2','m3','m','month','count','index','number','quantity','nr','item','kg','t')
    if numeric:
        try:
            number=Decimal(value.strip())
            if number.is_finite():return number
        except InvalidOperation:pass
    return value


def flattened(value,path=''):
    if isinstance(value,dict):
        for key,item in value.items():yield from flattened(item,f'{path}.{key}' if path else str(key))
    elif isinstance(value,list):
        if not value:yield path,'[]'
        for i,item in enumerate(value):yield from flattened(item,f'{path}[{i}]')
    else:yield path,value


def scalar_record(data):return {k:v for k,v in data.items() if not isinstance(v,(dict,list))}


def adopted_metadata(result):
    """Read only supplied identity fields; never invent dates or preparers."""
    inputs=result.get('inputs',{})
    inputs=inputs if isinstance(inputs,dict) else {}
    project=inputs.get('project',{})
    project=project if isinstance(project,dict) else {}
    metadata=result.get('metadata',{})
    metadata=metadata if isinstance(metadata,dict) else {}
    fields=('report_reference','revision','estimate_date','prepared_by','client_name','price_date','start_date','price_basis','risk_scope')
    adopted={}
    for key in fields:
        for source in (result,metadata,inputs,project):
            value=source.get(key)
            if value is not None and str(value).strip():
                adopted[key]=value;break
    return adopted


def report_tables(result):
    """Canonical record tables. IDs follow source order, independent of names."""
    if not isinstance(result,dict):raise ValueError('result: use an object')
    tables={};currency=result.get('currency','')
    def add(section,record,oid='',rid=None):
        records=tables.setdefault(section,[])
        rid=rid or f'{oid+"." if oid else ""}{section}.{len(records)+1:04d}'
        records.append({'row_id':rid,'option_id':oid,**record})
    add('summary',scalar_record(result),rid='summary')
    for key,value in result.items():
        if key in ('options','inputs','warnings') or not isinstance(value,(dict,list)):continue
        if isinstance(value,dict):add(key,dict(flattened(value)))
        elif value and all(isinstance(v,dict) for v in value):
            for record in value:
                record=dict(flattened(record))
                if key=='materials' and 'unit' in result:record.setdefault('unit',result['unit'])
                add(key,record)
        else:
            for i,item in enumerate(value):add(key,{'period':i,'value':item,'unit':'money' if key=='discounted_cashflows' else field_unit(key)},rid=f'{key}.{i+1:04d}')
    for i,option in enumerate(result.get('options',[]),1):
        oid=f'O{i:03d}';add('option_comparison',scalar_record(option),oid,oid)
        for section,value in option.items():
            if not isinstance(value,(dict,list)):continue
            if section=='effective_settings':add('option_settings',dict(flattened(value)),oid)
            elif isinstance(value,dict):add(section,dict(flattened(value)),oid)
            else:
                for n,item in enumerate(value,1):add(section,dict(flattened(item)) if isinstance(item,dict) else {'value':item},oid,f'{oid}.{section}.{n:04d}')
    if 'inputs' in result:
        for n,(key,value) in enumerate(flattened(result['inputs']),1):add('inputs',{'field':key,'value':value,'unit':field_unit(key,{'value':value})},rid=f'input.{n:04d}')
        add('inputs_json',{'inputs_json':json_text(result['inputs'])},rid='inputs_json')
    for n,warning in enumerate(result.get('warnings',[]),1):add('warnings',{'warning':warning},rid=f'warning.{n:04d}')
    for n,(key,value) in enumerate(flattened(result.get('inputs',{})),1):
        if key.endswith('source_ref'):add('sources',{'path':key,'source_ref':value},rid=f'source.{n:04d}')
    return tables


def long_records(result,tables=None):
    for section,records in (tables or report_tables(result)).items():
        for row in records:
            for field,value in row.items():
                if field in ('row_id','option_id'):continue
                unit=field_unit(field,row)
                if field=='value' and 'unit' in row:unit=row['unit']
                yield {'section':section,'row_id':row['row_id'],'option_id':row['option_id'],'field':field,
                       'value':value,'unit':unit,'currency':result.get('currency',''),'source_ref':row.get('source_ref','')}


def csv_records(records,fields):
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerow(fields)
    for record in records:writer.writerow([csv_safe(record.get(field,'')) for field in fields])
    return stream.getvalue()


def report_csv(result):return csv_records(long_records(result),LONG_FIELDS)


def standard_warning(warning,language):
    # Engine-generated bilingual notes contain a Chinese and English counterpart.
    if any('\u4e00'<=c<='\u9fff' for c in warning) and ' / ' in warning:return translated(warning,language)
    zh={
      'The base includes stated on-costs; zero additional allowance does not strip embedded costs.':'基数已含所述附加费用；额外比例为零不会移除已含费用。',
      'Record the rate source and price date before using the estimate for a project.':'用于项目估价前须记录单价来源及价格日期。',
      'Rectangular continuous strip only. Junctions, working space, earthwork support, bulking and disposal are separate measured items.':'仅适用于矩形连续条形基础；交接、工作空间、土方支护、松胀与外运须单独计量。',
      'Index basis not fully recorded. Confirm one shared index series/base year and consistent location-index basis before applying this comparison.':'指数基准记录不全；比较前须确认统一的指数系列、基年及地区指数基准。',
      'Illustrative/synthetic records demonstrate the workflow; they are not empirical market estimates or evidence of causal cost drivers.':'示例与合成记录仅展示工作流程，不是市场估价或成本因果证据。',
      'Fewer than 10 comparable records; interpret the descriptive range cautiously.':'可比记录少于十个；应审慎解释描述性范围。',
      'Multiple building functions may be pooled; select a building type for project benchmarking.':'可能合并了不同建筑用途；项目比较时请选择建筑类型。',
      'Location indexes normalize supplied prices; they do not remove specification, procurement or scope differences.':'地区指数用于统一给定价格，不能消除规格、采购及范围差异。',
      'Use total crew output, not individual output. Check whether subcontract and plant quotes already include labour or other costs.':'采用整组工人的产能；检查分包及机械报价是否已含人工或其他费用。',
      'Net geometric quantities. Apply the project measurement rules to descriptions and deductions.':'净几何工程量；项目说明与扣减须采用项目计量规则。',
      'IRR outside the supported search range.':'内部收益率超出支持的搜索范围。',
      'IRR is unavailable: require an initial outflow followed only by nonnegative flows for a unique conventional result.':'内部收益率不可用：需初始负现金流及随后非负现金流，才能取得唯一常规结果。',
    }
    import re
    match=re.fullmatch(r'(\d+) item\(s\) lack a complete rate source and price date\.',warning)
    chinese=f'{match.group(1)} 个项目缺少完整的单价来源及价格日期。' if match else zh.get(warning)
    if not chinese:return warning
    return chinese if language=='zh' else chinese+' / '+warning if language=='bilingual' else warning


def report_html(result,language='bilingual'):
    language_check(language);tables=report_tables(result)
    def cell(value):return escape(clean_text('—' if value is None else value))
    def display(value,key,row):
        value=source_preview(value,key,row,language)
        if key=='label':return label(str(value),language)
        if key=='warning':return standard_warning(str(value),language)
        value=typed_source_value(value,field_unit(key,row))
        if isinstance(value,bool):return translated('是 / Yes',language) if value else translated('否 / No',language)
        if isinstance(value,(float,int,Decimal)) and not isinstance(value,bool):
            u=field_unit(key,row);digits=2 if u.startswith('money') else 6
            if u.startswith('money/') or u in ('percent','fraction'):digits=6
            txt=f'{value:,.{digits}f}'
            if digits==6:txt=txt.rstrip('0').rstrip('.')
            return txt+('%' if u=='percent' else '')
        return value
    def table(records,fields=None):
        fields=fields or list(dict.fromkeys(k for row in records for k in row))
        head=''.join(f'<th>{cell(label(key,language))}</th>' for key in fields)
        body=''.join('<tr>'+''.join(f'<td>{cell(display(row.get(key,""),key,row))}</td>' for key in fields)+'</tr>' for row in records)
        return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    def metric_table(record):
        return table([{'field':label(k,language),'value':display(v,k,record),'unit':field_unit(k,record)} for k,v in record.items() if k not in ('row_id','option_id')],['field','value','unit'])
    metadata=adopted_metadata(result)
    content=metric_table(metadata) if metadata else ''
    content+='<p class="notice">'+cell(translated(SNAPSHOT,language))+'</p>'
    content+='<h2>'+cell(label('summary',language))+'</h2>'+metric_table(tables['summary'][0])
    if tables.get('option_comparison'):
        content+='<h2>'+cell(label('option_comparison',language))+'</h2>'+table(tables['option_comparison'],['option_id','name','gifa_m2','units_count','total','gdv','profit','return_on_cost_pct','meets_hurdle'])
        content+='<p>'+cell(translated('面积单位 m²；金额按项目币种；回报率单位 %。 / Areas in m²; amounts in project currency; returns in %.',language))+'</p>'
    for i,option in enumerate(result.get('options',[]),1):
        oid=f'O{i:03d}';content+=f'<h2>{i}. {oid} — {cell(option.get("name",""))}</h2>'+metric_table(scalar_record(option))
        for section in ('option_settings','housing','breakdown','cashflows','sensitivity'):
            records=[r for r in tables.get(section,[]) if r['option_id']==oid]
            if not records:continue
            content+='<h3>'+cell(label(section,language))+'</h3>'
            if section=='option_settings':content+=''.join(metric_table(r) for r in records)
            elif section=='cashflows':
                content+=table(records,['row_id','date','spend_fraction','land_payment','works_payment','sales','marketing','budget_cashflow','present_value'])
                content+=table(records,['row_id','date','loan_draw','loan_balance','interest','arrangement_fee','loan_repayment','equity_cashflow'])
            elif section=='housing':
                content+=table(records,['row_id','name','count','area_m2','gifa_m2','adjusted_rate','cost','gdv'])
                content+=table(records,['row_id','source_ref','area_source_ref'])
            else:content+=table(records)
    for section,records in tables.items():
        if section in ('summary','option_comparison','inputs_json','option_settings') or any(r['option_id'] for r in records):continue
        content+='<h2>'+cell(label(section,language))+'</h2>'
        if section in ('effective_settings','adjustments'):content+=''.join(metric_table(r) for r in records)
        elif section=='inputs':
            content+=table([{'field':r['field'],'value':r['value'],'unit':r['unit']} for r in records],['field','value','unit'])
        else:content+=table(records)
    return '<!doctype html><html lang="'+('en' if language=='en' else 'zh-CN')+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+cell(result.get('project_name','Construction cost report'))+'</title><style>body{font:14px/1.5 Arial,sans-serif;color:#243746;margin:0;background:#f2f5f7}main{max-width:1200px;margin:24px auto;padding:28px;background:white}h1{font-size:26px}h2{font-size:19px;margin-top:28px}h3{font-size:16px}.notice{border-left:3px solid #526572;padding:12px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;vertical-align:top;padding:7px;border-bottom:1px solid #dce4e8;overflow-wrap:anywhere}th{background:#edf1f4}footer{margin-top:24px;color:#526572}@page{size:A4 landscape;margin:12mm}@media print{body{background:white}main{margin:0;padding:0;max-width:none}table{table-layout:fixed;font-size:9px}.scroll{overflow:visible}thead{display:table-header-group}tr{break-inside:avoid}h2,h3{break-after:avoid}}@media(max-width:600px){main{margin:0;padding:12px}}</style></head><body><main><h1>'+cell(result.get('project_name',translated('工程成本报告 / Construction cost report',language)))+'</h1><p>'+cell(result.get('currency',''))+'</p>'+content+'<footer>'+cell(translated(METHOD,language))+'</footer></main></body></html>'


def excel_value(value,key,row):
    if key=='value' and row.get('field'):key=row['field']
    unit=field_unit(key,row)
    value=typed_source_value(value,unit)
    if isinstance(value,(int,float,Decimal)) and not isinstance(value,bool):
        if not math.isfinite(value):raise ValueError('Report numeric values must be finite')
        if unit=='percent':return Cell(Decimal(str(value))/100,4)
        if unit=='fraction':return Cell(value,4)
        if unit.startswith('money'):return Cell(value,3 if unit=='money' else 2)
        return Cell(value,2)
    if unit=='date' and value:
        try:return Cell(date.fromisoformat(str(value)),5)
        except ValueError:pass
    return Cell(value)


def source_preview(value,key,row,language):
    """Keep full source snapshots in JSON/CSV; use readable spreadsheet cells."""
    if isinstance(value,str) and (key=='csv' or (key=='value' and row.get('field')=='csv')):
        rows=max(0,len(value.splitlines())-1)
        return translated(f'{rows} 行源数据；完整 CSV 见 inputs.json 的 csv 字段。 / {rows} source rows; full CSV in inputs.json, csv field.',language)
    if isinstance(value,str) and len(value)>32767:
        return translated(f'{len(value)} 个字符；完整文本见 result.json 对应字段。 / {len(value)} characters; full text in the corresponding result.json field.',language)
    return value


def report_xlsx(result,language='bilingual'):
    language_check(language);tables=report_tables(result);sheets=[];refs={}
    snapshot=translated(SNAPSHOT,language)
    def schedule(name,records,fields=None):
        fields=fields or list(dict.fromkeys(k for row in records for k in row))
        headers=[label(k,language)+'\n'+k for k in fields]
        rows=[[],[Cell(name,6)],[Cell(snapshot,7)],headers]
        for record in records:
            row=[]
            for j,key in enumerate(fields,1):
                value=record.get(key)
                value=source_preview(value,key,record,language)
                if key=='label' and value is not None:value=label(str(value),language)
                if key=='warning' and value is not None:value=standard_warning(str(value),language)
                row.append(excel_value(value,key,record))
                refs[(record.get('row_id'),key)]=(name,f'{column(j)}{len(rows)+1}',record.get(key))
            rows.append(row)
        sheet=Sheet(name,rows,filter_end=len(rows));sheets.append(sheet);return sheet
    options=tables.get('option_comparison',[])
    if options:
        summary_fields=['option_id','name','gifa_m2','units_count','total','gdv','profit','return_on_cost_pct','meets_hurdle','target_gdv','residual_land_value']
        summary_fields += [k for k in ('cost_per_m2','cost_per_unit') if any(k in r for r in options)]
        summary=schedule('Summary',options,summary_fields)
        metric_records=[{'option_id':'','field':key,'value':value,'unit':field_unit(key,{key:value})} for key,value in adopted_metadata(result).items()]
        for record in [*tables['summary'],*options]:
            for key,value in record.items():
                if (record in options and key in summary_fields) or key in ('row_id','option_id'):continue
                metric_records.append({'option_id':record.get('option_id',''),'field':key,'value':value,'unit':field_unit(key,record)})
        summary.rows.extend([[],[Cell(label('summary',language),6)],['option_id','field','value','unit']]);summary.headers.append(len(summary.rows))
        for r in metric_records:
            val=excel_value(r['value'],r['field'],r)
            summary.rows.append([r['option_id'],label(r['field'],language),val,r['unit']])
            if r['option_id']:refs[(r['option_id'],r['field'])]=('Summary',f'C{len(summary.rows)}',r['value'])
        for section,name in [('breakdown','Cost plan'),('housing','Housing'),('cashflows','Cashflow'),('sensitivity','Sensitivity')]:
            schedule(name,tables.get(section,[]))
    else:
        rows=[{'row_id':f'summary.{key}','option_id':'','field':key,'value':value,'unit':field_unit(key,tables['summary'][0]),'currency':result.get('currency','')} for key,value in {**adopted_metadata(result),**tables['summary'][0]}.items() if key not in ('row_id','option_id')]
        schedule('Summary',rows)
        for section,name in [('items','BOQ'),('breakdown','Cost plan'),('materials','Resources'),('projects','Benchmarks'),('adjustments','Adjustments'),('element_totals','Elements'),('discounted_cashflows','Appraisal')]:
            if tables.get(section):schedule(name,tables[section])
    input_records=[]
    for section in ('effective_settings','option_settings'):
        for r in tables.get(section,[]):
            for key,value in r.items():
                if key not in ('row_id','option_id'):input_records.append({'row_id':f'{r["row_id"]}.{key}','option_id':r['option_id'],'section':section,'field':key,'value':value,'unit':field_unit(key,r)})
    input_records += [{**r,'section':'source_input'} for r in tables.get('inputs',[])]
    input_records += [{**r,'section':'source_reference'} for r in tables.get('sources',[])]
    input_records += [{**r,'section':'condition','warning':standard_warning(str(r['warning']),language)} for r in tables.get('warnings',[])]
    # Top-level grid controls and unknown future nested data remain inspectable.
    assigned={'summary','option_comparison','breakdown','housing','cashflows','sensitivity','effective_settings','option_settings','inputs','inputs_json','sources','warnings','items','materials','projects','adjustments','element_totals','discounted_cashflows'}
    for section,records in tables.items():
        if section not in assigned:
            for r in records:
                for key,value in r.items():
                    if key not in ('row_id','option_id'):input_records.append({'row_id':r['row_id']+'.'+key,'option_id':r['option_id'],'section':section,'field':key,'value':value,'unit':field_unit(key,r)})
    if input_records or options:
        schedule('Inputs',input_records,['row_id','option_id','section','field','value','unit','source_ref','path','warning'])
        # Long input values inherit the original field's native numeric format.
        for row,r in zip(sheets[-1].rows[4:],input_records):
            if 'field' in r and 'value' in r:row[4]=excel_value(source_preview(r['value'],'value',r,language),r['field'],r)
    checks=[]
    def ref(rid,key):
        name,address,value=refs[(rid,key)];return (f"'{name}'!{address}" if ' ' in name else f'{name}!{address}'),value
    def check(oid,name,expression,cached,tolerance,basis):
        checks.append({'row_id':f'{oid or "report"}.check.{len(checks)+1:04d}','option_id':oid,'check':translated(name,language),'basis':translated(basis,language),'difference':Formula(expression,float(cached)),'tolerance':tolerance})
    for record in options:
        oid=record['option_id'];housing=[r for r in tables.get('housing',[]) if r['option_id']==oid];flows=[r for r in tables.get('cashflows',[]) if r['option_id']==oid]
        def total_of(rows,key):
            pairs=[ref(r['row_id'],key) for r in rows if key in r]
            return 'SUM('+','.join(p[0] for p in pairs)+')',sum(Decimal(str(p[1])) for p in pairs)
        for field,title in [('gifa_m2','户型面积 / Housing area'),('units_count','住宅数量 / Dwelling count')]:
            source='gifa_m2' if field=='gifa_m2' else 'count'
            if housing and field in record:
                expr,value=total_of(housing,source);out,expected=ref(oid,field)
                check(oid,title,f'{expr}-{out}',value-Decimal(str(expected)),.0000005*(len(housing)+1) if field=='gifa_m2' else 0,'户型明细之和减方案结果；面积按每行半个最小展示单位容许舍入差异，住宅数精确核对。 / Sum housing detail minus option output; area permits half a presentation unit per rounded value, dwellings reconcile exactly.')
        # Match the raw canonical label, not the translated spreadsheet display label.
        costs=[r for r in tables.get('breakdown',[]) if r['option_id']==oid and r.get('label')=='building_works']
        if housing and costs:
            expr,value=total_of(housing,'cost');out,expected=ref(costs[0]['row_id'],'amount')
            rate_rounding=sum(Decimal(str(h.get('gifa_m2',0)))*Decimal('.0000005') for h in housing)
            check(oid,'户型成本 / Housing costs',f'{expr}-{out}',value-Decimal(str(expected)),float(Decimal('.005')*(len(housing)+1)),'户型成本之和减房屋工程；每个舍入金额容许 0.005。 / Sum housing costs minus building works; 0.005 per rounded monetary value.')
            # Independently recompute the adopted quantity × adjusted-rate cost.
            value=Decimal(0)
            for h in housing:
                a,av=ref(h['row_id'],'area_m2');c,cv=ref(h['row_id'],'count');rate,rv=ref(h['row_id'],'adjusted_rate')
                value+=Decimal(str(av))*Decimal(str(cv))*Decimal(str(rv))
            ranges=[]
            for key in ('area_m2','count','adjusted_rate'):
                first,_=ref(housing[0]['row_id'],key);last=refs[(housing[-1]['row_id'],key)][1]
                ranges.append(first+':'+last)
            check(oid,'面积乘单价 / Area × rate','SUMPRODUCT('+','.join(ranges)+f')-{out}',value-Decimal(str(expected)),float(Decimal('.005')*(len(housing)+1)+rate_rounding),'展示面积 × 住宅数 × 调整单价减房屋工程；容许金额及六位单价舍入差异。 / Displayed area × dwellings × adjusted rate minus building works; includes monetary and 6-decimal rate tolerance.')
        if flows:
            for key,expected_field,title in [('loan_draw','loan_principal','贷款提取 / Loan draws'),('loan_repayment','loan_principal','贷款偿还 / Loan repayments'),('equity_cashflow','profit','权益现金流 / Equity flows')]:
                if expected_field not in record:continue
                expr,value=total_of(flows,key);out,expected=ref(oid,expected_field)
                check(oid,title,f'{expr}-{out}',value-Decimal(str(expected)),.005*(len(flows)+1),'月度舍入金额之和减方案结果；容许差额 = 0.005 × (行数 + 1)。 / Sum monthly rounded values minus option output; tolerance = 0.005 × (rows + 1).')
        if all(k in record for k in ('gdv','total','profit')):
            sales,sv=ref(oid,'gdv');cost,cv=ref(oid,'total');profit,pv=ref(oid,'profit')
            check(oid,'展示利润 / Displayed profit',f'{sales}-{cost}-{profit}',Decimal(str(sv))-Decimal(str(cv))-Decimal(str(pv)),.015,'销售总值减成本再减利润；三个数均按两位小数展示。 / GDV minus cost minus profit; three values rounded to 2 decimals.')
    if not checks:
        # An unavailable detail reconciliation is explicit, rather than a synthetic PASS.
        checks.append({'row_id':'report.check.0001','option_id':'','check':translated('明细核对不可用 / Detail reconciliation unavailable',language),'basis':translated('本工具未提供可独立核对的明细。 / This tool provides no independently reconcilable schedule.',language),'difference':None,'tolerance':None})
    check_sheet=schedule('Checks',checks,['row_id','option_id','check','basis','difference','tolerance'])
    for row in check_sheet.rows[4:]:
        if isinstance(row[4],Cell) and isinstance(row[4].value,Formula):row[4]=Cell(row[4].value,8)
    return workbook_bytes(sheets)


def report_bundle(result,language='bilingual'):
    language_check(language);tables=report_tables(result)
    members={'report.html':report_html(result,language).encode('utf-8'),'estimate.xlsx':report_xlsx(result,language),
             'inputs.json':(json_text(result.get('inputs',{}),True)+'\n').encode('utf-8'),
             'result.json':(json_text(result,True)+'\n').encode('utf-8'),
             'report.csv':report_csv(result).encode('utf-8-sig')}
    for section,records in tables.items():
        if section=='inputs_json':continue
        fields=list(dict.fromkeys(['row_id','option_id','source_ref',*(k for r in records for k in r)]))
        members[f'tables/{section}.csv']=csv_records(records,fields).encode('utf-8-sig')
    manifest={'schema':'construction-cost-report','schema_version':SCHEMA_VERSION,'language':language,
              'reporting_units':{'currency':result.get('currency',''),'money':'currency units; 2 display decimals','area':'m2','quantity_rate_precision':6,'json_csv_percent':'0..100','xlsx_percent':'fraction'},
              'calculation':{'method':'Decimal application calculation; adopted cost sequence and bases','rounding':result.get('rounding_policy','Money 2 decimals; quantities/rates up to 6 decimals'),'basis':'Snapshot; change assumptions in app and recalculate; terminal checks never drive outputs'},
              'metadata':{**{k:v for k,v in result.items() if k in ('project_name','currency','type','metadata','effective_settings','price_basis','risk_scope','cost_changes_pct','value_changes_pct')},**adopted_metadata(result)},
              'members':{name:{'sha256':hashlib.sha256(content).hexdigest(),'byte_length':len(content)} for name,content in members.items()}}
    members['manifest.json']=(json_text(manifest,True)+'\n').encode('utf-8')
    return deterministic_zip(members)


def export_report(result,directory,name='report',language='bilingual'):
    language_check(language)
    if not name.replace('-','').replace('_','').isalnum():raise ValueError('Report name: letters, numbers, hyphen or underscore only')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    contents={'json':(json_text(result,True)+'\n').encode('utf-8'),'csv':report_csv(result).encode('utf-8-sig'),
              'html':report_html(result,language).encode('utf-8'),'xlsx':report_xlsx(result,language),'zip':report_bundle(result,language)}
    paths={}
    for extension,content in contents.items():
        path=directory/f'{name}.{extension}';path.write_bytes(content);paths[extension]=str(path)
    return paths
