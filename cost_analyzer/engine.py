"""Explicit cost bases and net geometry; rates are supplied by the estimator."""
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from functools import wraps
import json
from .validation import ZERO, ONE, number, fixed_number, pct, flag, currency, unit, money, output, text, price_date


def capture_inputs(function):
    @wraps(function)
    def calculate(data):
        if not isinstance(data,dict):
            raise ValueError('Input must be an object')
        try:
            snapshot=json.loads(json.dumps(data,ensure_ascii=False,allow_nan=False))
            result=function(data)
        except (TypeError,DecimalException,OverflowError) as exc:
            raise ValueError('Invalid input or calculation outside supported precision') from exc
        result['inputs']=snapshot
        return result
    return calculate


def allowances(direct, settings, *, includes_preliminaries=False, includes_ohp=False):
    prelim_pct=pct(settings.get('preliminaries_pct',0),'preliminaries_pct')
    ohp_pct=pct(settings.get('overheads_profit_pct',0),'overheads_profit_pct')
    if includes_preliminaries and prelim_pct:
        raise ValueError('Preliminaries already included in a rate; remove the duplicate allowance')
    if includes_ohp and ohp_pct:
        raise ValueError('OH&P already included in a rate; remove the duplicate allowance')
    result={'direct_cost':output(direct,2)}
    breakdown=[{'label':'direct_cost','base':output(direct,2),'percent':0,'amount':output(direct,2)}]
    prelim=money(direct*prelim_pct/100)
    ohp=money((direct+prelim)*ohp_pct/100)
    subtotal=direct+prelim+ohp
    contingency_pct=pct(settings.get('contingency_pct',0),'contingency_pct')
    fees_pct=pct(settings.get('fees_pct',0),'fees_pct')
    vat_pct=pct(settings.get('vat_pct',0),'vat_pct')
    contingency=money(subtotal*contingency_pct/100)
    # Fees include contingency in their base; VAT applies to cost plus fees.
    fees=money((subtotal+contingency)*fees_pct/100)
    vat=money((subtotal+contingency+fees)*vat_pct/100)
    rows=[('preliminaries',direct,prelim_pct,prelim),('overheads_profit',direct+prelim,ohp_pct,ohp),
          ('contingency',subtotal,contingency_pct,contingency),('fees',subtotal+contingency,fees_pct,fees),
          ('vat',subtotal+contingency+fees,vat_pct,vat)]
    for label,base,percent,amount in rows:
        result[label]=output(amount,2)
        breakdown.append({'label':label,'base':output(base,2),'percent':output(percent),'amount':output(amount,2)})
    result['total']=output(subtotal+contingency+fees+vat,2)
    result['breakdown']=breakdown
    result['warnings']=[]
    if includes_preliminaries or includes_ohp:
        result['warnings'].append('The base includes stated on-costs; zero additional allowance does not strip embedded costs.')
    return result


@capture_inputs
def early_estimate(data):
    area=fixed_number(data.get('area_m2'),'area_m2',positive=True)
    rate=fixed_number(data.get('base_rate'),'base_rate',positive=True)
    base_index=number(data.get('base_index',100),'base_index',positive=True)
    target_index=number(data.get('target_index',100),'target_index',positive=True)
    base_location=number(data.get('base_location_index',100),'base_location_index',positive=True)
    target_location=number(data.get('target_location_index',100),'target_location_index',positive=True)
    quality=number(data.get('quality_factor',1),'quality_factor',positive=True,maximum=10)
    adjusted=(rate*target_index/base_index*target_location/base_location*quality).quantize(Decimal('.000001'),rounding=ROUND_HALF_UP)
    result=allowances(money(area*adjusted),data,
                      includes_preliminaries=flag(data.get('rate_includes_preliminaries',False),'rate_includes_preliminaries'),
                      includes_ohp=flag(data.get('rate_includes_ohp',False),'rate_includes_ohp'))
    result.update(project_name=text(data.get('project_name','Area estimate'),'project_name'),currency=currency(data.get('currency','GBP')),
                  area_m2=output(area),adjusted_rate=output(adjusted),cost_per_m2=output(Decimal(str(result['total']))/area,2),
                  source_ref=text(data.get('source_ref',''),'source_ref'),price_date=price_date(data.get('price_date','')),
                  cost_scope=text(data.get('cost_scope','building'),'cost_scope'),
                  adjustments={'base_index':output(base_index),'target_index':output(target_index),'base_location_index':output(base_location),
                               'target_location_index':output(target_location),'quality_factor':output(quality)})
    if not result['source_ref'] or not result['price_date']:
        result['warnings'].append('Record the rate source and price date before using the estimate for a project.')
    return result


@capture_inputs
def takeoff(data):
    method=data.get('method','rectangle')
    count=number(data.get('count',1),'count',positive=True,maximum=10**6)
    if count!=count.to_integral_value():
        raise ValueError('count: use a whole number')
    if method=='count':
        gross=count; measure_unit='nr'; formula='count - deduction'
    else:
        length=number(data.get('length'),'length',positive=True,maximum=10**6)
        if method=='linear':
            gross=length*count; measure_unit='m'; formula='length × count - deduction'
        else:
            width=number(data.get('width'),'width',positive=True,maximum=10**6)
            if method in ('centreline','strip_foundation'):
                thickness=number(data.get('wall_thickness'),'wall_thickness',positive=True)
                if thickness>=min(length,width):
                    raise ValueError('wall_thickness must be smaller than both external dimensions')
                centreline=2*(length+width-2*thickness)*count
                if method=='centreline':
                    gross=centreline; measure_unit='m';formula='2 × (external length + external width - 2 × wall thickness) × count - deduction'
                else:
                    tw=number(data.get('trench_width'),'trench_width',positive=True)
                    td=number(data.get('trench_depth'),'trench_depth',positive=True)
                    cw=number(data.get('concrete_width'),'concrete_width',positive=True)
                    cd=number(data.get('concrete_depth'),'concrete_depth',positive=True)
                    if cw>tw or cd>td:
                        raise ValueError('Concrete section must fit inside the trench')
                    excavation=centreline*tw*td; concrete=centreline*cw*cd
                    displaced=number(data.get('other_displaced_volume',0),'other_displaced_volume')
                    if displaced>excavation-concrete:
                        raise ValueError('Displaced volume exceeds available backfill')
                    return {'centreline_m':output(centreline),'excavation_m3':output(excavation),'concrete_m3':output(concrete),
                            'backfill_m3':output(excavation-concrete-displaced),'formula':'Natural trench volume minus concrete and other displaced volume',
                            'warnings':['Rectangular continuous strip only. Junctions, working space, earthwork support, bulking and disposal are separate measured items.']}
            elif method in ('rectangle','volume'):
                gross=length*width*count;measure_unit='m2';formula='length × width × count - deduction'
                if method=='volume':
                    height=number(data.get('height'),'height',positive=True,maximum=10**6)
                    gross*=height;measure_unit='m3';formula='length × width × height × count - deduction'
            else:
                raise ValueError('method: rectangle, volume, linear, count, centreline or strip_foundation')
    deduction=number(data.get('deduction',0),'deduction')
    if deduction>gross:
        raise ValueError('Deduction exceeds gross measurement')
    return {'quantity':output(gross-deduction),'unit':measure_unit,'gross_quantity':output(gross),
            'deduction':output(deduction),'formula':formula,'warnings':['Net geometric quantities. Apply the project measurement rules to descriptions and deductions.']}


@capture_inputs
def unit_rate(data):
    materials=data.get('materials',[])
    if not isinstance(materials,list) or len(materials)>1000:
        raise ValueError('materials: use a list with at most 1000 rows')
    total_material=ZERO; details=[]
    for i,row in enumerate(materials,1):
        if not isinstance(row,dict):
            raise ValueError(f'material {i}: use an object')
        consumption=number(row.get('consumption'),'consumption')
        pack_price=number(row.get('pack_price'),'pack_price')
        pack_size=number(row.get('pack_size'),'pack_size',positive=True)
        waste=pct(row.get('waste_pct',0),'waste_pct')
        cost=consumption*pack_price/pack_size*(ONE+waste/100)
        total_material+=cost
        details.append({'name':text(row.get('name',f'Material {i}'),'material name'),'cost_per_unit':output(cost),
                        'consumption':output(consumption),'purchased_consumption':output(consumption*(ONE+waste/100))})
    crew=number(data.get('crew_hourly_cost',0),'crew_hourly_cost')
    crew_output=number(data.get('crew_output_per_hour',1),'crew_output_per_hour',positive=bool(crew))
    plant=number(data.get('plant_hourly_cost',0),'plant_hourly_cost')
    plant_output=number(data.get('plant_output_per_hour',1),'plant_output_per_hour',positive=bool(plant))
    labour=crew/crew_output if crew else ZERO
    plant_cost=plant/plant_output if plant else ZERO
    subcontract=number(data.get('subcontract_per_unit',0),'subcontract_per_unit')
    markup=pct(data.get('markup_pct',0),'markup_pct')
    direct=total_material+labour+plant_cost+subcontract
    return {'unit':unit(data.get('unit','m2')),'currency':currency(data.get('currency','GBP')),
            'material':output(total_material),'labour':output(labour),'plant':output(plant_cost),'subcontract':output(subcontract),
            'direct_rate':output(direct),'quoted_rate':output(direct*(ONE+markup/100)),'markup_pct':output(markup),'materials':details,
            'warnings':['Use total crew output, not individual output. Check whether subcontract and plant quotes already include labour or other costs.']}


def price_boq(rows, settings):
    if not isinstance(settings,dict):
        raise ValueError('Project settings must be an object')
    if not isinstance(rows,list) or not rows or len(rows)>10000:
        raise ValueError('BOQ: provide between 1 and 10000 rows')
    project_currency=currency(settings.get('currency','GBP'))
    result_rows=[];seen=set();direct=ZERO;included_prelims=False;included_ohp=False;missing_sources=0
    for n,row in enumerate(rows,1):
        if not isinstance(row,dict):
            raise ValueError(f'BOQ row {n}: use an object')
        identifier=text(row.get('item_id'),'item_id',100)
        if not identifier or identifier in seen:
            raise ValueError(f'BOQ row {n}: item_id is empty or duplicated')
        if not text(row.get('description'),'description'):
            raise ValueError(f'BOQ row {n}: work description is required')
        seen.add(identifier)
        if currency(row.get('currency',project_currency))!=project_currency:
            raise ValueError(f'BOQ row {n}: mixed currencies are not supported')
        quantity=fixed_number(row.get('quantity'),'quantity');rate=fixed_number(row.get('rate'),'rate')
        total=money(quantity*rate); direct+=total
        included_prelims |= flag(row.get('included_preliminaries',False),'included_preliminaries')
        included_ohp |= flag(row.get('included_ohp',False),'included_ohp')
        source=text(row.get('source_ref',''),'source_ref');priced=price_date(row.get('price_date',''))
        missing_sources+=not bool(source and priced)
        result_rows.append({'item_id':identifier,'description':text(row.get('description'),'description'),
                            'element':text(row.get('element','Unassigned'),'element'),'unit':unit(row.get('unit','item')),
                            'quantity':output(quantity),'rate':output(rate),'total':output(total,2),'currency':project_currency,
                            'source_ref':source,'price_date':priced,
                            'included_preliminaries':flag(row.get('included_preliminaries',False),'included_preliminaries'),
                            'included_ohp':flag(row.get('included_ohp',False),'included_ohp')})
    result=allowances(direct,settings,includes_preliminaries=included_prelims,includes_ohp=included_ohp)
    result.update(items=result_rows,project_name=text(settings.get('project_name','BOQ estimate'),'project_name'),currency=project_currency)
    elements={}
    for row in result_rows:
        elements[row['element']]=elements.get(row['element'],ZERO)+Decimal(str(row['total']))
    result['element_totals']={key:output(value,2) for key,value in elements.items()}
    result['inputs']=json.loads(json.dumps({'items':rows,'project':settings},ensure_ascii=False,allow_nan=False))
    if missing_sources:
        result['warnings'].append(f'{missing_sources} item(s) lack a complete rate source and price date.')
    return result


@capture_inputs
def appraise(data):
    flows=data.get('cashflows',[])
    if not isinstance(flows,list) or not 2<=len(flows)<=200:
        raise ValueError('cashflows: provide 2 to 200 annual values, starting at period 0')
    values=[number(value,f'cashflow {i}',minimum=-(10**15)) for i,value in enumerate(flows)]
    discount=number(data.get('discount_rate_pct',8),'discount_rate_pct',minimum=-99,maximum=1000)/100
    discounted=[value/(ONE+discount)**i for i,value in enumerate(values)]
    def payback(series):
        if series[0]>=0:
            return None
        running=series[0]
        for i,value in enumerate(series[1:],1):
            if running<0 and running+value>=0 and value>0:
                return output(Decimal(i-1)-running/value)
            running+=value
        return None
    warnings=[];irr=None
    if values[0]<0 and all(v>=0 for v in values[1:]) and any(v>0 for v in values[1:]):
        def npv(rate):
            return sum(value/(ONE+rate)**i for i,value in enumerate(values))
        lower=Decimal('-0.999999');upper=ONE
        while npv(upper)>0 and upper<1024:
            upper*=2
        if npv(upper)==0:
            irr=output(upper*100)
        elif npv(lower)==0:
            irr=output(lower*100)
        elif npv(lower)>0 and npv(upper)<0:
            for _ in range(160):
                middle=(lower+upper)/2
                if npv(middle)>0: lower=middle
                else: upper=middle
            irr=output((lower+upper)*50)
        else:
            warnings.append('IRR outside the supported search range.')
    else:
        warnings.append('IRR is unavailable: require an initial outflow followed only by nonnegative flows for a unique conventional result.')
    gdv=number(data.get('gdv',0),'gdv');cost=number(data.get('non_land_cost',0),'non_land_cost')
    profit=pct(data.get('target_profit_pct',0),'target_profit_pct')/100
    basis=data.get('profit_basis','gdv')
    if basis not in ('gdv','cost'):
        raise ValueError('profit_basis: use gdv or cost')
    residual=gdv*(ONE-profit)-cost if basis=='gdv' else gdv/(ONE+profit)-cost
    return {'currency':currency(data.get('currency','GBP')),'npv':output(sum(discounted),2),'irr_pct':irr,
            'payback_period':payback(values),'discounted_payback_period':payback(discounted),
            'residual_land_value':output(money(residual),2),'profit_basis':basis,
            'discounted_cashflows':[output(v,2) for v in discounted],
            'payback_convention':'Linear interpolation within each annual period; NPV uses end-period cashflows.',
            'warnings':warnings}
