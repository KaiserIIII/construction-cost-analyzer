# 建筑工程成本分析

[English](README.md) · [MIT 许可证](LICENSE)

使用 Python、pandas 和 Matplotlib 分析建筑项目的成本偏差。仓库包含 18 条项目记录、Jupyter Notebook 和命令行分析脚本，用于观察预算超支及其与项目因素的关联。

## 分析内容

- 对比实际成本与预算，汇总超支比例和成本偏差。
- 按结构类型、地区比较项目差异。
- 计算天气延误、变更单等记录因素与成本偏差的相关性。
- 检查高超支项目并生成图表。

当前数据用于小规模教学案例，数据来源尚不足以证明其代表行业总体。相关性应理解为这些记录内部的关联。

## 运行

```bash
python -m venv .venv
```

激活虚拟环境后执行：

```bash
python -m pip install -r requirements.txt
python analysis/analyzer.py
```

脚本在终端输出报告，并将图表写入 `outputs/`。Notebook 入口：

```bash
jupyter notebook analysis.ipynb
```

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| [analysis.ipynb](analysis.ipynb) | Notebook 分析 |
| [analysis/analyzer.py](analysis/analyzer.py) | 命令行报告与图表 |
| [analysis/chart_generator.py](analysis/chart_generator.py) | 图表生成 |
| [data/construction_projects.csv](data/construction_projects.csv) | 项目记录 |
| [requirements.txt](requirements.txt) | Python 依赖 |

## 结果解释

修改数据后应从 CSV 重新计算汇总结果。当前分析不用于估计因果效应，也未验证预测模型，不能据此直接确定新项目的风险准备金。
