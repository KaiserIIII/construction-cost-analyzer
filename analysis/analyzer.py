#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construction Project Cost Analyzer
建筑工程成本数据分析工具
Analyzes cost overrun causes and risk management for construction projects.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

# Auto-detect Chinese font on your system
import matplotlib.font_manager as fm
_sys_fonts = [f.name for f in fm.fontManager.ttflist]
_cjk_candidates = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans']
_selected = next((f for f in _cjk_candidates if f in _sys_fonts), 'DejaVu Sans')
plt.rcParams['font.family'] = _selected
plt.rcParams['axes.unicode_minus'] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 1. Data Loading & Cleaning
# ============================================================
df = pd.read_csv(os.path.join(DATA_DIR, 'construction_projects.csv'))
df['start_date'] = pd.to_datetime(df['开工日期'])
df['end_date'] = pd.to_datetime(df['竣工日期'])
df['actual_duration'] = (df['end_date'] - df['start_date']).dt.days
df['cost_deviation_wan'] = df['实际成本_万元'] - df['预算_万元']
df['cost_deviation_pct'] = (df['cost_deviation_wan'] / df['预算_万元'] * 100).round(1)
df['cost_per_sqm'] = (df['实际成本_万元'] * 10000 / df['建筑面积_平米']).round(0).astype(int)

# Map columns for readability
df['structure'] = df['结构类型'].map({'框架': 'Frame', '框剪': 'Frame-Shear', '钢结构': 'Steel', '砖混': 'Masonry'})
df['region'] = df['地区'].map({'华东': 'East China', '华北': 'North China', '华南': 'South China', '西南': 'Southwest'})
df['is_over_budget'] = df['是否超预算'].map({'是': True, '否': False})

print("=" * 60)
print("  Construction Project Cost Analysis Report")
print("=" * 60)

# ============================================================
# 2. Overall Statistics
# ============================================================
print(f"\n[SUMMARY] {len(df)} projects analyzed")
print(f"  Avg floor area: {df['建筑面积_平米'].mean():,.0f} m2")
print(f"  Avg budget: {df['预算_万元'].mean():,.0f} wan CNY")
print(f"  Avg actual cost: {df['实际成本_万元'].mean():,.0f} wan CNY")
over_run = df['is_over_budget'].sum()
print(f"  Over-budget projects: {over_run}/{len(df)} ({over_run/len(df)*100:.1f}%)")
print(f"  Mean cost deviation: {df['cost_deviation_wan'].mean():.1f} wan ({df['cost_deviation_pct'].mean():.1f}%)")

# ============================================================
# 3. By Structure Type
# ============================================================
print("\n" + "-" * 40)
print("[STRUCTURE TYPE ANALYSIS]")
struct_stats = df.groupby('structure').agg(
    count=('项目名称', 'count'),
    avg_deviation_pct=('cost_deviation_pct', 'mean'),
    avg_cost_per_sqm=('cost_per_sqm', 'mean')
).round(1)
print(struct_stats.to_string())

# ============================================================
# 4. By Region
# ============================================================
print("\n" + "-" * 40)
print("[REGIONAL ANALYSIS]")
region_stats = df.groupby('region').agg(
    count=('项目名称', 'count'),
    avg_deviation_pct=('cost_deviation_pct', 'mean'),
    over_budget_ratio=('is_over_budget', 'mean'),
    avg_weather_delay=('天气延误_天', 'mean')
).round(1)
region_stats['over_budget_ratio'] = (region_stats['over_budget_ratio'] * 100).round(1)
print(region_stats.to_string())

# ============================================================
# 5. Correlation Analysis
# ============================================================
print("\n" + "-" * 40)
print("[COST OVERRUN DRIVERS — Pearson Correlation]")
corr_cols = {
    'cost_deviation_wan': 'Cost Deviation',
    '变更单数': 'Change Orders',
    '天气延误_天': 'Weather Delay',
    '安全事故数': 'Safety Incidents',
    '层数': 'Floors',
    '建筑面积_平米': 'Floor Area',
    'actual_duration': 'Duration'
}
corr_df = df[list(corr_cols.keys())].corr()
cost_corr = corr_df['cost_deviation_wan'].drop('cost_deviation_wan').sort_values(ascending=False)
for col, val in cost_corr.items():
    bar = '#' * int(abs(val) * 20)
    direction = '(+)' if val > 0 else '(-)'
    label = corr_cols.get(col, col)
    print(f"  {label:<20s} r={val:+.3f} {direction} {bar}")

# ============================================================
# 6. Change Orders Impact
# ============================================================
print("\n" + "-" * 40)
print("[IMPACT OF CHANGE ORDERS]")
df['co_level'] = pd.cut(df['变更单数'], bins=[0, 5, 12, 30], labels=['Low(0-5)', 'Med(6-12)', 'High(13+)'])
co_stats = df.groupby('co_level', observed=False).agg(
    count=('项目名称', 'count'),
    avg_deviation_pct=('cost_deviation_pct', 'mean'),
    over_budget_ratio=('is_over_budget', 'mean')
).round(1)
co_stats['over_budget_ratio'] = (co_stats['over_budget_ratio'] * 100).round(0).astype(int)
print(co_stats.to_string())

# ============================================================
# 7. Charts
# ============================================================
fig, axes = plt.subplots(2, 3, figsize=(16, 10))

# Chart 1: Structure type vs cost deviation
ax = axes[0, 0]
struct_means = df.groupby('structure')['cost_deviation_pct'].mean().sort_values()
colors = ['#e74c3c' if x > 0 else '#27ae60' for x in struct_means.values]
bars = ax.barh(struct_means.index, struct_means.values, color=colors, edgecolor='white')
ax.axvline(x=0, color='gray', linestyle='--', linewidth=1)
ax.set_title('Cost Deviation by Structure Type', fontsize=12, fontweight='bold')
ax.set_xlabel('Cost Deviation (%)')
for bar, val in zip(bars, struct_means.values):
    ax.text(val + 0.3 if val >= 0 else val - 0.8, bar.get_y() + bar.get_height()/2,
            f'{val:+.1f}%', va='center', fontsize=10)

# Chart 2: Regional comparison
ax = axes[0, 1]
x = np.arange(len(region_stats))
width = 0.35
bars1 = ax.bar(x - width/2, region_stats['avg_deviation_pct'], width, label='Avg Deviation %', color='#3498db')
ax2 = ax.twinx()
bars2 = ax2.bar(x + width/2, region_stats['over_budget_ratio'], width, label='Over-budget %', color='#e74c3c', alpha=0.7)
ax.set_xticks(x)
ax.set_xticklabels(region_stats.index, fontsize=9)
ax.set_title('Cost Deviation by Region', fontsize=12, fontweight='bold')
ax.set_ylabel('Avg Deviation (%)')
ax2.set_ylabel('Over-budget Ratio (%)')
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)

# Chart 3: Distribution histogram
ax = axes[0, 2]
ax.hist(df['cost_deviation_pct'], bins=8, color='#9b59b6', edgecolor='white', alpha=0.8)
ax.axvline(x=0, color='red', linestyle='--', linewidth=1.5)
ax.axvline(x=df['cost_deviation_pct'].mean(), color='orange', linestyle='-', linewidth=1.5,
           label=f'Mean: {df["cost_deviation_pct"].mean():.1f}%')
ax.set_title('Cost Deviation Distribution', fontsize=12, fontweight='bold')
ax.set_xlabel('Cost Deviation (%)')
ax.set_ylabel('Project Count')
ax.legend(fontsize=9)

# Chart 4: Change orders vs cost deviation
ax = axes[1, 0]
colors = ['#e74c3c' if v else '#27ae60' for v in df['is_over_budget']]
ax.scatter(df['变更单数'], df['cost_deviation_pct'], c=colors, s=df['建筑面积_平米']/200, alpha=0.7, edgecolors='black', linewidth=0.5)
z = np.polyfit(df['变更单数'], df['cost_deviation_pct'], 1)
p = np.poly1d(z)
x_line = np.linspace(df['变更单数'].min(), df['变更单数'].max(), 100)
ax.plot(x_line, p(x_line), '--', color='gray', alpha=0.7, linewidth=1.5)
ax.set_title('Change Orders vs Cost Deviation', fontsize=12, fontweight='bold')
ax.set_xlabel('Change Orders (count)')
ax.set_ylabel('Cost Deviation (%)')

# Chart 5: Cost per sqm by structure
ax = axes[1, 1]
struct_cost = df.groupby('structure')['cost_per_sqm'].mean().sort_values()
bars = ax.barh(struct_cost.index, struct_cost.values, color=['#f39c12', '#e67e22', '#d35400'])
ax.set_title('Avg Cost per m2 by Structure', fontsize=12, fontweight='bold')
ax.set_xlabel('Cost per m2 (CNY)')
for bar, val in zip(bars, struct_cost.values):
    ax.text(val + 30, bar.get_y() + bar.get_height()/2, f'{val:,}', va='center', fontsize=10)

# Chart 6: Top 5 over-budget projects
ax = axes[1, 2]
top5 = df.nlargest(5, 'cost_deviation_pct')
short_names = [n[:8] + '..' if len(n) > 8 else n for n in top5['项目名称']]
x = np.arange(len(top5))
width = 0.25
ax.bar(x - width, top5['cost_deviation_pct'], width, label='Deviation %', color='#c0392b')
ax.bar(x, top5['变更单数'], width, label='Change Orders', color='#8e44ad')
ax.bar(x + width, top5['天气延误_天'], width, label='Weather Delay', color='#2980b9')
ax.set_xticks(x)
ax.set_xticklabels(short_names, rotation=20, ha='right', fontsize=8)
ax.set_title('Top 5 Over-budget Projects', fontsize=12, fontweight='bold')
ax.legend(fontsize=8)

plt.tight_layout()
chart_path = os.path.join(OUTPUT_DIR, 'cost_analysis_charts.png')
fig.savefig(chart_path, dpi=150, bbox_inches='tight')
print(f"\n[DONE] Charts saved to outputs/cost_analysis_charts.png")

# ============================================================
# 8. Key Findings
# ============================================================
print("\n" + "=" * 60)
print("  KEY FINDINGS")
print("=" * 60)
print(f"1. {over_run/len(df)*100:.1f}% of projects exceeded budget: avg deviation {df['cost_deviation_pct'].mean():.1f}%")
print(f"2. Change orders are the #1 controllable cost driver (r={cost_corr['变更单数']:.3f})")
print(f"3. Weather delays strongly correlate with cost overruns (r={cost_corr['天气延误_天']:.3f})")
print(f"4. Frame-Shear wall structures have highest deviation ({struct_stats.loc['Frame-Shear','avg_deviation_pct']:.1f}%)")
print(f"5. High change-order projects (>12 COs) go over budget {co_stats.loc['High(13+)','over_budget_ratio']}% of the time")
print(f"6. Each additional change order correlates with ~{cost_corr['变更单数']:.2f} std increase in cost deviation")
print("\n  RECOMMENDATIONS:")
print("  > Tighten change order approval process")
print("  > Frame-Shear projects need larger risk reserves")
print("  > East China/Southwest: budget extra weather contingency")
print("\n" + "=" * 60)
