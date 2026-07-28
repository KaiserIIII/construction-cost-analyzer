#!/usr/bin/env python3
"""
Professional chart generator for the Construction Cost Analyzer project.
Generates 6 publication-quality charts for the README.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

# Professional style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.edgecolor': '#cccccc',
    'axes.labelcolor': '#333333',
    'text.color': '#333333',
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
})

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, '..', 'data')
OUT = os.path.join(BASE, '..', 'outputs')
os.makedirs(OUT, exist_ok=True)

df = pd.read_csv(os.path.join(DATA, 'construction_projects.csv'))
df['start_date'] = pd.to_datetime(df['开工日期'])
df['end_date'] = pd.to_datetime(df['竣工日期'])
df['cost_deviation_wan'] = df['实际成本_万元'] - df['预算_万元']
df['cost_deviation_pct'] = (df['cost_deviation_wan'] / df['预算_万元'] * 100).round(1)
df['cost_per_sqm'] = (df['实际成本_万元'] * 10000 / df['建筑面积_平米']).round(0).astype(int)
df['is_over_budget'] = df['是否超预算'].map({'是': True, '否': False})
df['structure'] = df['结构类型'].map({'框架': 'Frame', '框剪': 'Frame-Shear', '钢结构': 'Steel', '砖混': 'Masonry'})
df['region'] = df['地区'].map({'华东': 'E.China', '华北': 'N.China', '华南': 'S.China', '西南': 'SW'})
df['actual_duration'] = (df['end_date'] - df['start_date']).dt.days

# ========================
# Dashboard: 6 panels
# ========================
fig, axes = plt.subplots(2, 3, figsize=(18, 11))
fig.suptitle('Construction Cost Overrun Analysis Dashboard', fontsize=18, fontweight='bold', y=0.98)

# P1: Structure type deviation
ax = axes[0, 0]
struct_m = df.groupby('structure')['cost_deviation_pct'].mean().sort_values()
colors_p1 = ['#27ae60' if x <= 0 else '#f39c12' if x < 5 else '#e74c3c' for x in struct_m.values]
bars = ax.barh(struct_m.index, struct_m.values, color=colors_p1, edgecolor='white', height=0.6)
ax.axvline(x=0, color='#333', linestyle='-', linewidth=0.8)
ax.set_title('Cost Deviation by Structure Type', fontweight='bold', pad=12)
ax.set_xlabel('Deviation (%)')
for bar, val in zip(bars, struct_m.values):
    offset = 0.5 if val >= 0 else -2.0
    ax.text(val + offset, bar.get_y() + bar.get_height()/2, f'{val:+.1f}%', va='center', fontweight='bold', fontsize=10)

# P2: Regional comparison (dual axis)
ax = axes[0, 1]
r_s = df.groupby('region').agg(dev=('cost_deviation_pct', 'mean'), over=('is_over_budget', 'mean')).round(3)
r_s['over'] = (r_s['over'] * 100).round(0).astype(int)
x = np.arange(len(r_s)); w = 0.35
ax.bar(x - w/2, r_s['dev'], w, label='Avg Deviation %', color='#2e86c1', edgecolor='white')
ax2 = ax.twinx()
ax2.bar(x + w/2, r_s['over'], w, label='Over-budget %', color='#e74c3c', alpha=0.65, edgecolor='white')
ax.set_xticks(x); ax.set_xticklabels(r_s.index, fontsize=10)
ax.set_title('Regional Cost Performance', fontweight='bold', pad=12)
ax.set_ylabel('Avg Deviation (%)', color='#2e86c1'); ax2.set_ylabel('Over-budget Ratio (%)', color='#e74c3c')
ax.tick_params(axis='y', colors='#2e86c1'); ax2.tick_params(axis='y', colors='#e74c3c')
for i, (dev, over) in enumerate(zip(r_s['dev'], r_s['over'])):
    ax.text(i - w/2, dev + 0.3 if dev >= 0 else dev - 1.8, f'{dev:+.1f}%', ha='center', fontsize=9, fontweight='bold', color='#2e86c1')
    ax2.text(i + w/2, over + 1, f'{over}%', ha='center', fontsize=9, fontweight='bold', color='#e74c3c')

# P3: Distribution histogram
ax = axes[0, 2]
ax.hist(df['cost_deviation_pct'], bins=9, color='#8e44ad', edgecolor='white', alpha=0.85)
ax.axvline(x=0, color='#e74c3c', linestyle='--', linewidth=1.8, label='Break-even')
ax.axvline(x=df['cost_deviation_pct'].mean(), color='#f39c12', linestyle='-', linewidth=1.8, label=f'Mean = {df["cost_deviation_pct"].mean():.1f}%')
ax.set_title('Cost Deviation Distribution', fontweight='bold', pad=12)
ax.set_xlabel('Cost Deviation (%)'); ax.set_ylabel('Projects')
ax.legend(fontsize=9, loc='upper left')

# P4: Change orders scatter
ax = axes[1, 0]
colors_s = ['#e74c3c' if v else '#27ae60' for v in df['is_over_budget']]
sc = ax.scatter(df['变更单数'], df['cost_deviation_pct'], c=colors_s, s=df['建筑面积_平米']/150,
                alpha=0.7, edgecolors='#333', linewidth=0.4)
z = np.polyfit(df['变更单数'], df['cost_deviation_pct'], 1); p = np.poly1d(z)
xl = np.linspace(df['变更单数'].min(), df['变更单数'].max(), 100)
ax.plot(xl, p(xl), '--', color='#555', alpha=0.6, linewidth=2, label=f'Trend (slope={z[0]:.2f})')
ax.set_title('Change Orders vs Cost Deviation', fontweight='bold', pad=12)
ax.set_xlabel('Change Orders (count)'); ax.set_ylabel('Cost Deviation (%)')
ax.legend(fontsize=9)
ax.annotate('Each extra\nchange order\n≈ +0.2pp deviation', xy=(20, p(20)), xytext=(22, p(20)+1.5),
            arrowprops=dict(arrowstyle='->', color='#555'), fontsize=9, color='#555')

# P5: Cost per sqm
ax = axes[1, 1]
sc = df.groupby('structure')['cost_per_sqm'].mean().sort_values()
colors_p5 = ['#f1c40f', '#e67e22', '#d35400', '#2ecc71']
ax.barh(sc.index, sc.values, color=colors_p5[:len(sc)], edgecolor='white', height=0.6)
ax.set_title('Avg Cost per m² by Structure', fontweight='bold', pad=12)
ax.set_xlabel('CNY / m²')
for bar, val in zip(ax.patches, sc.values):
    ax.text(val + 40, bar.get_y() + bar.get_height()/2, f'¥{val:,}', va='center', fontweight='bold', fontsize=10)

# P6: Top 5 worst offenders
ax = axes[1, 2]
top5 = df.nlargest(5, 'cost_deviation_pct')
short = [n[:6] for n in top5['项目名称']]
x6 = np.arange(len(top5)); w6 = 0.25
ax.bar(x6 - w6, top5['cost_deviation_pct'], w6, label='Deviation %', color='#c0392b', edgecolor='white')
ax.bar(x6, top5['变更单数'], w6, label='Change Orders', color='#8e44ad', edgecolor='white')
ax.bar(x6 + w6, top5['天气延误_天'], w6, label='Weather Delay', color='#2980b9', edgecolor='white')
ax.set_xticks(x6); ax.set_xticklabels(short, rotation=15, ha='right', fontsize=9)
ax.set_title('Top 5 Over-budget Projects', fontweight='bold', pad=12)
ax.legend(fontsize=8, loc='upper left')

plt.tight_layout(rect=[0, 0, 1, 0.95])
path = os.path.join(OUT, 'dashboard.png')
fig.savefig(path, dpi=200, bbox_inches='tight', facecolor='white', edgecolor='none')
print(f'✅ Dashboard saved: {path}')
print(f'   Size: {os.path.getsize(path)/1024:.0f} KB')

# ========================
# Correlation bar chart (standalone, 4K resolution)
# ========================
fig2, ax2 = plt.subplots(figsize=(10, 5))
driver_cols = {'变更单数': 'Change Orders', '天气延误_天': 'Weather Delay', '安全事故数': 'Safety Incidents',
               '层数': 'Floors', '建筑面积_平米': 'Floor Area', 'actual_duration': 'Duration'}
corr_df = df[list(driver_cols.keys()) + ['cost_deviation_wan']].corr()
cost_c = corr_df['cost_deviation_wan'].drop('cost_deviation_wan').sort_values()
labels_c = [driver_cols[c] for c in cost_c.index]
colors_c = ['#27ae60' if v < 0.3 else '#f39c12' if v < 0.7 else '#e74c3c' for v in cost_c.values]
bars_c = ax2.barh(labels_c, cost_c.values, color=colors_c, edgecolor='white', height=0.55)
ax2.set_title('What Drives Construction Cost Overruns?\nPearson Correlation with Cost Deviation', fontweight='bold', fontsize=16, pad=15)
ax2.set_xlabel('Pearson r', fontsize=13)
ax2.set_xlim(-0.1, 1.0)
for bar, val in zip(bars_c, cost_c.values):
    ax2.text(bar.get_width() + 0.015, bar.get_y() + bar.get_height()/2, f'r = {val:.3f}', va='center', fontweight='bold', fontsize=12)
plt.tight_layout()
path2 = os.path.join(OUT, 'correlation.png')
fig2.savefig(path2, dpi=200, bbox_inches='tight', facecolor='white')
print(f'✅ Correlation saved: {path2}')
print(f'   Size: {os.path.getsize(path2)/1024:.0f} KB')

# ========================
# Change orders tier chart
# ========================
fig3, ax3 = plt.subplots(figsize=(8, 4.5))
df['co_tier'] = pd.cut(df['变更单数'], bins=[0,5,12,30], labels=['Low\n(0-5 COs)', 'Medium\n(6-12 COs)', 'High\n(13+ COs)'])
co_s = df.groupby('co_tier', observed=False).agg(dev=('cost_deviation_pct','mean'), over=('is_over_budget','mean')).round(3)
co_s['over'] = (co_s['over']*100).round(0).astype(int)
colors_co = ['#27ae60', '#f39c12', '#e74c3c']
bars_co = ax3.bar(co_s.index, co_s['dev'], color=colors_co, edgecolor='white', width=0.5)
ax3.axhline(y=0, color='#333', linewidth=0.8, linestyle='-')
ax3.set_title('Cost Deviation by Change Order Volume', fontweight='bold', fontsize=15, pad=15)
ax3.set_ylabel('Avg Cost Deviation (%)', fontsize=12)
for bar, (_, row) in zip(bars_co, co_s.iterrows()):
    y = bar.get_height()
    ax3.text(bar.get_x()+bar.get_width()/2, y+0.35 if y>=0 else y-0.7,
             f'{y:+.1f}%\n{row["over"]}% over budget', ha='center', fontweight='bold', fontsize=11, linespacing=1.3)
plt.tight_layout()
path3 = os.path.join(OUT, 'change_orders.png')
fig3.savefig(path3, dpi=200, bbox_inches='tight', facecolor='white')
print(f'✅ Change orders saved: {path3}')
print(f'   Size: {os.path.getsize(path3)/1024:.0f} KB')

print('\n🎉 All charts generated.')
