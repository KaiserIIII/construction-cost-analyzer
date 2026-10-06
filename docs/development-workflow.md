# Residential development options / 住宅开发方案估算

Compare housing mixes through an order of cost estimate, monthly financing and development appraisal. Select **Development options / 方案估算**, or run:

```bash
python -m cost_analyzer development examples/development.json --output outputs/development
```

在「方案估算」中输入场地、价格指数、费用与融资条件，按方案录入户型数量、每户 GIFA、原始单价和销售价格。一个方案可以包含多个户型与不同单价。输入可保存为 JSON，结果包含费用基数、月度现金流和敏感性表。[三个方案的示例](../examples/development.json) 使用自编量价与指数假设。

## Inputs / 输入

| Input / 输入 | Basis / 口径 |
| --- | --- |
| `area_m2` per dwelling / 每户面积 | Sum applicable floors under the adopted GIFA measurement boundary; record dimensions and assumptions in `area_source_ref`. Plot area is separate. / 汇总适用楼层面积，记录尺寸与测量边界，场地面积另填。 |
| `count`, `base_rate`, `sale_price` / 数量、单价与售价 | Price each housing type separately with matching cost and sales evidence. / 混合户型分别采用对应的造价与售价。 |
| Price/location indices / 价格与地区指数 | `adjusted_rate = base_rate × target_index/base_index × target_location_index/base_location_index`. Use compatible series and bases. / 保留指数系列、基准、日期与来源。 |
| Embedded preliminaries / 已含现场费 | Reconstruct a net rate by dividing by `1 + embedded_preliminaries_pct/100`; record whether this share is sourced or a proxy. / 拆分比例须有依据或明确作为假设。 |
| Percentages / 比例 | Enter 10 for 10%, not 0.10. Inclusive OH&P rates cannot receive another OH&P allowance. / 填 10 表示 10%，已含总部费与利润不能再次计取。 |

## Cost bases / 费用基数

1. Housing works = adjusted rate × GIFA per dwelling × count, summed across housing types.
2. External works = percentage of housing works; building estimate = housing + external works.
3. Preliminaries = percentage of the building estimate. Site clearance and facilitating works are separate amounts.
4. Contract subtotal = building estimate + site clearance + facilitating works + preliminaries; OH&P = percentage of this subtotal.
5. Works = contract subtotal + OH&P; fees = percentage of works; `K = works + design fees`.
6. Land `L = plot area × land rate`; marketing = `q × GDV`; finance `F` follows the draw schedule.
7. Four separate risks share the selected base; tender and construction inflation apply successively.

本模块先计算工程与设计费，再加入土地、营销和融资。现场费以建筑及外部工程为基数；总部费与利润以包含前期工程和现场费的承包小计为基数。四类风险共用同一基数并分别列示。这是一套明确的计算约定，使用时应与题目或合同核对；基本面积估算和清单工具继续使用其各自记录的附加费顺序。

Let `M = (1 + sum of risk fractions) × (1 + tender inflation) × (1 + construction inflation)`.

- **All-in / 全部开发费用**: `C = M × (K + L + qV + F)`.
- **Works-only / 工程与设计费**: `C = M × K + L + qV + F`.
- **Completion index / 竣工指数**: use a final-period price index and zero both future inflation allowances; combining them is rejected. / 采用竣工指数时，两项未来涨价比例须为零。

## Monthly financing / 月度融资

Programmes run 1–120 months. Preparation spending is distributed equally over preparation months; the remaining works/design spending is distributed equally over construction months. Land is paid at month 0; sales, marketing and principal redemption occur at completion. Loan draws fund the entered share of land and pre-reserve works/design fees. Each draw precedes that month's simple interest (`balance × annual rate / 12`). The arrangement fee is charged on committed principal at month 0; interest, marketing and reserves are equity funded. Interest is not capitalized. Staged sales, lender draw restrictions, exit fees and actual daily lending conventions are outside this schedule.

按准备期和施工期分配支出；每月先提款，再计算当月单利。第 0 月支付土地及贷款安排费，竣工时销售并还本。利息不滚入本金，费用与准备金由权益承担。月度日期按起始日增加月份计算，不能替代银行的日计息规则；借款和工期均由使用者输入。

- **Budget cashflow / 预算现金流** excludes actual financing charges and principal transfers, but retains allocated reserves, including any finance-related reserve component. It is not a funding-independent unlevered valuation.
- **Equity cashflow / 权益现金流** adds borrowing and subtracts interest, fees and repayment; its undiscounted sum equals profit before display rounding.
- **NPV**: `Σ CF_m / (1 + annual discount rate)^(m/12)`, with month 0 added once.
- **IRR**: solve only a single change from outflows to inflows; effective annual return = `(1 + monthly IRR)^12 − 1`. Missing or unsupported roots return `null`.

## Decision and sensitivity / 决策与敏感性

Return on cost is `(GDV − total cost) / total cost` over the entire project, distinct from annual IRR. Only options meeting the entered cost-return hurdle qualify for recommendation, ranked by return on cost. No qualifying option means no viable recommendation. Sensitivity combinations independently vary non-sales costs and sales value, defaulting to nine cases at ±10%; custom axes accept 1–7 unique values each, including zero, from −100% to +100% (up to 49 cases). marketing is recalculated from the changed sales value.

回报门槛按整个项目的总成本利润率判断；亏损最小仍可能不具备可行性。默认九组情景；两轴可分别自定义 1–7 个变动值，须含 0，范围 −100% 至 +100%，最多 49 组。非销售费用与售价分别调整，营销费随售价重算。

With `F = aK×K + aL×L` derived from loan timing, `B=M` for all-in or `B=1` for works-only, marketing fraction `q`, and hurdle `h`:

```text
Non-sales budget N = M×K + B×(L + F)
Break-even GDV = N / (1 − B×q)
Target GDV = N / (1/(1+h) − B×q)
Residual land = [V/(1+h) − B×q×V − K×(M + B×aK)] / [B×(1+aL)]
```

土地余额重算了与地价相关的融资。负余额代表缺口，不构成土地出价。税费、额外工程、售价证据与规划条件须按项目另行确认。

## Reconciliation / 作业核对

Populate settings from the brief and adopted sources; retain geometry assumptions and price references. Compare exported cost bases, dates and financing assumptions with the required method, then review base and sensitivity results. Reproducing arithmetic does not establish source reliability.

先录入题目和采用的资料，再核对费用基数、指数日期、借款时点及回报定义。JSON 保留完整输入，CSV 包含每个方案的费用、融资与敏感性明细，HTML 可独立查看和打印。内部保持十进制精度，到展示时金额才取两位，因此显示行的合计可能有分位差异；清单工具则逐行舍入后汇总。

## Independent option controls / 方案独立参数

Expand **Option settings** and refresh the housing option names. Blank fields inherit common settings; entered zero overrides them. Each option may set its own duration, preparation months/spend, start date, external works, facilitating cost, marketing, loan share, annual interest and arrangement fee. The result records `effective_settings` for each option and total development cost per m² and per dwelling. Programme-dependent interest, NPV, IRR and residual land value use that option's adopted schedule.

展开「各方案独立参数」，刷新住宅 CSV 中的方案名称。空白继承公共值，输入 0 则采用零。工期、准备期与支出、开始日、室外工程、前期工程、营销及贷款条件可分别设置；结果保留各方案实际采用值，每平方米成本采用总开发成本 ÷ GIFA，每户成本采用总开发成本 ÷ 总户数。名称变更后须刷新参数，避免将旧方案条件套入新方案。

Native JSON stores overrides in `options[].settings`. Missing controls inherit; invalid resulting preparation/programme combinations are rejected. `cost_changes_pct` and `value_changes_pct` store the custom sensitivity arrays; a missing axis uses the common sensitivity percentage.

See [the extended original example](../examples/development-extended.json) and [report/export formats](exports.md). 完整的原始输入、方案采用值、来源与全部情景随交付包保存。
