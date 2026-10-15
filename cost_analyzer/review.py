"""Local documentation preflight; not an independent audit or source verification."""
import hashlib
import json
from decimal import Decimal
from .development import development


EXPLICIT_FIELDS = (
    'land_rate', 'site_clearance_rate', 'facilitating_cost', 'external_works_pct',
    'preliminaries_pct', 'overheads_profit_pct', 'fees_pct', 'marketing_pct',
    'risk_design_pct', 'risk_construction_pct', 'risk_employer_change_pct', 'risk_other_pct',
    'tender_inflation_pct', 'construction_inflation_pct', 'duration_months',
    'prep_months', 'prep_spend_pct', 'loan_share_pct', 'start_date',
    'rate_includes_preliminaries', 'rate_includes_ohp', 'price_basis', 'risk_scope',
    'base_index', 'target_index', 'base_location_index', 'target_location_index',
    'hurdle_pct', 'discount_rate_pct', 'currency',
)
LIMITS = (
    'Checks recorded inputs and arithmetic validation only; references are not opened or verified. '
    'Documented does not mean submission-ready, market-verified or NRM-certified. '
    'The review does not verify drawings, tax, specialist scope or lending approval. / '
    '仅检查输入记录和数值有效性，不访问或核实引用内容。资料已记录不等于可提交、市场价格已验证或符合 NRM。'
    '本检查不核实图纸、税费、专业工程范围或贷款审批。'
)


def review_development(data):
    """Return repeatable issues with native JSON paths and affected option IDs."""
    issues = []
    programmes = []
    digest = None

    def issue(code, path, message, severity='error', option_id=''):
        issues.append({'code': code, 'severity': severity, 'path': path,
                       'option_id': option_id, 'message': message})

    def result(status):
        return {'type': 'development_input_review', 'status': status,
                'input_sha256': digest, 'error_count': sum(i['severity'] == 'error' for i in issues),
                'warning_count': sum(i['severity'] == 'warning' for i in issues),
                'issues': issues, 'programmes': programmes, 'limitations': LIMITS}

    try:
        canonical = json.dumps(data, ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False).encode('utf-8')
        digest = hashlib.sha256(canonical).hexdigest()
        calculated = development(data)
    except (ValueError, TypeError, RecursionError) as exc:
        issue('invalid_input', '', str(exc))
        return result('invalid')

    def required_text(value, path, option_id=''):
        if not str(value or '').strip():
            issue('missing_evidence', path,
                  'Record the adopted reference or date. / 请记录采用的依据或日期。', option_id=option_id)

    for key in ('price_date', 'estimate_date', 'index_source_ref'):
        required_text(data.get(key), key)

    if data.get('price_date') and data.get('estimate_date') and data['price_date'] > data['estimate_date']:
        issue('evidence_after_estimate', 'price_date',
              'Rate date is after the estimate date; explain the valuation basis. / 单价日期晚于估算日期，需解释估值口径。',
              'warning')

    for index, (raw, adopted) in enumerate(zip(data['options'], calculated['options'])):
        oid = f'O{index + 1:03d}'
        overrides = raw.get('settings', {})
        effective = {**data, **overrides}

        def setting_path(key):
            return f'options[{index}].settings.{key}' if key in overrides else key

        required = list(EXPLICIT_FIELDS)
        if Decimal(str(effective.get('loan_share_pct', 0))) > 0:
            required += ['loan_interest_pct', 'loan_fee_pct']
        for key in required:
            if key not in effective or effective[key] is None or effective[key] == '':
                issue('missing_explicit_input', setting_path(key),
                      'Set this input explicitly; use zero only when intentional. / 请明确填写；仅在确定为零时填零。',
                      option_id=oid)

        if Decimal(str(effective.get('embedded_preliminaries_pct', 0))) > 0:
            issue('embedded_preliminaries_proxy', 'embedded_preliminaries_pct',
                  'Confirm the embedded percentage and its base; reconstruction may be a proxy. / 核对已含现场费比例及基数，拆分可能属于近似假设。',
                  'warning', oid)

        dates = adopted['cashflows']
        programmes.append({'option_id': oid, 'name': adopted['name'],
                           'start_date': dates[0]['date'], 'completion_date': dates[-1]['date'],
                           'duration_months': adopted['effective_settings']['duration_months']})
        for position, unit in enumerate(raw['units']):
            prefix = f'options[{index}].units[{position}]'
            required_text(unit.get('area_source_ref'), prefix + '.area_source_ref', oid)
            required_text(unit.get('source_ref') or data.get('source_ref'),
                          prefix + '.source_ref' if unit.get('source_ref') else 'source_ref', oid)
            for key in ('sale_source_ref', 'sale_price_date', 'sale_basis'):
                required_text(unit.get(key), prefix + '.' + key, oid)
            if Decimal(str(unit['sale_price'])) <= 0:
                issue('zero_sales_value', prefix + '.sale_price',
                      'A zero selling price is not evidence of market value. / 零售价不能作为市场价值依据。', option_id=oid)
            if unit.get('sale_basis') in ('asking', 'assumed'):
                issue('sales_basis', prefix + '.sale_basis',
                      'Asking or assumed prices need comparison and justification; they are not completed sales. / 挂牌价或假设价需比较和论证，不是成交价。',
                      'warning', oid)
            if unit.get('sale_price_date') and data.get('estimate_date') and unit['sale_price_date'] > data['estimate_date']:
                issue('evidence_after_estimate', prefix + '.sale_price_date',
                      'Sales evidence is dated after the estimate; explain the valuation basis. / 售价证据晚于估算日期，需解释估值口径。',
                      'warning', oid)

    status = 'incomplete' if any(i['severity'] == 'error' for i in issues) else 'review_required' if issues else 'documented'
    return result(status)
