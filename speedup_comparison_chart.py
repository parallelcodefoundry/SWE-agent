import matplotlib.pyplot as plt
import numpy as np

# Data
categories = ['w/o profiling', 'w/ profiling']
avg_speedup = [1.1, 1.2]  # Average speedup (solid bars)
max_speedup = [3.2, 3.4]  # Max speedup (will be stacked on top, so we need the difference)

# For stacked bar, the second segment should be the additional height
max_additional = [max_speedup[i] - avg_speedup[i] for i in range(len(max_speedup))]

# Colors
colors = ['#FF8C00', '#1E90FF']  # Orange for w/o profiling, Blue for w/ profiling

# Create figure
fig, ax = plt.subplots(figsize=(8, 6))

# Bar positions
x = np.arange(len(categories))
width = 0.5

# Plot average speedup (solid bars)
bars_avg = ax.bar(x, avg_speedup, width, color=colors, label='Average Speedup')

# Plot max speedup (striped bars, stacked on top)
bars_max = ax.bar(x, max_additional, width, bottom=avg_speedup,
                   color=colors, hatch='///', edgecolor='white', linewidth=0.5)

# Customize the chart
ax.set_ylabel('% Speedup', fontsize=12)
ax.set_title('Performance Optimization: Profiling vs No Profiling', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
ax.set_ylim(0, 4.5)

# Add value labels on bars
for i, (avg, mx) in enumerate(zip(avg_speedup, max_speedup)):
    # Label for average (middle of solid portion)
    ax.text(i, avg/2, f'Avg: {avg}%', ha='center', va='center', fontsize=11, fontweight='bold', color='black')
    # Label for max (middle of striped portion)
    ax.text(i, avg + (mx - avg)/2, f'Max: {mx}%', ha='center', va='center', fontsize=11, fontweight='bold', color='black')

# Create custom legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#FF8C00', label='w/o profiling'),
    Patch(facecolor='#1E90FF', label='w/ profiling'),
    Patch(facecolor='gray', label='Average Speedup'),
    Patch(facecolor='gray', hatch='///', edgecolor='white', label='Max Speedup')
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

# Add grid for readability
ax.yaxis.grid(True, linestyle='--', alpha=0.7)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig('/pscratch/sd/k/krydzy/SWE-agent/speedup_comparison_new.png', dpi=150, bbox_inches='tight')
plt.savefig('/pscratch/sd/k/krydzy/SWE-agent/speedup_comparison_new.pdf', bbox_inches='tight')
print("Chart saved as speedup_comparison_new.png and speedup_comparison_new.pdf")
