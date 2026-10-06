"""Residential option estimates with explicit scope and monthly loan draws.

All arithmetic retains Decimal precision until presentation. This calculation
sequence is configurable study/project input, not an assertion of NRM compliance.
"""
import calendar
from datetime import date
from decimal import Decimal
from .engine import capture_inputs
from .validation import ZERO, ONE, number, fixed_number, pct, flag, currency, output, text, price_date

PERCENTAGES=('external_works_pct','preliminaries_pct','overheads_profit_pct','fees_pct',
             'embedded_preliminaries_pct','marketing_pct','risk_design_pct','risk_construction_pct',
             'risk_employer_change_pct','risk_other_pct','tender_inflation_pct','construction_inflation_pct',
             'loan_share_pct','loan_interest_pct','loan_fee_pct','hurdle_pct','discount_rate_pct','sensitivity_pct')
RISK_KEYS=('risk_design','risk_construction','risk_employer_change','risk_other')
OPTION_SETTINGS={'duration_months','prep_months','prep_spend_pct','start_date','external_works_pct',
                 'facilitating_cost','marketing_pct','loan_share_pct','loan_interest_pct','loan_fee_pct'}
REPORT_FIELDS={'report_reference','revision','estimate_date','prepared_by','client_name'}
TOP_FIELDS=set(PERCENTAGES)|{'project_name','currency','site_area_m2','land_rate','site_clearance_rate',
    'facilitating_cost','duration_months','prep_months','prep_spend_pct','base_index','target_index',
    'base_location_index','target_location_index','price_basis','risk_scope','rate_includes_preliminaries',
    'rate_includes_ohp','start_date','price_date','source_ref','index_source_ref','assumptions','options',
    'cost_changes_pct','value_changes_pct'}|REPORT_FIELDS
TEXT_FIELDS={'project_name','currency','price_basis','risk_scope','start_date','price_date',
             'source_ref','index_source_ref','assumptions','name','area_source_ref'}|REPORT_FIELDS


def validate_fields(data,allowed):
    unknown=set(data)-allowed
    if unknown:raise ValueError('Unknown field(s): '+', '.join(sorted(str(k) for k in unknown)))
    for key in TEXT_FIELDS.intersection(data):
        if not isinstance(data[key],str):raise ValueError(f'{key}: use text')
        text(data[key],key)
    for key in ('rate_includes_preliminaries','rate_includes_ohp'):
        if key in data and not isinstance(data[key],(bool,str)):
            raise ValueError(f'{key}: use a boolean or true/false text')


def integer(value,name,minimum=0,maximum=120):
    result=number(value,name,minimum=minimum,maximum=maximum)
    if result!=result.to_integral_value():raise ValueError(f'{name}: use a whole number')
    return int(result)


def sensitivity_grid(data,key):
    if key not in data:
        variance=pct(data.get('sensitivity_pct',10),'sensitivity_pct')
        return sorted({-variance,ZERO,variance})
    raw=data[key]
    if not isinstance(raw,list) or not 1<=len(raw)<=7:raise ValueError(f'{key}: use 1 to 7 percentages including zero')
    values=[number(v,key,minimum=-100,maximum=100) for v in raw]
    if len(set(values))!=len(values) or ZERO not in values:
        raise ValueError(f'{key}: use unique percentages including zero')
    return sorted(values)


def annual_irr(flows):
    """Unique IRR only for one change from negative to positive cashflows."""
    nonzero=[v for v in flows if v]
    if not nonzero or nonzero[0]>=0 or nonzero[-1]<=0:return None
    signs=[v>0 for v in nonzero]
    if sum(a!=b for a,b in zip(signs,signs[1:]))!=1:return None
    def npv(rate):return sum(v/(ONE+rate)**i for i,v in enumerate(flows))
    low=Decimal('-.999999');high=ONE
    while npv(high)>0 and high<1024:high*=2
    if not (npv(low)>0 and npv(high)<=0):return None
    for _ in range(160):
        mid=(low+high)/2
        if npv(mid)>0:low=mid
        else:high=mid
    annual=((ONE+(low+high)/2)**12-ONE)*100
    if abs(annual)>Decimal('1e9'):return None
    return output(annual)


def month_date(start,month):
    if not start:return ''
    current=date.fromisoformat(start);absolute=current.year*12+current.month-1+month
    year,zero_month=divmod(absolute,12);day=min(current.day,calendar.monthrange(year,zero_month+1)[1])
    return date(year,zero_month+1,day).isoformat()


def settings(data):
    validate_fields(data,TOP_FIELDS)
    p={k:pct(data.get(k,10 if k in ('hurdle_pct','sensitivity_pct') else 0),k)/100 for k in PERCENTAGES}
    n=integer(data.get('duration_months',5),'duration_months',minimum=1)
    prep=integer(data.get('prep_months',1 if n>1 else 0),'prep_months',maximum=n-1)
    share=pct(data.get('prep_spend_pct',10 if prep else 0),'prep_spend_pct')/100
    if not prep and share:raise ValueError('prep_spend_pct: use zero when prep_months is zero')
    weights=[share/prep if i<prep else (ONE-share)/(n-prep) for i in range(n)]
    basis=data.get('price_basis','estimate_plus_inflation');scope=data.get('risk_scope','all_in')
    if basis not in ('estimate_plus_inflation','completion_index'):raise ValueError('price_basis: invalid option')
    if scope not in ('all_in','works_only'):raise ValueError('risk_scope: use all_in or works_only')
    if basis=='completion_index' and (p['tender_inflation_pct'] or p['construction_inflation_pct']):
        raise ValueError('Completion index already prices the future period: set both inflation allowances to zero')
    includes=flag(data.get('rate_includes_preliminaries',False),'rate_includes_preliminaries')
    includes_ohp=flag(data.get('rate_includes_ohp',False),'rate_includes_ohp')
    if not includes and p['embedded_preliminaries_pct']:raise ValueError('embedded preliminaries requires an inclusive rate')
    if includes and not p['embedded_preliminaries_pct'] and p['preliminaries_pct']:
        raise ValueError('Preliminaries already included: record an embedded percentage to reconstruct a net rate, or use no extra allowance')
    if includes_ohp and p['overheads_profit_pct']:raise ValueError('OH&P already included in the rate')
    price_factor=number(data.get('target_index',100),'target_index',positive=True)/number(data.get('base_index',100),'base_index',positive=True)
    location=number(data.get('target_location_index',100),'target_location_index',positive=True)/number(data.get('base_location_index',100),'base_location_index',positive=True)
    net_factor=price_factor*location/(ONE+p['embedded_preliminaries_pct'])
    site=number(data.get('site_area_m2'),'site_area_m2',positive=True)
    land=site*number(data.get('land_rate',0),'land_rate')
    clearance=site*number(data.get('site_clearance_rate',0),'site_clearance_rate')
    facilitating=number(data.get('facilitating_cost',0),'facilitating_cost')
    risk=sum(p[k+'_pct'] for k in RISK_KEYS)
    multiplier=(ONE+risk)*(ONE+p['tender_inflation_pct'])*(ONE+p['construction_inflation_pct'])
    other_factor=multiplier if scope=='all_in' else ONE
    if ONE/(ONE+p['hurdle_pct'])-other_factor*p['marketing_pct']<=0:
        raise ValueError('marketing_pct: no finite sales value can achieve the stated hurdle with these reserves')
    weighted_years=sum(w*Decimal(n-i)/12 for i,w in enumerate(weights))
    aK=p['loan_share_pct']*(p['loan_interest_pct']*weighted_years+p['loan_fee_pct'])
    aL=p['loan_share_pct']*(p['loan_interest_pct']*Decimal(n)/12+p['loan_fee_pct'])
    start=price_date(data.get('start_date',''));price_date(data.get('price_date',''));price_date(data.get('estimate_date',''))
    # Validate completion-date bounds before constructing the entire report.
    month_date(start,n)
    return p,n,weights,net_factor,site,land,clearance,facilitating,multiplier,other_factor,aK,aL,start


def option(raw,s,data):
    validate_fields(raw,{'name','units','settings'})
    if 'settings' in raw:
        overrides=raw['settings']
        if not isinstance(overrides,dict):raise ValueError('option settings: use an object')
        validate_fields(overrides,OPTION_SETTINGS)
        data={**data,**overrides};s=settings(data)
    p,n,weights,factor,site,land,clearance,facilitating,M,B,aK,aL,start=s
    effective={k:output(p[k]*100) for k in sorted(OPTION_SETTINGS) if k in p}
    adopted_prep=integer(data.get('prep_months',1 if n>1 else 0),'prep_months')
    effective.update(duration_months=n,prep_months=adopted_prep,
                     prep_spend_pct=output(pct(data.get('prep_spend_pct',10 if adopted_prep else 0),'prep_spend_pct')),
                     start_date=start,facilitating_cost=output(facilitating,2))
    name=text(raw.get('name'),'option name',limit=100)
    if not name:raise ValueError('option name is required')
    units=raw.get('units')
    if not isinstance(units,list) or not 1<=len(units)<=200:raise ValueError('units: provide 1 to 200 housing types')
    housing=[];house_cost=ZERO;V=ZERO;area=ZERO;count=0
    for item in units:
        if not isinstance(item,dict):raise ValueError('units: each housing type must be an object')
        validate_fields(item,{'name','count','area_m2','base_rate','sale_price','source_ref','area_source_ref'})
        unit_name=text(item.get('name'),'housing name',limit=100)
        if not unit_name:raise ValueError('housing name is required')
        c=integer(item.get('count'),'count',minimum=1,maximum=10000)
        a=fixed_number(item.get('area_m2'),'area_m2',positive=True)
        rate=fixed_number(item.get('base_rate'),'base_rate',positive=True)*factor
        sale=fixed_number(item.get('sale_price'),'sale_price')
        cost=a*c*rate;gdv=sale*c;gifa=a*c
        house_cost+=cost;V+=gdv;area+=gifa;count+=c
        housing.append({'name':unit_name,'count':c,'area_m2':output(a),'gifa_m2':output(gifa),
                        'adjusted_rate':output(rate),'cost':output(cost,2),'gdv':output(gdv,2),
                        'source_ref':text(item.get('source_ref',data.get('source_ref','')),'source_ref'),
                        'area_source_ref':text(item.get('area_source_ref',''),'area_source_ref')})
    externals=house_cost*p['external_works_pct'];building=house_cost+externals
    prelim=building*p['preliminaries_pct'];contract=building+clearance+facilitating+prelim
    ohp=contract*p['overheads_profit_pct'];works=contract+ohp;fees=works*p['fees_pct'];K=works+fees
    commitment=p['loan_share_pct']*(K+land);arrangement=commitment*p['loan_fee_pct']
    finance=aK*K+aL*land;interest=finance-arrangement;marketing=p['marketing_pct']*V
    base=K+land+finance+marketing;total=M*K+B*(land+finance+marketing)
    profit=V-total;roc=profit/total if total else ZERO
    breakdown=[]
    def row(label,amount,base_value=None,percent=ZERO):
        breakdown.append({'label':label,'base':output(amount if base_value is None else base_value,2),
                          'percent':output(percent*100),'amount':output(amount,2)})
    for label,amount in [('building_works',house_cost),('external_works',externals),('building_estimate',building),
                         ('site_clearance',clearance),('facilitating_works',facilitating)]:
        row(label,amount,house_cost if label=='external_works' else None,p['external_works_pct'] if label=='external_works' else ZERO)
    row('preliminaries',prelim,building,p['preliminaries_pct']);row('contract_subtotal',contract)
    row('overheads_profit',ohp,contract,p['overheads_profit_pct']);row('works_total',works)
    row('fees',fees,works,p['fees_pct']);row('works_and_fees',K);row('land_cost',land,site)
    row('marketing',marketing,V,p['marketing_pct']);row('interest',interest);row('arrangement_fee',arrangement,commitment,p['loan_fee_pct']);row('base_cost',base)
    risk_base=base if B==M else K
    risks=ZERO
    for key in RISK_KEYS:
        value=risk_base*p[key+'_pct'];risks+=value;row(key,value,risk_base,p[key+'_pct'])
    row('after_risk',base+risks)
    tender=(risk_base+risks)*p['tender_inflation_pct'];row('tender_inflation',tender,risk_base+risks,p['tender_inflation_pct']);row('after_tender',base+risks+tender)
    inflation=(risk_base+risks+tender)*p['construction_inflation_pct'];row('construction_inflation',inflation,risk_base+risks+tender,p['construction_inflation_pct']);row('total',total)
    # Spread all reserves using the entered works profile, retaining land/sales payments at their stated times.
    budget_works=total-land-marketing-finance
    flows=[];budget_flows=[];equity_flows=[];balance=ZERO
    for month in range(n+1):
        w=weights[month] if month<n else ZERO;lp=land if month==0 else ZERO
        wp=w*budget_works;sales=V if month==n else ZERO;q=sales*p['marketing_pct']
        budget=sales-lp-wp-q;draw=p['loan_share_pct']*(lp+w*K);balance+=draw
        repayment=balance if month==n else ZERO;balance-=repayment
        carry=balance*p['loan_interest_pct']/12;fee=arrangement if month==0 else ZERO
        equity=budget+draw-carry-fee-repayment
        present=budget/(ONE+p['discount_rate_pct'])**(Decimal(month)/12)
        flows.append({'month':month,'date':month_date(start,month),'spend_fraction':output(w),
                      'land_payment':output(lp,2),'works_payment':output(wp,2),'sales':output(sales,2),
                      'marketing':output(q,2),'budget_cashflow':output(budget,2),'loan_draw':output(draw,2),
                      'loan_balance':output(balance,2),'interest':output(carry,2),'arrangement_fee':output(fee,2),
                      'loan_repayment':output(repayment,2),'equity_cashflow':output(equity,2),'present_value':output(present,2)})
        budget_flows.append(budget);equity_flows.append(equity)
    non_sales=M*K+B*(land+finance)
    target_denominator=ONE/(ONE+p['hurdle_pct'])-B*p['marketing_pct']
    residual=(V/(ONE+p['hurdle_pct'])-B*p['marketing_pct']*V-K*(M+B*aK))/(B*(ONE+aL))
    sensitivity=[]
    for cost_pct in sensitivity_grid(data,'cost_changes_pct'):
        change_cost=cost_pct/100
        for value_pct in sensitivity_grid(data,'value_changes_pct'):
            change_value=value_pct/100
            sv=V*(ONE+change_value);sc=non_sales*(ONE+change_cost)+B*p['marketing_pct']*sv
            sp=sv-sc;sr=sp/sc if sc else None
            sensitivity.append({'cost_change_pct':output(change_cost*100),'value_change_pct':output(change_value*100),
                                'total':output(sc,2),'gdv':output(sv,2),'profit':output(sp,2),
                                'return_on_cost_pct':output(sr*100) if sr is not None else None,
                                'meets_hurdle':sr is not None and sr>=p['hurdle_pct']})
    def npv(values):return output(sum(v/(ONE+p['discount_rate_pct'])**(Decimal(i)/12) for i,v in enumerate(values)),2)
    return {'name':name,'total':output(total,2),'gifa_m2':output(area),'units_count':count,'gdv':output(V,2),
            'profit':output(profit,2),'return_on_cost_pct':output(roc*100),'profit_on_gdv_pct':output(profit/V*100) if V else None,
            'meets_hurdle':roc>=p['hurdle_pct'],'land_cost':output(land,2),'works_and_fees':output(K,2),
            'finance':output(finance,2),'interest':output(interest,2),'arrangement_fee':output(arrangement,2),
            'loan_principal':output(commitment,2),'breakeven_gdv':output(non_sales/(ONE-B*p['marketing_pct']),2),
            'target_gdv':output(non_sales/target_denominator,2),'residual_land_value':output(residual,2),
            'affordable_cost':output(V/(ONE+p['hurdle_pct']),2),'budget_npv':npv(budget_flows),'equity_npv':npv(equity_flows),
            'budget_irr_annual_pct':annual_irr(budget_flows),'equity_irr_annual_pct':annual_irr(equity_flows),
            'effective_settings':effective,'cost_per_m2':output(total/area),'cost_per_unit':output(total/Decimal(count),2),
            'breakdown':breakdown,'housing':housing,'cashflows':flows,'sensitivity':sensitivity},roc


@capture_inputs
def development(data):
    common=settings(data)
    cost_grid=sensitivity_grid(data,'cost_changes_pct');value_grid=sensitivity_grid(data,'value_changes_pct')
    raw=data.get('options')
    if not isinstance(raw,list) or not 1<=len(raw)<=20:raise ValueError('options: provide 1 to 20 alternatives')
    if any(not isinstance(r,dict) for r in raw):raise ValueError('options: each alternative must be an object')
    calculated=[option(r,common,data) for r in raw]
    options=[result for result,_ in calculated]
    names=[r['name'] for r in options]
    if len(set(names))!=len(names):raise ValueError('option names must be unique')
    viable=[(r,roc) for r,roc in calculated if r['meets_hurdle']]
    recommended=max(viable,key=lambda entry:entry[1])[0]['name'] if viable else None
    warnings=[
        '利润率按整个项目的总成本计算；月度 IRR 另行年化。 / Return on cost covers the whole project; monthly IRR is separately annualized.',
        '贷款按土地及风险前工程/设计费分期提取；利息不资本化，准备金、营销费和融资费用由权益支付。 / Loan draws fund land and pre-reserve works/fees; simple interest is cash-serviced, with reserves, marketing and finance equity-funded.',
        '预算 NPV 去掉实际融资及本金现金流，但保留已分配的准备金；权益 NPV 包含融资。 / Budget NPV excludes actual finance/principal flows but retains allocated reserves; equity NPV includes financing.',
        '内部计算保留精度，展示金额取两位；明细之和可能有分位差异。 / Calculation retains precision until display rounding; rounded rows may differ by pennies.',
        '敏感性分别调整非销售成本与售价，营销费用随售价重算。 / Sensitivity varies non-sales costs and values independently, recalculating marketing.',
        '税费不自动推定；建筑面积、单价、指数系列与日期须与采用的资料对应。 / Tax treatment is not inferred; match areas, rates, index series and dates to the adopted sources.'
    ]
    if common[0]['embedded_preliminaries_pct']:
        warnings.append('移除已含现场费使用输入的比例；未经明细证实的比例属于 proxy 假设。 / Stripping embedded preliminaries uses the entered proportion; without a source breakdown it is a proxy assumption.')
    if not data.get('price_date') or not data.get('index_source_ref') or any(not h['source_ref'] or not h['area_source_ref'] for r in options for h in r['housing']):
        warnings.append('请补全面积、价格与指数来源及价格日期，再用于项目或作业判断。 / Complete area, rate and index references and price dates before using the result for project or coursework decisions.')
    if not viable:warnings.append('没有方案达到目标回报；亏损最小不构成可行方案。 / No option meets the hurdle; the smallest loss is not a viable recommendation.')
    if any(r['residual_land_value']<0 for r in options):warnings.append('负土地余额代表缺口，不是可报出的土地购买价。 / A negative land residual is a deficit, not a land bid.')
    return {'type':'development','project_name':text(data.get('project_name','Development options'),'project_name'),
            'currency':currency(data.get('currency','GBP')),'option_count':len(options),'viable_count':len(viable),
            'recommended_option':recommended,'price_basis':data.get('price_basis','estimate_plus_inflation'),
            'risk_scope':data.get('risk_scope','all_in'),'rounding_policy':'Full Decimal calculation; display only: money 2 decimals, quantities/rates 6 decimals',
            'cost_changes_pct':[output(v) for v in cost_grid],'value_changes_pct':[output(v) for v in value_grid],
            'options':options,'warnings':warnings}
