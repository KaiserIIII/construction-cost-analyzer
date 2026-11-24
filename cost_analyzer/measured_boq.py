"""Take-off, squaring, abstracting and billing with traceable quantities."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP, localcontext
from math import prod

from .engine import capture_inputs, price_boq
from .validation import fixed_number, number, output, text, unit


DIMENSION_COUNT = {'nr': 0, 'm': 1, 'm2': 2, 'm3': 3}
ITEM_KINDS = {'measured', 'pc_sum', 'fixed', 'daywork_rate'}
ITEM_FIELDS = {
    'item_id', 'description', 'element', 'unit', 'kind', 'quantity', 'rate', 'currency',
    'source_ref', 'price_date', 'included_preliminaries', 'included_ohp',
}
PROJECT_FIELDS = {
    'project_name', 'currency', 'preliminaries_pct', 'overheads_profit_pct',
    'contingency_pct', 'fees_pct', 'vat_pct',
}
MEASUREMENT_FIELDS = {
    'measurement_id', 'item_id', 'drawing_ref', 'note', 'timesing', 'dimensions', 'operation',
}


def check_fields(record, allowed, name):
    if not isinstance(record, dict):
        raise ValueError(f'{name}: use an object')
    unknown = record.keys() - allowed
    if unknown:
        raise ValueError(f'{name}: unknown field {min(unknown)}')


def identifier(record, key, name):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name}: {key} is required')
    return text(value, f'{name} {key}', 100)


def decimal_text(value):
    return format(value.normalize(), 'f') if value else '0'


@capture_inputs
def measured_boq(data):
    check_fields(data, {'project', 'quantity_places', 'measurement_standard', 'items', 'measurements'}, 'Measured BoQ')
    settings = data.get('project', {})
    check_fields(settings, PROJECT_FIELDS, 'project')
    places = data.get('quantity_places', 6)
    if type(places) is not int or not 0 <= places <= 6:
        raise ValueError('quantity_places: use an integer from 0 to 6')
    item_rows, dimension_rows = data.get('items'), data.get('measurements')
    for rows, name in ((item_rows, 'items'), (dimension_rows, 'measurements')):
        if not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
            raise ValueError(f'{name}: provide between 1 and 10000 rows')

    items = {}
    for position, row in enumerate(item_rows, 1):
        name = f'Item {position}'
        check_fields(row, ITEM_FIELDS, name)
        item_id = identifier(row, 'item_id', name)
        if item_id in items:
            raise ValueError(f'{name}: item_id is duplicated ({item_id})')
        kind = row.get('kind', 'measured')
        if not isinstance(kind, str) or kind not in ITEM_KINDS:
            raise ValueError(f'{name}: kind must be measured, pc_sum, fixed or daywork_rate')
        if 'quantity' in row and kind in ('measured', 'daywork_rate'):
            raise ValueError(f'{name}: quantity must be omitted for {kind}')
        measure_unit = unit(row.get('unit', 'item'))
        if kind == 'pc_sum' and (measure_unit != 'item' or number(row.get('quantity', 1), 'quantity') != 1):
            raise ValueError(f'{name}: PC sums use unit item and quantity 1')
        if kind == 'measured' and measure_unit not in DIMENSION_COUNT:
            raise ValueError(f'{name}: measured items use m, m2, m3 or nr')
        items[item_id] = {**row, 'item_id': item_id, 'kind': kind, 'unit': measure_unit}

    taking_off, squaring, abstract = [], [], []
    billed, dayworks, rounded_out = [], [], []
    additions, deductions = defaultdict(Decimal), defaultdict(Decimal)
    seen = set()
    # Three six-place dimensions, timesing, and the sum of up to 10,000 lines
    # fit within this context without rounding intermediate quantities.
    rounding_unit = Decimal(1).scaleb(-places)
    with localcontext(prec=64):
        for position, row in enumerate(dimension_rows, 1):
            name = f'Measurement {position}'
            check_fields(row, MEASUREMENT_FIELDS, name)
            measurement_id = identifier(row, 'measurement_id', name)
            item_id = identifier(row, 'item_id', name)
            if measurement_id in seen:
                raise ValueError(f'{name}: measurement_id is duplicated ({measurement_id})')
            if item_id not in items or items[item_id]['kind'] != 'measured':
                raise ValueError(f'{name}: item_id must refer to a measured item ({item_id})')
            seen.add(measurement_id)
            measure_unit = items[item_id]['unit']
            dimensions = row.get('dimensions')
            count = DIMENSION_COUNT[measure_unit]
            if not isinstance(dimensions, list) or len(dimensions) != count:
                raise ValueError(f'{name}: {measure_unit} requires {count} dimensions')
            factors = [
                fixed_number(value, f'{name} dimension {i}', positive=True, maximum=10**6)
                for i, value in enumerate(dimensions, 1)
            ]
            timesing = number(row.get('timesing', 1), f'{name} timesing', positive=True, maximum=10**6)
            if timesing != timesing.to_integral_value():
                raise ValueError(f'{name}: timesing must be a whole number')
            operation = row.get('operation', 'add')
            if operation not in ('add', 'deduct'):
                raise ValueError(f'{name}: operation must be add or deduct')
            drawing_ref = row.get('drawing_ref')
            if not isinstance(drawing_ref, str) or not drawing_ref.strip():
                raise ValueError(f'{name}: drawing_ref is required')
            quantity = timesing * prod(factors)
            deduct = operation == 'deduct'
            (deductions if deduct else additions)[item_id] += quantity
            trace = {'measurement_id': measurement_id, 'item_id': item_id, 'unit': measure_unit}
            taking_off.append({
                **trace, 'drawing_ref': text(drawing_ref, f'{name} drawing_ref'),
                'note': text(row.get('note'), f'{name} note'),
                'timesing': int(timesing), 'dimensions': ' × '.join(map(decimal_text, factors)),
                'operation': operation,
            })
            squaring.append({**trace, 'squared_quantity': decimal_text(-quantity if deduct else quantity)})

        for item_id, item in items.items():
            kind = item['kind']
            if kind == 'daywork_rate':
                dayworks.append({**item, 'quantity': 0})
                continue
            if kind == 'measured':
                if item_id not in additions:
                    raise ValueError(f'{item_id}: a measured item needs at least one addition')
                gross, deduction = additions[item_id], deductions[item_id]
                net = gross - deduction
                if net < 0:
                    raise ValueError(f'{item_id}: deductions exceed added quantities')
                quantity = net.quantize(rounding_unit, rounding=ROUND_HALF_UP)
                if net and not quantity:
                    rounded_out.append(item_id)
                abstract.append({
                    'item_id': item_id, 'unit': item['unit'],
                    'added_quantity': decimal_text(gross), 'deducted_quantity': decimal_text(deduction),
                    'net_quantity': decimal_text(net), 'quantity': output(quantity),
                })
                billed.append({**item, 'quantity': decimal_text(quantity)})
            elif kind == 'pc_sum':
                billed.append({**item, 'quantity': 1})
            else:
                billed.append(item)

    result = price_boq(billed, settings)
    daywork_rates = []
    if dayworks:
        priced_dayworks = price_boq(dayworks, {'currency': result['currency']})
        daywork_rates = [{key: value for key, value in row.items() if key not in ('quantity', 'total')}
                         for row in priced_dayworks['items']]
        result['warnings'].extend(priced_dayworks['warnings'])
    if rounded_out:
        result['warnings'].append('Positive quantities rounded to zero: ' + ', '.join(rounded_out))
    for row in result['items']:
        row['kind'] = items[row['item_id']]['kind']
    result.update(
        measurement_standard=text(data.get('measurement_standard'), 'measurement_standard'),
        quantity_places=places, taking_off=taking_off, squaring=squaring, abstract=abstract,
        daywork_rates=daywork_rates,
    )
    return result
