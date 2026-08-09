# Construction Cost Analyzer

> A reproducible Python analysis of the factors associated with construction cost overruns.

[中文说明](README_zh.md) · [License](LICENSE)

## Overview

This project analyzes 18 historical construction projects to identify measurable relationships between cost variance and factors such as change orders, weather delays, structural type, and region. It provides both a narrative Jupyter notebook and a command-line analysis script.

## Key findings

| Finding | Result | Practical interpretation |
|---|---:|---|
| Weather delays show the strongest correlation | `r = +0.891` | Longer delays are associated with larger cost overruns |
| Change orders are a major risk indicator | `r = +0.757` | 90% of projects with more than 12 change orders exceeded budget |
| Frame-shear wall projects had the highest variance | `+6.9%` | This category may require a larger contingency allowance |
| Projects exceeding budget | `55.6%` | The mean cost variance in the sample was `+2.1%` |

> These results describe a small educational dataset and should not be treated as causal estimates or industry-wide benchmarks.

## Repository structure

```text
construction-cost-analyzer/
├── analysis.ipynb                  # Narrative notebook
├── analysis/analyzer.py            # Command-line analysis
├── data/construction_projects.csv  # Source dataset (18 projects)
├── outputs/                         # Generated figures
├── requirements.txt
└── LICENSE
```

## Quick start

### Jupyter Notebook

```bash
python -m pip install -r requirements.txt
jupyter notebook analysis.ipynb
```

### Command line

```bash
python -m pip install -r requirements.txt
python analysis/analyzer.py
```

The script prints a summary report and writes six visualizations to `outputs/`.

## Analysis workflow

1. Clean and validate the project records.
2. Summarize cost variance and over-budget frequency.
3. Compare structural types and regions.
4. Calculate Pearson correlations for six candidate drivers.
5. Group projects by change-order count.
6. Examine the five largest overruns and generate recommendations.

## Tech stack

- Python 3.10+
- pandas and NumPy
- Matplotlib
- Jupyter Notebook

## Roadmap

- [ ] Validate the analysis on a larger public dataset
- [ ] Add predictive modeling with scikit-learn
- [ ] Build an interactive Streamlit dashboard

## License

MIT License. See [LICENSE](LICENSE).
