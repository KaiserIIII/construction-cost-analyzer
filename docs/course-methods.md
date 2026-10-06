# Course methods / 课程方法

The toolkit turns the methods from **Construction Quantification and Costing** into explicit, reviewable calculations. It uses original examples and user-supplied rates. The course references explain the methods; the software does not reproduce licensed price-book tables or claim full automated compliance with every measurement rule.

本工具把 Construction Quantification and Costing 课程中的方法实现为可以逐步复核的计算。示例为自编，实际单价由用户录入；计量方法和具体工程描述仍需结合项目采用的规则判断。

| Course topic / 课程主题 | Tool / 工具 | Calculation and boundary / 计算与适用条件 |
| --- | --- | --- |
| Design economics; building cost estimating / 设计经济、早期估价 | Early estimate / 初步估算 | GIFA × adjusted works rate; explicit time, location and quality factors / 总内部楼面面积乘调整后本体单价 |
| Measurement; NRM 2 / 计量与 NRM 2 | Net takeoff / 净工程量 | Rectangle, volume, length, count; explicit deductions / 面积、体积、长度、个数与明确扣减 |
| Substructure centreline / 基础中心线 | Strip foundation / 条形基础 | External rectangle dimensions to centreline; natural excavation, concrete, displaced volume and backfill / 外部尺寸转中心线，自然挖方、混凝土与回填 |
| Labour, material and plant / 人材机 | Unit rates / 单价分析 | Whole-crew hourly cost ÷ output; purchase-unit conversion; material-specific waste / 班组小时费用除产量、材料包装换算与分项损耗 |
| Pricing a BoQ / 清单计价 | CSV bill / CSV 清单 | Net quantity × rate; line rounding, element totals, embedded-cost checks / 净量乘单价、逐行取整、分部汇总与包含项检查 |
| Development appraisal / 开发评价 | Cashflows and residual land / 现金流与土地剩余法 | NPV, conventional IRR, simple/discounted payback, distinct profit bases / NPV、常规 IRR、回收期及利润基数 |

## Cost bases and rounding / 费用基数与取整

1. Direct works: line quantities × rates; round each line to 2 decimals before summing.
2. Preliminaries: percentage of direct works.
3. OH&P: percentage of direct works plus preliminaries.
4. Contingency: percentage of the subtotal above.
5. Fees: percentage of that subtotal plus contingency.
6. VAT: percentage of the cost including fees.

附加费基数是本工具明确采用的一套计算约定，报告逐项显示；它不是所有合同的通用收费规则。若合同采用其他基数，应拆成清单项或另行核算。税率由用户填入，默认为零，不提供税务判断。历史单价或任一清单项已含现场费、总部费或利润时，不能对其再次套用相应全局比例。

Base rates and BOQ quantities/rates accept at most 6 decimals. Adjusted early-estimate rates are rounded to 6 decimals before multiplying by area; monetary line/allowance values use decimal arithmetic and `ROUND_HALF_UP` to 2 decimals. JSON numeric outputs are checked to retain that declared precision: money up to 1e12; quantities/rates and other 6-decimal outputs up to 1e9. Larger results fail with an explicit error.

原始单价与清单量价最多支持 6 位小数。面积法的调整单价先取 6 位再乘面积，金额和附加费按十进制四舍五入取 2 位。金额最大支持 1e12，量价等 6 位输出最大支持 1e9，以保证导出的 JSON 数字不丢失所声明的精度。

## Geometry and productivity / 几何与生产率

Rectangular centreline length is `2 × (external length + external width − 2 × wall thickness)`. The foundation helper assumes a continuous rectangular strip of uniform section. Junctions, working space, support, soil bulking, disposal and other structures are separate items. Backfill is natural trench volume minus concrete and user-entered displaced volume. Material waste changes consumption in the rate, not the net BOQ quantity. Small-opening exemptions and item-specific NRM deductions are not inferred automatically.

中心线公式适用于均匀墙厚的矩形外围。基础助手假定连续矩形条基与均匀截面，不自动处理交接、工作空间、支护、土方膨胀和弃土。回填为自然沟槽体积减混凝土及另填的占用体积。材料损耗进入单价，不放大净清单量；具体项目的扣减和描述需按所采用的计量规则确定。

## Financial conventions / 财务约定

The separate [residential development workflow](development-workflow.md) supports multi-option OCEs and monthly staged financing. Its fees precede risk allowances, with selectable reserve scope. Monthly NPV, annualized IRR, finance-aware residuals and sales-dependent marketing are described there. / [住宅开发估算](development-workflow.md) 支持多方案 OCE 和月度分期融资，设计费先于风险准备计取，可选择准备金范围；其月度现金流及费用基数与下列年度评价工具分别记录。

Cashflow 0 occurs now; subsequent flows occur at annual period ends. Payback interpolates within the recovery period, so its convention differs from strict year-end receipts. IRR is reported only for an initial outflow followed by nonnegative flows with a root inside the supported range; otherwise it returns `null` with a reason. Residual land value is `GDV × (1−profit margin) − non-land cost` for a GDV-based target, or `GDV/(1+cost markup) − non-land cost` for profit on total development cost including land. Finance, taxes and transaction costs must already be included in the supplied non-land cost or cashflows.

第 0 期为现在，其后现金流按年末折现。回收期采用回收期间内的线性插值；严格只在年末收款时不能直接使用该小数年份。IRR 仅报告初始支出、随后非负流入的常规单根，其他情况明确返回不可用。利润按 GDV 或按含土地的总开发成本计取时采用不同剩余法公式；融资、税费和交易成本须已进入输入。

References / 参考： [RICS NRM](https://www.rics.org/profession-standards/rics-standards-and-guidance/sector-standards/construction-standards/nrm), [ONS Construction OPI](https://www.ons.gov.uk/businessindustryandtrade/constructionindustry/datasets/interimconstructionoutputpriceindices). Course topics reviewed: Building cost estimating, Design economics, Intro to measurement, NRM 2, Intro to Unit Rate Estimating, Labour/Material/Plant components, Development Appraisal.
