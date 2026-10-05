# Construction Cost Analyzer

[简体中文](README_zh.md) · [MIT License](LICENSE)

An exploratory analysis of construction cost variance using Python, pandas, and Matplotlib. The repository includes an 18-record project dataset, a Jupyter notebook, and command-line scripts for examining budget overruns and related project factors.

## Analysis

- Compare actual cost with budget and summarize overrun frequency.
- Examine variation by structural type and region.
- Calculate correlations with weather delays, change orders, and other recorded factors.
- Inspect high-overrun projects and generate charts.

The included data supports a small educational case study. Its provenance does not establish a representative industry sample; correlations should be interpreted as associations within these records.

## Run

```bash
python -m venv .venv
```

Activate the environment, then:

```bash
python -m pip install -r requirements.txt
python analysis/analyzer.py
```

The script prints an analysis report and writes charts to `outputs/`. To explore the narrative analysis:

```bash
jupyter notebook analysis.ipynb
```

## Repository

| Path | Purpose |
| --- | --- |
| [analysis.ipynb](analysis.ipynb) | Notebook analysis |
| [analysis/analyzer.py](analysis/analyzer.py) | Command-line report and charts |
| [analysis/chart_generator.py](analysis/chart_generator.py) | Chart generation |
| [data/construction_projects.csv](data/construction_projects.csv) | Included project records |
| [requirements.txt](requirements.txt) | Python dependencies |

## Interpretation

Recompute summaries from the CSV when changing data. The analysis does not estimate causal effects, validate a predictive model, or establish a contingency allowance for new projects.
