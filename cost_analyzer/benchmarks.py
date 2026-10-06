"""Comparable cost records and reproducible, explicitly synthetic scenarios."""
import csv
import io
import random
from decimal import Decimal
from .validation import number, currency, unit, price_date, flag, text, output

PROJECT_FIELDS=('project_id','building_type','region','currency','floor_area_m2','budget','actual_cost',
                'base_index','location_index','cost_scope','source_type','source_ref','price_date')
BOQ_FIELDS=('item_id','description','element','unit','quantity','rate','currency','source_ref','price_date')


def csv_rows(content, required):
    if not isinstance(content,str) or len(content.encode('utf-8'))>5_000_000:
        raise ValueError('CSV must be UTF-8 text under 5 MB')
    reader=csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)) or not set(required)<=set(reader.fieldnames):
        raise ValueError('CSV missing required columns or has duplicate headers: '+', '.join(required))
    rows=[]
    for row_number,row in enumerate(reader,2):
        if row_number>10001:
            raise ValueError('CSV exceeds 10000 rows')
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f'CSV row {row_number}: column count does not match header')
        rows.append((row_number,row))
    if not rows:
        raise ValueError('CSV contains no data rows')
    return rows


def read_boq_csv(content):
    result=[]
    for row_number,row in csv_rows(content,BOQ_FIELDS):
        try:
            for key in ('quantity','rate'):
                number(row[key],key)
            row['currency']=currency(row['currency']);row['unit']=unit(row['unit'])
            row['price_date']=price_date(row['price_date'])
            for field in ('included_preliminaries','included_ohp'):
                if field in row:
                    row[field]=flag(row[field],field)
        except ValueError as exc:
            raise ValueError(f'CSV row {row_number}: {exc}') from None
        result.append(row)
    return result


def read_projects(content):
    result=[];seen=set()
    for row_number,row in csv_rows(content,PROJECT_FIELDS):
        try:
            for key in PROJECT_FIELDS:
                if not row[key].strip():
                    raise ValueError(f'{key}: required')
            for key in ('floor_area_m2','budget','actual_cost','base_index','location_index'):
                row[key]=number(row[key],key,positive=True)
            row['currency']=currency(row['currency'])
            price_date(row['price_date'])
            if row['source_type'] not in ('observed','synthetic','illustrative'):
                raise ValueError('source_type: use observed, synthetic or illustrative')
            if row['project_id'] in seen:
                raise ValueError('project_id duplicated')
            seen.add(row['project_id'])
            for key in ('project_id','building_type','region','cost_scope','source_ref'):
                row[key]=text(row[key],key)
            for key in ('index_type','index_series','index_base_year'):
                row[key]=text(row.get(key,'unspecified'),key) or 'unspecified'
        except ValueError as exc:
            raise ValueError(f'CSV row {row_number}: {exc}') from None
        result.append(row)
    return result


def quantile(values,p):
    ordered=sorted(values)
    position=Decimal(len(ordered)-1)*Decimal(str(p))
    lower=int(position);upper=min(lower+1,len(ordered)-1)
    return ordered[lower]+(ordered[upper]-ordered[lower])*(position-lower)


def benchmark(content,filters=None,target_index=100,target_location_index=100):
    filters=filters or {}
    if not isinstance(filters,dict):
        raise ValueError('filters: use an object')
    allowed=('building_type','region','currency','cost_scope','source_type')
    if any(key not in allowed for key in filters):
        raise ValueError('Unsupported benchmark filter')
    target=number(target_index,'target_index',positive=True)
    location=number(target_location_index,'target_location_index',positive=True)
    rows=[row for row in read_projects(content) if all(not value or str(row.get(key))==str(value) for key,value in filters.items())]
    if not rows:
        raise ValueError('No comparable records match the selected filters')
    for key in ('currency','cost_scope','source_type','index_type','index_series','index_base_year'):
        if len({row[key] for row in rows})>1:
            raise ValueError(f'Select a single {key} before benchmarking; mixed records are not comparable')
    prices=[];deviations=[];projects=[];sources={}
    for row in rows:
        normalized=row['actual_cost']/row['floor_area_m2']*target/row['base_index']*location/row['location_index']
        deviation=(row['actual_cost']-row['budget'])/row['budget']*100
        prices.append(normalized);deviations.append(deviation)
        sources[row['source_type']]=sources.get(row['source_type'],0)+1
        projects.append({**{key:str(value) if isinstance(value,Decimal) else value for key,value in row.items()},
                         'project_id':row['project_id'],'normalized_cost_per_m2':output(normalized,2),'cost_deviation_pct':output(deviation),
                         'source_type':row['source_type'],'source_ref':row['source_ref']})
    warnings=[]
    if any(rows[0][key]=='unspecified' for key in ('index_type','index_series','index_base_year')):
        warnings.append('Index basis not fully recorded. Confirm one shared index series/base year and consistent location-index basis before applying this comparison.')
    if rows[0]['source_type']!='observed':
        warnings.append('Illustrative/synthetic records demonstrate the workflow; they are not empirical market estimates or evidence of causal cost drivers.')
    if len(rows)<10:
        warnings.append('Fewer than 10 comparable records; interpret the descriptive range cautiously.')
    if not filters.get('building_type'):
        warnings.append('Multiple building functions may be pooled; select a building type for project benchmarking.')
    if not filters.get('region'):
        warnings.append('Location indexes normalize supplied prices; they do not remove specification, procurement or scope differences.')
    return {'sample_count':len(rows),'currency':rows[0]['currency'],'cost_scope':rows[0]['cost_scope'],'source_counts':sources,
            'median_cost_per_m2':output(quantile(prices,.5),2),'p25_cost_per_m2':output(quantile(prices,.25),2),
            'p75_cost_per_m2':output(quantile(prices,.75),2),'mean_deviation_pct':output(sum(deviations)/len(rows)),
            'over_budget_count':sum(value>0 for value in deviations),'target_index':output(target),'target_location_index':output(location),
            'projects':projects,'warnings':warnings,'quantile_method':'Linear interpolation of ordered values (R7).',
            'index_basis':{key:rows[0][key] for key in ('index_type','index_series','index_base_year')},
            'inputs':{'csv':content,'filters':filters,'target_index':output(target),'target_location_index':output(location)}}


def generate_scenarios(count=500,seed=42):
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=10000:
        raise ValueError('count: integer from 1 to 10000')
    if isinstance(seed,bool) or not isinstance(seed,int):
        raise ValueError('seed: use an integer')
    rng=random.Random(seed);rows=[]
    types=[('housing',1400),('office',2000),('school',1800),('warehouse',1000),('healthcare',2600)]
    regions=[('reference',100),('metro',115),('regional',92),('remote',108)]
    for i in range(count):
        building,base=types[i%len(types)]
        region,location=regions[(i//len(types))%len(regions)]
        area=rng.randint(200,25000)
        price_index=rng.randint(90,145)
        # Arbitrary demonstrator assumptions, not calibrated to actual projects.
        unit_budget=base*(price_index/100)*(location/100)*rng.uniform(.85,1.15)
        budget=round(area*unit_budget,2)
        actual=round(budget*rng.uniform(.88,1.24),2)
        year=2020+i%7;month=1+i%12
        rows.append(dict(project_id=f'SYN-{i+1:04d}',building_type=building,region=region,currency='GBP',floor_area_m2=area,
                         budget=budget,actual_cost=actual,base_index=price_index,location_index=location,cost_scope='building',
                         source_type='synthetic',source_ref=f'scenario-generator-v1-seed-{seed}',price_date=f'{year}-{month:02d}-01',
                         index_type='synthetic',index_series='scenario_reference',index_base_year='reference_100'))
    return rows


def scenario_csv(rows):
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=PROJECT_FIELDS+('index_type','index_series','index_base_year'),lineterminator='\n',restval='unspecified')
    writer.writeheader();writer.writerows(rows)
    return stream.getvalue()
