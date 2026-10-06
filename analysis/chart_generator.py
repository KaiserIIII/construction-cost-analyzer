#!/usr/bin/env python3
"""Optional descriptive charts for the labeled 500-case demonstration set."""
import csv
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from cost_analyzer.benchmarks import benchmark
    content=(ROOT/'data/synthetic_projects.csv').read_text(encoding='utf-8')
    result=benchmark(content,{'currency':'GBP','cost_scope':'building'},100,100)
    rows=list(csv.DictReader(content.splitlines()))
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    axes[0].hist([row['cost_deviation_pct'] for row in result['projects']],bins=20,color='#23646c',edgecolor='white')
    axes[0].set(xlabel='Cost deviation (%)',ylabel='Scenario count',title='Budget vs actual: synthetic assumptions')
    axes[0].axvline(0,color='#bb7a28',linewidth=1.5)
    groups=sorted({row['building_type'] for row in rows})
    values=[[row['normalized_cost_per_m2'] for row,source in zip(result['projects'],rows) if source['building_type']==group] for group in groups]
    axes[1].boxplot(values,showfliers=True)
    axes[1].set_xticks(range(1,len(groups)+1),groups)
    axes[1].set(xlabel='Building function',ylabel='Normalized GBP / m2',title='Descriptive distributions by function')
    axes[1].tick_params(axis='x',rotation=20)
    fig.suptitle('500 synthetic scenarios · workflow demonstration, not market evidence',fontsize=12)
    output=ROOT/'outputs';output.mkdir(exist_ok=True)
    fig.savefig(output/'cost_analysis_charts.png',dpi=160)
    plt.close(fig)
    print('Charts: outputs/cost_analysis_charts.png')


if __name__=='__main__':main()
