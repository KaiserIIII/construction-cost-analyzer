# Development input review / 开发估算输入检查

```bash
python -m cost_analyzer review examples/development-review.json
python -m cost_analyzer review my-development.json --output outputs/input-review.json
```

The review runs locally using the standard library. It does not open references or upload inputs. It supplements the development calculator; existing `development` commands retain their numerical behavior and defaults.

The output path must differ from the input path; the command rejects overwriting the original input with its review.

检查在本地完成，不访问引用内容，也不上传输入。它是计算之外的资料检查；原有 `development` 计算入口和默认值保持兼容。计算成功不代表输入完整。浏览器保存输入时会包含表单当前采用的默认值；本检查不能判断这些值是否经过使用者确认。

## Read the result / 阅读结果

| Status | Meaning / 含义 | Exit |
| --- | --- | --- |
| `invalid` | The existing engine rejected a numeric value, date, field or structure. / 输入未通过计算引擎校验。 | 2 |
| `incomplete` | Arithmetic can run, but a required declaration/reference is missing or a selling price is zero. / 可计算，但声明或依据缺项，或售价为零。 | 1 |
| `review_required` | Listed inputs are recorded, but a stated assumption or date needs review. / 已记录，仍有需核对的假设或日期。 | 0 |
| `documented` | The listed fields are present and no configured warning applies. This does not verify their contents. / 指定字段已记录，未触发本检查中的警告；不表示内容已验证。 | 0 |

Automation must read `status` and `warning_count`; exit 0 does not mean there are no warnings. `issues` contains a stable code, severity, JSON field path and affected option ID. A path refers to the input snapshot. An inherited missing setting points to the common field; an explicitly overridden setting points to `options[index].settings.field`. A missing common field may affect several options.

自动化程序应同时读取状态与警告数量。字段路径定位原始输入；公共参数缺失可能同时影响多个方案。`programmes` records the engine's monthly start and completion dates, including option overrides. These dates do not establish whether the programme is achievable. `input_sha256` hashes canonical UTF-8 JSON with sorted object keys, so input changes can be identified; it does not hash the external evidence. No timestamp or online source check is implied.

## What is checked / 检查范围

- Land, clearance, facilitating works, external works, preliminaries, OH&P, professional fees, marketing, four risk percentages and both inflation allowances must be explicitly entered. Use zero only for an intentional exclusion or zero assumption, and explain material exclusions in the report.
- Programme, loan share, pricing/risk bases, price/location indices, hurdle and discount rates must be explicit. A positive loan share also requires interest and arrangement fee inputs. Option overrides are respected.
- Rate inclusion flags must be explicit. Existing engine checks still reject incompatible embedded costs or future inflation applied to a completion index.
- Area and construction-rate references, index reference, cost date and estimate date must be recorded. Each housing type must have a separate sales reference, date and basis.
- Asking/assumed sales evidence, evidence dated after the estimate, and reconstruction of embedded preliminaries produce warnings. An asking price is not a completed transaction. The tool cannot judge comparability or whether a claimed sold record is authentic.

这些要求用于防止缺项被默认值掩盖，不构成通用计量规则。税务、规划、融资批准、污染治理、图纸面积和售价可比性仍须由使用者核对。

## Sales metadata / 售价记录

```json
{
  "sale_source_ref": "Local comparable reference and adoption rationale",
  "sale_price_date": "2026-09-01",
  "sale_basis": "asking"
}
```

These optional fields belong in each `options[].units[]` row. Legacy eight-column housing CSV files remain accepted. Add any of `sale_source_ref,sale_price_date,sale_basis` after the existing columns when needed; duplicate or unrecognised columns are rejected. A loaded input with these fields retains them in saved housing CSV, result JSON, XLSX, HTML and ZIP tables.

`examples/development-review.json` is self-authored synthetic data, including assumed selling prices. Its warning is intentional; it is not a market appraisal. No personal submission or project answers are bundled.
