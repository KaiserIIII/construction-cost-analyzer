# Estimate reports and data exports / 估算报告与数据导出

Calculate the current inputs, then choose a report language and **Excel**, **Delivery ZIP**, **HTML**, **CSV** or **JSON**. All tools use the same export service. Changing an input disables export until the estimate is recalculated.

完成计算后选择报告语言，再导出 Excel、交付包、HTML、CSV 或 JSON。各工具采用同一导出流程；修改输入后须重新计算。报告编号、版本、估算日期、编制人和委托方可在方案估算页面填写，空白字段不补造信息。

Save input JSON at any stage and reload it to continue. Input JSON and housing CSV use local attachment downloads, including in the in-app browser. For benchmark reports, the full original CSV remains in `inputs.json`; printable reports and workbook cells summarize the source instead of placing a large CSV in one cell.

输入尚未填完也可保存 JSON，重新载入后继续。输入 JSON 与住宅 CSV 均通过本地附件下载。同类项目比较会在 `inputs.json` 保留完整原始 CSV；打印报告和工作簿仅展示来源摘要，避免把整份 CSV 塞进单元格。

| File / 文件 | Use / 用途 |
| --- | --- |
| `.xlsx` | Typed schedules with frozen headings, filters, print titles and native number/date formats. Development estimates include Summary, Cost plan, Housing, Cashflow, Sensitivity, Inputs and Checks. / 金额、数量、百分比与日期保留正确类型，提供汇总、费用、户型、现金流、敏感性、输入及核对表。 |
| `.html` | Standalone report with the adopted assumptions and source references, printable on A4 landscape. / 独立报告，保留采用条件与来源，支持 A4 横向打印。 |
| `.csv` | One header and a uniform long table for spreadsheets and downstream analysis. / 单表头、统一列结构，便于导入分析软件。 |
| `.json` | Full result and original input snapshot. / 完整结果与原始输入。 |
| `.zip` | HTML, XLSX, JSON inputs/results, the long CSV, separate record tables and a SHA-256 manifest. / 报告、工作簿、原始输入、结果、长表、分类明细及校验清单。 |

The XLSX is an estimate snapshot. Checks contain real Excel formulas comparing independent detail totals with the reported result. They do not drive the cost model. To change an assumption, edit the saved input in the application and export again. Amounts display two decimal places; rates and quantities retain up to six. Checks state a tolerance for independently rounded values.

Excel 保留估算时点的结果。核对表用公式比较户型面积、建筑成本、借款提取与偿还、权益现金流和利润；核对公式不参与模型计算。调整假设后，应在应用中重新计算并导出。金额显示两位，单价与数量最多六位；核对表列出展示舍入的允许差额。

## CSV schema / CSV 结构

The long CSV uses UTF-8 with BOM when saved or downloaded. Every row has these eight columns:

```text
section,row_id,option_id,field,value,unit,currency,source_ref
```

`option_id` is `O001`, `O002`, etc., following the input order. A `row_id` groups the fields of one detail record. Field names remain stable English identifiers even when the human report is Chinese. Units include `money`, `money/m2`, `money/dwelling`, `m2`, `m3`, `month`, `percent` and `fraction`. The `inputs_json` section retains complete native inputs. CSV percentages use 10 for 10%; XLSX percentage cells store 0.10 with a percentage format. Genuine negative numbers remain numeric; formula-like text is escaped for spreadsheet import.

方案编号按输入顺序生成，行编号关联同一明细的各字段。中文报告不会改变机器字段名。比例在 CSV/JSON 中用 0–100 表示，在 Excel 中采用原生百分比值。ZIP 中的 `tables/*.csv` 各自保留单一、固定的表头：住宅、费用、现金流、敏感性、来源等按记录分表，完整保留全部行。

The ZIP manifest specifies schema version, language, reporting units, calculation and rounding basis, adopted report metadata, and the byte length and SHA-256 of every other member. Identical input snapshots and export language produce the same package bytes. No macros or external workbook links are generated.

交付包清单记录结构版本、语言、单位、算法和舍入口径，以及各文件大小和 SHA-256。可据此检查文件是否缺失或被修改。浏览器附件在本地内存中短期保留，默认十分钟过期；较多新导出可能提前替换旧附件。过期后重新导出即可。

## CLI / 命令行

```bash
python -m cost_analyzer development examples/development-extended.json --output outputs/development --language bilingual
python -m cost_analyzer estimate examples/early-estimate.json --output outputs/estimate --language en
```

`--language` accepts `zh`, `en` or `bilingual` on all report commands and the demo. No extra package is required to write XLSX or ZIP.

## Reporting basis / 编制口径

The schedules make cost bases, timing, risk allowances and sources explicit. [RICS Cost Reporting](https://www.rics.org/profession-standards/rics-standards-and-guidance/sector-standards/construction-standards/black-book/cost-reporting) discusses reporting purpose, models, budgets and variable costs. [RICS NRM](https://www.rics.org/profession-standards/rics-standards-and-guidance/sector-standards/construction-standards/nrm) provides measurement and cost-planning guidance. These are references for reviewing project requirements; this configurable course-method calculation is not an NRM compliance certification. XLSX uses the [ECMA Office Open XML format](https://ecma-international.org/technical-committees/tc45/).

采用课程或项目要求的费用顺序和基数，并在报告中记录。实际应用时，应核对所需计量规则、合同范围、报价价格日期和税费；格式完整不能替代资料的可靠性。未来价格指数、已含现场费的拆分比例和销售价格证据尤其需要说明采用依据。
