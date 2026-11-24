# Measured BOQ / 计量到清单

Use **Measured BOQ** in the browser or run the example from the repository root.

```bash
python -m cost_analyzer measured-boq examples/measured-boq.json --output outputs/measured-boq
```

The editable JSON contains `project`, `items`, and `measurements`. Record the applicable measurement rules and edition in `measurement_standard`. Use the project's required number of decimal places in `quantity_places` (0–6, default 6).

网页选择「计量到清单」，可载入示例或上传输入 JSON。输入按项目、清单项和计量记录组织。可在 `measurement_standard` 写明采用的规则及版本，在 `quantity_places` 设置清单量小数位数。

| Stage / 工序 | Record / 记录 |
| --- | --- |
| Taking off / 计量 | Give each measurement a unique `measurement_id` and link it to an `item_id`. Enter the drawing, revision, detail or assumption reference in `drawing_ref`. Add the calculation basis or query reference in `note`. |
| Squaring / 列式计算 | Enter dimensions in metres, up to six decimal places. Use one, two or three dimensions for `m`, `m2` or `m3`. For `nr`, use an empty dimension array and put the count in `timesing`. `timesing` defaults to 1 and must be a positive whole number. Mark deductions with `operation: "deduct"`. |
| Abstracting / 汇总 | The same bill item may have several additions and deductions. The workflow retains the exact decimal products and subtracts deductions before rounding the combined quantity half up. |
| Billing / 清单计价 | Enter the description, unit rate, source and price date for each bill item. Measured quantities come from the abstract. The bill rounds each extended amount to two decimal places before summing. |

Items default to `kind: "measured"`. For a supplied quantity with no dimension lines, use `kind: "fixed"` and enter `quantity`. For a prime cost sum, use `kind: "pc_sum"`, unit `item`, and the sum as the rate. Its quantity is one. For a rates-only daywork schedule, use `kind: "daywork_rate"` and omit quantity. To price a daywork allowance, use a separate fixed line with an explicit basis.

实测项目由汇总表供量。已给定的数量可用 `fixed`，指定暂定金额用 `pc_sum`。`daywork_rate` 单独列出计日工费率，如需计入预算，可另建一条注明依据的固定清单项。

The shared BOQ engine applies the entered preliminaries percentage to priced items, OH&P to priced items plus preliminaries, and contingency after OH&P. Prime cost and fixed items are part of that base. Check the required allowance bases, scope overlaps, deduction rules and tender treatment for the specific project.

In the example, two strips give 2 × 4.2 × 0.6 × 0.3 = 1.512 m³. A junction deduction of 0.072 m³ leaves 1.440 m³. At £120.50/m³ the bill amount is £173.52. The £100 PC sum brings the subtotal to £273.52. OH&P is £54.70 and contingency is £22.98, giving **£351.20**. The example uses invented arithmetic inputs.

The Excel export preserves exact unrounded quantities as text and billed quantities as numbers. **Checks** compares the rounded abstract with the bill and recalculates line amounts. Edit the saved JSON and re-export to change the estimate. The accompanying CSV and HTML retain the same item IDs and reference records.
