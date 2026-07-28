# 🏗️ Construction Cost Analyzer

> **建筑工程成本超支驱动因素分析** — 从数据中找出成本失控的真正原因

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

---

## 📌 项目概述 / Overview

建筑施工项目超预算是一个全球性问题——但大多数时候，人们把它归结为模糊的"市场波动"或"不可抗力"。

**这个项目不满足于模糊解释。** 我用 18 个工程项目的历史数据，通过统计分析和可视化，揭示了成本超支的**具体驱动因素**，并发现了变更单数量、天气延误、结构类型等因素与成本偏差之间的量化关系。

> Construction cost overruns are a global problem — but most explanations stop at vague "market fluctuations." This project goes deeper: using 18 project records, I ran statistical analysis and visualizations to uncover *which specific factors* drive budgets off track, and to what degree.

---

## 🔑 核心发现 / Key Findings

| 发现 | 数据 | 含义 |
|------|------|------|
| 🎯 **变更单是第一杀手** | r = +0.757 | 变更单 >12 的项目 90% 超预算 |
| 🌧️ **天气延误极强相关** | r = +0.891 | 每多延误 1 天，成本按比例攀升 |
| 🏢 **框剪结构风险最高** | 偏差率 +6.9% | 预留更大风险储备金 |
| 📊 **55.6% 项目超预算** | 均值偏差 2.1% | 行业普遍现象，但可控 |

---

## 📂 项目结构 / Project Structure

```
construction-cost-analyzer/
│
├── 📓 analysis.ipynb              ← Jupyter Notebook（推荐入口，含完整叙事）
├── 📜 analysis/analyzer.py         ← Python 脚本版（快速跑出结果）
├── 📊 data/construction_projects.csv ← 18 个项目的历史数据
├── 📈 outputs/                     ← 生成的图表
├── 📄 README.md                    ← 你正在看的
├── 📄 requirements.txt             ← 依赖清单
├── 📄 .gitignore
└── 📜 LICENSE                      ← MIT
```

---

## 🚀 快速开始 / Quick Start

### 方式一：Jupyter Notebook（推荐）

```bash
pip install -r requirements.txt
jupyter notebook analysis.ipynb
```

Notebook 里有完整的**数据叙事**——从问题定义 → 数据清洗 → 探索性分析 → 统计建模 → 结论建议，每一步都有讲解。

### 方式二：命令行直接跑

```bash
pip install -r requirements.txt
python analysis/analyzer.py
```

终端输出分析报告 + `outputs/` 里生成 6 张可视化图表。

---

## 📊 分析流程 / Analysis Pipeline

```
[数据清洗] → [描述性统计] → [按结构/地区分组对比]
                                ↓
[结论建议] ← [变更单分级分析] ← [Pearson 相关性矩阵]
```

### 分析维度

1. **整体概况**：样本均值、超预算比例、成本偏差分布
2. **结构类型对比**：框剪 vs 框架 vs 钢结构 vs 砖混 — 谁的偏差最大？
3. **地区差异**：华东/华北/华南/西南 — 哪些地区需要额外天气储备金？
4. **相关性矩阵**：6 个驱动因素与成本偏差的 Pearson r
5. **变更单分级**：低(0-5) / 中(6-12) / 高(13+) — 每档的超预算比例
6. **TOP5 深度分析**：最严重超预算项目的多维拆解

---

## 💻 技术栈 / Tech Stack

| 工具 | 用途 |
|------|------|
| **pandas** | 数据处理、分组聚合、描述性统计 |
| **matplotlib** | 6 张可视化图表，打造分析 dashboard |
| **numpy** | Pearson 相关系数、多项式拟合 |
| **Jupyter Notebook** | 交互式数据叙事 |

---

## 🎯 为什么做这个项目 / Why I Built This

我是工程管理专业的学生，学过 BIM、数据分析、Python 编程和建筑工程管理。这个项目的价值在于**它坐落在两个领域的交叉点**：

- **领域知识**：我理解变更单流程、结构类型差异、地区施工特点
- **技术能力**：我用 Python 把这个"感觉"变成了可量化的数字

出国留学申请文书里，这个项目回答了一个关键问题：**"为什么一个工程管理的学生要学计算机/数据科学？"** —— 因为传统工程管理依靠经验，而数据驱动的工程管理需要编程能力。

> I'm an Engineering Management student who learned BIM, data analysis, and Python. This project sits at the intersection: domain knowledge (construction) × technical skills (data science). It's my answer to the question "Why does an EM student want to study CS?" — because data-driven construction management needs programming.

---

## 🔮 未来计划 / Roadmap

- [ ] 引入真实公开数据集（如中国工程造价信息网）
- [ ] 加入机器学习模型预测超预算概率（scikit-learn）
- [ ] Streamlit 交互式 Dashboard
- [ ] 英文版报告（用于海外申请材料）

---

## 📜 License

MIT © 2026

---

*如果你觉得有用，给个 ⭐ Star 吧！*
