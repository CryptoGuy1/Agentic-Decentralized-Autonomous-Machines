import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

# --- Figure (high DPI for IEEE) ---
fig, ax = plt.subplots(figsize=(14, 12), dpi=300)
ax.set_xlim(0, 14.6)
ax.set_ylim(0, 13)
ax.axis('off')

# --- Colors ---
box_color = '#FFFFFF'
edge_color = '#404040'
text_color = '#000000'
arrow_color = '#606060'
lifeline_color = '#A0A0A0'

# --- Fonts (IEEE-friendly) ---
FS_ACTOR = 14      # actor labels
FS_PHASE = 16      # phase headings
FS_STEP = 12       # step number circles
FS_ARROWLBL = 11   # arrow labels

# --- Actor order (left -> right) ---
actor_keys_in_order = [
    'Sensor', 'Aggregator', 'Decision', 'Coordinator', 'Weaviate', 'Blockchain', 'Alert'
]

# --- Evenly spaced x-positions for equal gaps ---
left_margin = 1.2
right_margin = 13.4
xs = np.linspace(left_margin, right_margin, len(actor_keys_in_order))

actors = {k: x for k, x in zip(actor_keys_in_order, xs)}

# --- Draw actor boxes at top ---
actor_y = 12
actor_width = 1.8
actor_height = 0.8

for k in actor_keys_in_order:
    x = actors[k]
    box = FancyBboxPatch(
        (x - actor_width/2, actor_y), actor_width, actor_height,
        boxstyle="round,pad=0.05",
        facecolor=box_color,
        edgecolor=edge_color,
        linewidth=1.6
    )
    ax.add_patch(box)

    if k in ['Sensor', 'Aggregator', 'Decision', 'Coordinator']:
        display_name = f'{k}\nAgent'
    elif k == 'Weaviate':
        display_name = 'Weaviate DB'
    elif k == 'Blockchain':
        display_name = 'Blockchain'
    else:  # Alert
        display_name = 'Alert System'

    ax.text(
        x, actor_y + actor_height/2, display_name,
        fontsize=FS_ACTOR, fontweight='bold', ha='center', va='center',
        color=text_color
    )

# --- Lifelines (vertical dashed) ---
lifeline_start = actor_y - 0.1
lifeline_end = 0.5
for k in actor_keys_in_order:
    x = actors[k]
    ax.plot(
        [x, x], [lifeline_start, lifeline_end],
        linestyle='--', linewidth=1.2, color=lifeline_color, alpha=0.7
    )

# --- Arrow helpers ---
def draw_arrow(ax, x_start, x_end, y, label, step_num, style='solid'):
    """Draw horizontal arrow between actors with step number and label."""
    arrow = FancyArrowPatch(
        (x_start, y), (x_end, y),
        arrowstyle='->', mutation_scale=15,
        linewidth=1.6, color=arrow_color,
        linestyle='-' if style == 'solid' else '--'
    )
    ax.add_patch(arrow)

    # Step number circle (slight left offset to reduce overlap with labels)
    cx = (x_start + x_end) / 2 - 0.5
    circle = plt.Circle(
        (cx, y), 0.22,
        facecolor=box_color, edgecolor=edge_color, linewidth=1.6
    )
    ax.add_patch(circle)
    ax.text(
        cx, y, str(step_num),
        fontsize=FS_STEP, fontweight='bold', ha='center', va='center',
        color=text_color
    )

    # Label above the arrow (slight right bias)
    ax.text(
        (x_start + x_end)/2 + 0.3, y + 0.25, label,
        fontsize=FS_ARROWLBL, ha='center', va='bottom',
        color=text_color
    )

def draw_self_call(ax, x, y, label, step_num):
    """Draw a self-call loop at x,y."""
    loop_width = 0.7
    # horizontal top
    ax.plot([x, x + loop_width], [y, y], color=arrow_color, linewidth=1.6)
    # vertical down
    ax.plot([x + loop_width, x + loop_width], [y, y - 0.35], color=arrow_color, linewidth=1.6)
    # horizontal back with head
    ax.plot(
        [x + loop_width, x], [y - 0.35, y - 0.35],
        color=arrow_color, linewidth=1.6, marker='>', markersize=6,
        markerfacecolor=arrow_color
    )

    # Step number circle
    circle = plt.Circle(
        (x + loop_width/2, y), 0.22,
        facecolor=box_color, edgecolor=edge_color, linewidth=1.6
    )
    ax.add_patch(circle)
    ax.text(
        x + loop_width/2, y, str(step_num),
        fontsize=FS_STEP, fontweight='bold', ha='center', va='center',
        color=text_color
    )

    # label text
    ax.text(
        x + loop_width + 0.35, y - 0.18, label,
        fontsize=FS_ARROWLBL, ha='left', va='center',
        color=text_color
    )

# ===== WORKFLOW STEPS =====
current_y = 11.2

# 1: Continuous Monitoring (Sensor self-call)
draw_self_call(ax, actors['Sensor'], current_y,
               'Collect & preprocess sensor data', 1)
current_y -= 0.8

# 2: Trigger Identification
draw_self_call(ax, actors['Sensor'], current_y,
               'Detect methane above threshold', 2)
current_y -= 0.8

# 3: Crew Trigger Event
draw_arrow(
    ax, actors['Sensor'], actors['Weaviate'], current_y,
    'Post crew trigger event', 3, 'solid'
)
current_y -= 0.8

# 4: Other agents join crew (same step id for all joins)
draw_arrow(
    ax, actors['Aggregator'], actors['Weaviate'], current_y,
    'Subscribe to crew', 4, 'dashed'
)
draw_arrow(
    ax, actors['Decision'], actors['Weaviate'], current_y - 0.18,
    'Join crew', 4, 'dashed'
)
draw_arrow(
    ax, actors['Coordinator'], actors['Weaviate'], current_y - 0.36,
    'Join crew', 4, 'dashed'
)
current_y -= 1.25

# 5: Data Aggregation (request)
draw_arrow(
    ax, actors['Aggregator'], actors['Weaviate'], current_y,
    'Query multi-sensor data', 5, 'solid'
)
current_y -= 0.65

# 6: Data Aggregation (response)
draw_arrow(
    ax, actors['Weaviate'], actors['Aggregator'], current_y,
    'Return aggregated data', 6, 'dashed'
)
current_y -= 0.85

# 7: Collaborative Reasoning (Decision uses LLM)
draw_self_call(ax, actors['Decision'], current_y,
               'LLM-based anomaly classification', 7)
current_y -= 0.75

# 8: Store analysis in Weaviate
draw_arrow(
    ax, actors['Decision'], actors['Weaviate'], current_y,
    'Store analysis & recommendation', 8, 'solid'
)
current_y -= 0.85

# 9: Coordinator retrieves decisions
draw_arrow(
    ax, actors['Coordinator'], actors['Weaviate'], current_y,
    'Retrieve crew analysis', 9, 'solid'
)
current_y -= 0.65

# 10: Governance query
draw_arrow(
    ax, actors['Coordinator'], actors['Blockchain'], current_y,
    'Check governance policy', 10, 'solid'
)
current_y -= 0.65

# 11: Governance response
draw_arrow(
    ax, actors['Blockchain'], actors['Coordinator'], current_y,
    'Return consensus rules', 11, 'dashed'
)
current_y -= 0.9

# 12: Action Execution
draw_arrow(
    ax, actors['Coordinator'], actors['Alert'], current_y,
    'Trigger alert or control action', 12, 'solid'
)
current_y -= 0.85

# 13: On-Chain Logging
draw_arrow(
    ax, actors['Coordinator'], actors['Blockchain'], current_y,
    'Log decision (immutable record)', 13, 'solid'
)
current_y -= 0.85

# 14: Explainability Trace
draw_arrow(
    ax, actors['Coordinator'], actors['Weaviate'], current_y,
    'Store reasoning trace', 14, 'solid'
)

# --- Phase labels on the left ---
phase_x = 0.3
ax.text(
    phase_x, 10.5, 'EMISSION\nDETECTION', fontsize=FS_PHASE, fontweight='bold',
    ha='center', va='center', rotation=90, color=text_color
)
ax.text(
    phase_x, 6.5, 'CREW\nCOORDINATION', fontsize=FS_PHASE, fontweight='bold',
    ha='center', va='center', rotation=90, color=text_color
)
ax.text(
    phase_x, 2.5, 'ACTION &\nLOGGING', fontsize=FS_PHASE, fontweight='bold',
    ha='center', va='center', rotation=90, color=text_color
)

# --- Phase separators (optional) ---
ax.plot([0.8, 14.2], [8.2, 8.2], linestyle='--', linewidth=1.2,
        color=lifeline_color, alpha=0.5)
ax.plot([0.8, 14.2], [4.2, 4.2], linestyle='--', linewidth=1.2,
        color=lifeline_color, alpha=0.5)

plt.tight_layout()
plt.savefig('adam_workflow.pdf', format='pdf', bbox_inches='tight', dpi=300)
plt.savefig('adam_workflow.png', format='png', bbox_inches='tight', dpi=300)
plt.show()

# --- Caption for LaTeX ---
print("\n" + "="*70)
print("SUGGESTED FIGURE CAPTION FOR LaTeX:")
print("="*70)

print("="*70)
