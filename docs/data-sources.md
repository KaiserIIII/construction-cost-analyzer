# Data sources / 数据来源

| Dataset / 数据集 | Coverage / 范围 | Use / 用途 |
| --- | --- | --- |
| `data/indices/ons_construction_opi.csv` | 1,500 monthly index observations; 150 months, 10 series, Jan 2014–Jun 2026 / 1,500 条月度指数记录 | Historic OPI adjustment reference / 历史产出价格调整参考 |
| `data/synthetic_projects.csv` | 500 self-authored scenarios, five functions, four illustrative location levels, seed 42 / 500 个自编模拟情景 | Test imports, filtering, normalization and reports / 练习导入、筛选、归一化与报告 |
| `data/construction_projects.csv` | Original 18 illustrative CNY records / 原有 18 条人民币教学记录 | Compatibility analysis without price-index adjustment / 不调整价格指数的兼容分析 |

## ONS official statistics / ONS 官方统计

Source: [Construction Output Price Indices](https://www.ons.gov.uk/businessindustryandtrade/constructionindustry/datasets/interimconstructionoutputpriceindices), released **13 August 2026**. The source workbook describes Great Britain; the dataset page describes UK. Both labels are retained in the metadata. Indices are not seasonally adjusted, **2015=100**. Repeated aggregate columns across worksheets are checked for equality and deduplicated. Growth-rate columns and quarterly/annual summary rows are excluded.

来源为 2026 年 8 月 13 日发布的 ONS 建筑产出价格指数，未经季节调整，以 2015=100 定基。导入器核对并移除跨工作表重复的汇总值，不把增长率、季度或年度汇总混作月度指数。工作簿与网页的地理范围标签分别保存在元数据中。

Contains public sector information licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Source: Office for National Statistics. Crown copyright 2026. This attribution applies to the index CSV; the repository's software and original examples use MIT.

**OPI is not BCIS Tender Price Index.** It is not a set of individual project costs, current supplier quotations, location factors or a forecast. Apply an appropriate index series to prices with a compatible scope; never combine different series or base years without rebasing. Existing ONS history may be revised, so this repository retains a frozen release and SHA-256 checksums.

**OPI 与 BCIS 投标价格指数不同。** 它不是项目实际造价样本、供应商现时报价、地区系数或未来预测。需选择适用的系列并统一指数基年；不能直接拼接不同定基的数据。

Rebuild the frozen CSV using an existing `openpyxl` environment:

```bash
python -X utf8 scripts/import_ons_opi.py
```

The command checks the reviewed workbook hash before parsing. If ONS changes the current release, it fails rather than accepting changed bytes. Use `--workbook saved-release.xlsx` for a local copy matching the recorded hash. Normal application use reads CSV and requires no XLSX reader.

## Project scenario generation / 项目情景生成

```bash
python -X utf8 scripts/generate_examples.py
python -m cost_analyzer generate --count 500 --seed 42 --output data/synthetic_projects.csv
```

The assumptions and generated CSV checksum are in `data/synthetic_projects.metadata.json`. Base rates, productivity, cost variation, dates and location/price indices are **arbitrary demonstration assumptions**, not fitted to ONS or actual projects. More simulated rows improve workflow coverage; they do not increase empirical estimation accuracy. The original 18 rows have no verified source or consistent cost scope, and remain separately marked `illustrative`.

生成假设和校验值在元数据中完整记录。单价、日期、成本变化和指数均为模拟参数，未依据 ONS 或实际项目校准。增加模拟数量能扩大功能测试覆盖，不能提高实证估价精度。原有 18 条记录保留为独立的教学数据，不并入真实样本。

## Import your own evidence / 导入实际项目记录

Use `examples/project-history-template.csv`. Set `source_type=observed` only for genuine sourced records. Record the actual price date, source reference, currency and consistent cost scope. Include `index_type`, `index_series`, `index_base_year`; the program rejects mixed values when supplied and warns when the basis is unspecified. Normalize the target index to that same series/base year. Align location index bases separately. Use comparable function, specification, contract and procurement conditions; index adjustment alone does not establish comparability.

实际记录应标为 `observed` 并提供可核查的来源、价格日期、币种和统一费用范围。建议完整填写指数类型、系列、基年；程序会拒绝已填写的混合基准，并提示未填写的基准。地区指数也需统一口径。涉及客户或企业资料时，使用适当的内部项目编号，并在本地处理。
