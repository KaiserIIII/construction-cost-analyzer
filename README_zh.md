# Construction Cost Analyzer · 建筑计量计价工具

[English](README.md) · [计算方法](docs/course-methods.md) · [数据来源](docs/data-sources.md) · [MIT 许可证](LICENSE)

用于工程量计算、工料机单价分析、工程量清单计价、指数调整估算和开发投资评价的本地工具。计算方法结合 **Construction Quantification and Costing（建筑计量与计价）** 课程内容。

中英文浏览器工作区与 Python 命令行共用计算引擎。导出结果保留输入、报价来源、价格日期和费用基数，便于在电子表格中核对、修改和继续使用。

![计量计价与开发评价工作区](docs/images/workspace.jpg)

## 启动工作区

需要 **Python 3.10 或以上版本**。应用、命令行和核心测试只使用标准库，无需安装第三方包。

```bash
python -m cost_analyzer serve
```

打开 **http://127.0.0.1:8765/**。Windows 下也可双击 `start.cmd`。点击「载入教学示例」，修改参数后计算；页面右上角可切换中文与英文。服务仅监听本机回环地址，文件在本地处理。

## 从计量到估价

| 阶段 | 计算与输出 |
| --- | --- |
| 初步估算 | 建筑面积 × 历史单价，分别调整价格、地区和质量系数；列示现场费用、总部费与利润、风险准备、顾问费和增值税。 |
| 工程量计算 | 面积、体积、长度、个数与矩形中心线计量；连续条形基础分别计算开挖、混凝土和自然回填。 |
| 工料机组价 | 材料包装价格换算、材料损耗、整个班组的生产率、机械产量、分包费用和加价；报价单价可带入清单条目。 |
| 清单计价 | 导入 CSV 或在页面添加条目，计算逐项金额、分部汇总和项目附加费用；已含费用标记防止重复计取现场费用或总部费与利润。 |
| 同类项目比较 | 按建筑用途、地区、币种、费用范围和来源类型筛选，统一适用的价格与地区指数，比较中位数、四分位数及预算偏差。 |
| 开发投资评价 | 年度期末现金流、净现值、常规现金流内部收益率、简单与折现回收期，以及按销售额或总成本利润率计算的土地剩余价值。 |

输入可保存为 JSON 并重新载入，结果可导出 JSON、CSV 或打印。命令行还会生成独立 HTML 报告。修改输入后，原结果会提示重新计算，并暂停导出。

## 数据与实际项目导入

- **1,500 条 ONS 官方指数记录**：10 个建筑产出价格指数系列，覆盖 2014 年 1 月至 2026 年 6 月的 150 个月，固定使用 2026 年 8 月 13 日发布的数据。初步估算页面支持选择原始与目标价格月份；CSV 配有来源、发布信息和校验值。
- **500 个可复现项目情景**：覆盖 5 类建筑用途和 4 类示例地区，随机种子为 42。数据标为 `synthetic`，其中单价、日期和指数假设未经实际市场校准。
- **实际项目历史记录**：使用 [CSV 模板](examples/project-history-template.csv) 导入有来源的 `observed` 记录，统一币种、费用范围、指数系列和基年。原有 18 条教学记录通过兼容分析脚本单独保留。

ONS OPI 是建筑产出价格指数，与 BCIS 投标价格指数不同，不提供供应商报价、地区系数或未来预测。1,500 条记录是价格指数观测值，并非已完工项目。详见 [数据来源与许可](docs/data-sources.md)。

## 手算示例与命令行

[examples](examples/) 中的单价均为自编算例。用于实际项目时，应替换为项目报价和实测工程量。

| 示例 | 可核对的结果 |
| --- | --- |
| 面积 1,000 m²，原始单价 £1,000/m²，价格系数 1.20、地区系数 1.05，现场费 10%、总部费与利润 5% | 合计 £1,455,300 |
| 外尺寸 10 m × 8 m，墙厚 0.30 m，沟槽 0.80 m × 1.20 m，混凝土 0.60 m × 0.30 m | 中心线 34.8 m；开挖 33.408 m³；混凝土 6.264 m³；自然回填 27.144 m³ |
| 砖与砂浆 £33.12/m²，班组 £48/h、产量 2 m²/h，加价 10% | 直接单价 £57.12/m²；报价单价 £62.832/m² |

```bash
python -m cost_analyzer demo --output outputs/demo
python -m cost_analyzer estimate examples/early-estimate.json --output outputs/estimate
python -m cost_analyzer boq --input examples/boq.csv --project examples/project.json --output outputs/boq
python -m cost_analyzer benchmark --input data/synthetic_projects.csv --building-type office --currency GBP --source-type synthetic --output outputs/benchmark
python -m cost_analyzer appraise examples/appraisal.json --output outputs/appraisal
```

各输出目录包含 JSON、UTF-8 CSV 和 HTML 文件。运行 `python -m cost_analyzer --help` 或在子命令后加 `--help` 可查看参数。

## 计量与费用口径

工具对应课程中的设计经济性、早期估算、中心线计量、工料机组价与开发评价。[计算方法说明](docs/course-methods.md) 列出公式、附加费用基数、舍入规则和计量边界。

净工程量与材料损耗分别计算。矩形连续条形基础之外的交接、工作面、支护、松胀和弃土，应按项目要求另列条目。附加费用和增值税比例由使用者输入；税务处理和合同计量规则需依据具体项目确定。

金额使用十进制运算，按四舍五入保留两位小数。清单工程量和单价最多保留六位小数，逐项金额先舍入再汇总。比较项目时，已填写的混合币种、费用范围、来源类型或指数基准须先筛选或统一。存在多次正负变化的非常规现金流仍计算净现值，但不返回可能存在歧义的内部收益率。

## 开发与验证

```bash
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/generate_examples.py
```

测试覆盖手算结果、舍入与数值范围、重复费用、异常 CSV/JSON、指数可比性、报告转义、命令行以及实际本地 HTTP 接口。安装了 Node.js 时还会检查浏览器工具函数。可选 XLSX 导入器的样本测试需要已有 `openpyxl` 环境；日常使用直接读取固定 CSV。CI 在 Windows、Linux 和 Python 3.10–3.13 上运行核心测试。

[analysis.ipynb](analysis.ipynb) 提供可重跑的操作示例。可选图表使用 [requirements.txt](requirements.txt) 中的已测试版本：

```bash
python analysis/chart_generator.py
```

| 路径 | 内容 |
| --- | --- |
| [cost_analyzer](cost_analyzer/) | 计算引擎、命令行、本地服务与双语页面 |
| [examples](examples/) | 算例输入、清单 CSV 和项目历史模板 |
| [data/indices](data/indices/) | ONS 官方数据快照、来源信息和校验值 |
| [scripts/import_ons_opi.py](scripts/import_ons_opi.py) | 校验原始文件后导入已核对的 ONS 发布数据 |
| [tests](tests/) | 计算、数据与接口回归测试 |
| [analysis/analyzer.py](analysis/analyzer.py) | 原有 18 条教学记录的独立兼容报告 |

软件和自编示例使用 MIT 许可证。ONS 指数按 [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) 标明来源并使用。CI 引用与可选包版本记录在 [工具链说明](docs/toolchain.md) 中。
