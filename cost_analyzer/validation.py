"""Shared input boundaries and deterministic decimal arithmetic."""
import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

ZERO = Decimal('0')
ONE = Decimal('1')


def number(value, name, *, minimum=0, positive=False, maximum=10**15):
    if isinstance(value, bool) or value is None:
        raise ValueError(f'{name}: enter a finite number')
    value_text = str(value).strip()
    if len(value_text)>80:
        raise ValueError(f'{name}: number is too long')
    try:
        result = Decimal(value_text)
    except (InvalidOperation, ValueError):
        raise ValueError(f'{name}: enter a finite number') from None
    if not result.is_finite() or result < Decimal(str(minimum)) or result > Decimal(str(maximum)) or (positive and result <= 0):
        raise ValueError(f'{name}: invalid value or outside supported range')
    if len(result.as_tuple().digits)>28 or (result and abs(result)<Decimal('1e-9')):
        raise ValueError(f'{name}: precision outside supported range (28 digits, minimum nonzero 1e-9)')
    return result


def pct(value, name):
    return number(value, name, maximum=100)


def flag(value, name):
    if value in (True, False):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in ('true','false','yes','no','1','0',''):
        return value.strip().lower() in ('true','yes','1')
    raise ValueError(f'{name}: use true or false')


def currency(value='GBP'):
    result = str(value).strip().upper()
    if not re.fullmatch(r'[A-Z]{3}', result):
        raise ValueError('currency: use a three-letter currency code')
    return result


def unit(value='m2'):
    result = str(value).strip().replace('²','2').replace('³','3')
    if result not in ('m','m2','m3','nr','item','h','day','t','kg'):
        raise ValueError('unit: use m, m2, m3, nr, item, h, day, t or kg')
    return result


def price_date(value):
    if value:
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',str(value)):
            raise ValueError('price_date: use YYYY-MM-DD')
        try:
            date.fromisoformat(str(value))
        except ValueError:
            raise ValueError('price_date: use YYYY-MM-DD') from None
    return str(value or '')


def money(value):
    return value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def output(value, places=6):
    rounded=value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    limit=Decimal('1e12') if places<=2 else Decimal('1e9')
    if abs(rounded)>limit:
        raise ValueError('Calculation result outside safe JSON precision (money 1e12, quantities/rates 1e9)')
    result = float(rounded)
    if not math.isfinite(result):
        raise ValueError('Calculation result outside supported range')
    if Decimal(str(result))!=rounded:
        raise ValueError('Calculation result cannot preserve the declared decimal precision')
    return result


def fixed_number(value,name,**kwargs):
    result=number(value,name,**kwargs)
    if result!=result.quantize(Decimal('.000001')):
        raise ValueError(f'{name}: maximum 6 decimal places')
    return result


def text(value, name, limit=2000):
    result=str(value or '').strip()
    if len(result)>limit:
        raise ValueError(f'{name}: maximum {limit} characters')
    return result
