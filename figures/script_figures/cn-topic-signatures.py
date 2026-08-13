"""
cn-topic-signatures.py
──────────────────────
Isolated standalone script for the per-topic cluster approval-rate bubble chart.
Source: notebooks/07_paper_visuals.ipynb cell 4.
No src.io / parquet dependency — all bubble values are hardcoded from
data/processed/topics/topic_cluster_stats.parquet (extracted 2026-06-26).

Column mapping:
  avg_cluster_0 → paper Cluster 1 (Cl.1, red  #ff5a52, 53.9% of raters)
  avg_cluster_1 → paper Cluster 2 (Cl.2, blue #58a5ff, 46.1% of raters)

Outputs (same basename triplet per AGENTS.md):
  cn-topic-signatures.pdf
  cn-topic-signatures.png

Run:
  cd figures/script_figures
  python cn-topic-signatures.py
"""

import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Output paths ──────────────────────────────────────────────────────────────
HERE    = pathlib.Path(__file__).parent
PDF_OUT = HERE / "cn-topic-signatures.pdf"
PNG_OUT = HERE / "cn-topic-signatures.png"

# ── Palette / style ───────────────────────────────────────────────────────────
PAPER_BG   = "#ffffff"
PAPER_TEXT = "#111827"

CLUSTER_COLORS     = {1: "#ff5a52", 2: "#58a5ff"}
CLUSTER_LINE_COLORS = {1: "#ff5a52", 2: "#58a5ff"}
USER_SHARES        = {1: 53.9, 2: 46.1}

NOTE_COUNT_DOT_COLOR = "#888888"
TICK_LABEL_COLOR     = "#2C2C2E"
TICK_MARK_COLOR      = "#1C1C1E"
AXIS_LABEL_COLOR     = "#1C1C1E"
GRID_LINE_COLOR      = "#F2F2F7"
SPINE_COLOR          = "#1C1C1E"
LEGEND_TEXT_COLOR    = PAPER_TEXT

# ── Legend layout knobs (unchanged from notebook) ─────────────────────────────
LEGEND_BOTTOM = 0.03
LEGEND_X      = 0
LEGEND_Y      = 0.02

LEGEND_CL1_DOT_X  = LEGEND_X + 0.045; LEGEND_CL1_DOT_Y  = LEGEND_Y + 0.310
LEGEND_CL1_TEXT_X = LEGEND_X + 0.080; LEGEND_CL1_TEXT_Y = LEGEND_Y + 0.310
LEGEND_CL2_DOT_X  = LEGEND_X + 0.045; LEGEND_CL2_DOT_Y  = LEGEND_Y + 0.260
LEGEND_CL2_TEXT_X = LEGEND_X + 0.080; LEGEND_CL2_TEXT_Y = LEGEND_Y + 0.260

LEGEND_NOTE_COUNT_TEXT_X = LEGEND_X + 0.015; LEGEND_NOTE_COUNT_TEXT_Y = LEGEND_Y + 0.190
LEGEND_100_DOT_X  = LEGEND_X + 0.045; LEGEND_100_DOT_Y  = LEGEND_Y + 0.150
LEGEND_100_TEXT_X = LEGEND_X + 0.080; LEGEND_100_TEXT_Y = LEGEND_Y + 0.150
LEGEND_500_DOT_X  = LEGEND_X + 0.045; LEGEND_500_DOT_Y  = LEGEND_Y + 0.100
LEGEND_500_TEXT_X = LEGEND_X + 0.080; LEGEND_500_TEXT_Y = LEGEND_Y + 0.100
LEGEND_1500_DOT_X = LEGEND_X + 0.045; LEGEND_1500_DOT_Y = LEGEND_Y + 0.035
LEGEND_1500_TEXT_X = LEGEND_X + 0.080; LEGEND_1500_TEXT_Y = LEGEND_Y + 0.035

PLOT_NOTE_DOT_SIZES   = {100: 200,  500: 750,  1500: 2100}
LEGEND_NOTE_DOT_SIZES = {100:  50,  500: 100,  1500:  200}
PLOT_DOT_WHITE_EDGE_WIDTH = 1

# ── Baked data (extracted from topic_cluster_stats.parquet 2026-06-26) ────────
# Format: (display_label, avg_cluster_0=Cl.1, avg_cluster_1=Cl.2, notes)
# Ordered by approval gap: Cl.2-dominant (top) → Cl.1-dominant (bottom)
BAKED_DATA = [
    ("Haitian pets claim",    0.207, 0.858,  36),
    ("Trump conviction",      0.260, 0.785,  64),
    ("Vaccines / COVID-19",   0.367, 0.765, 388),
    ("Ukraine / Russia war",  0.509, 0.806, 139),
    ("Voting / elections",    0.383, 0.677, 107),
    ("Epstein files",         0.473, 0.758, 164),
    ("Tariffs",               0.512, 0.750, 116),
    ("Biden / Kamala Harris", 0.494, 0.606, 220),
    ("Israel / Palestine",    0.605, 0.515, 233),
    ("Iran",                  0.657, 0.536, 299),
    ("Gaza hostages",         0.693, 0.453, 159),
    ("Elon Musk",             0.696, 0.405, 185),
    ("Abortion ban",          0.808, 0.258,  71),
]

# Internal cluster index → paper cluster number mapping (matches notebook)
INTERNAL_TO_PAPER = {0: 1, 1: 2}   # avg_cluster_0 → Cl.1, avg_cluster_1 → Cl.2
PAPER_TO_INTERNAL = {v: k for k, v in INTERNAL_TO_PAPER.items()}


def marker_area(notes, size_lookup=PLOT_NOTE_DOT_SIZES):
    counts = np.array(sorted(size_lookup), dtype=float)
    areas  = np.array([size_lookup[int(n)] for n in counts], dtype=float)
    x = float(notes)
    if x <= counts[0]:
        slope = (areas[1] - areas[0]) / (counts[1] - counts[0])
        return max(1.0, float(areas[0] + (x - counts[0]) * slope))
    if x >= counts[-1]:
        slope = (areas[-1] - areas[-2]) / (counts[-1] - counts[-2])
        return max(1.0, float(areas[-1] + (x - counts[-1]) * slope))
    return max(1.0, float(np.interp(x, counts, areas)))


def legend_size(notes):
    return marker_area(notes, LEGEND_NOTE_DOT_SIZES)


# ── Build display_order list ──────────────────────────────────────────────────
display_order = []
for display_label, cl1_rate, cl2_rate, notes in BAKED_DATA:
    # Store as dict keyed by internal index for easy scatter loop below
    display_order.append({
        "label":  display_label,
        "avg_cluster_0": cl1_rate,   # paper Cl.1
        "avg_cluster_1": cl2_rate,   # paper Cl.2
        "notes":  notes,
    })

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.2, 4.0))
fig.patch.set_facecolor(PAPER_BG)
ax.set_facecolor(PAPER_BG)

# Dotted lines per cluster (draw first, under dots)
for paper_c, internal_c in PAPER_TO_INTERNAL.items():
    col_key = f"avg_cluster_{internal_c}"
    xs = [row[col_key] for row in display_order]
    ys = [row["label"]  for row in display_order]
    ax.plot(xs, ys,
            color=CLUSTER_LINE_COLORS[paper_c],
            linewidth=1.1, linestyle=(0, (1.2, 2.5)),
            alpha=0.75, zorder=2)

# Scatter dots (draw smallest first so large dots sit on top)
for row in sorted(display_order, key=lambda r: marker_area(r["notes"])):
    for paper_c, internal_c in PAPER_TO_INTERNAL.items():
        col_key = f"avg_cluster_{internal_c}"
        ax.scatter(
            row[col_key], row["label"],
            s=marker_area(row["notes"]),
            color=CLUSTER_COLORS[paper_c],
            alpha=0.92, zorder=3,
            edgecolors="white",
            linewidths=PLOT_DOT_WHITE_EDGE_WIDTH,
        )

ax.set_xlabel("Approval rate", fontsize=13, labelpad=8, color=AXIS_LABEL_COLOR)
ax.set_xlim(0, 1)
ax.set_xticks([0, 0.25, 0.50, 0.75, 1.00])
ax.grid(axis="x", color=GRID_LINE_COLOR, linewidth=0.8)
ax.set_axisbelow(True)
ax.invert_yaxis()
ax.tick_params(axis="y", labelsize=10, color=TICK_MARK_COLOR, labelcolor=TICK_LABEL_COLOR)
ax.tick_params(axis="x", labelsize=10, color=TICK_MARK_COLOR, labelcolor=TICK_LABEL_COLOR)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_linewidth(1.4)
ax.spines["bottom"].set_linewidth(1.4)
ax.spines["left"].set_color(SPINE_COLOR)
ax.spines["bottom"].set_color(SPINE_COLOR)

fig.subplots_adjust(bottom=LEGEND_BOTTOM)


def legend_dot(x, y, size, color):
    ax.scatter([x], [y], s=size, color=color,
               transform=ax.transAxes,
               edgecolors="none", linewidths=0,
               zorder=10, clip_on=False)


def legend_text(x, y, text):
    ax.text(x, y, text, transform=ax.transAxes,
            ha="left", va="center",
            fontsize=9, color=LEGEND_TEXT_COLOR,
            zorder=10, clip_on=False)


legend_dot(LEGEND_CL1_DOT_X, LEGEND_CL1_DOT_Y, 9 ** 2, CLUSTER_COLORS[1])
legend_text(LEGEND_CL1_TEXT_X, LEGEND_CL1_TEXT_Y, f"Cl. 1 ({USER_SHARES[1]:.1f}%)")
legend_dot(LEGEND_CL2_DOT_X, LEGEND_CL2_DOT_Y, 9 ** 2, CLUSTER_COLORS[2])
legend_text(LEGEND_CL2_TEXT_X, LEGEND_CL2_TEXT_Y, f"Cl. 2 ({USER_SHARES[2]:.1f}%)")

legend_text(LEGEND_NOTE_COUNT_TEXT_X, LEGEND_NOTE_COUNT_TEXT_Y, "note count:")
legend_dot(LEGEND_100_DOT_X,  LEGEND_100_DOT_Y,  legend_size(100),  NOTE_COUNT_DOT_COLOR)
legend_text(LEGEND_100_TEXT_X, LEGEND_100_TEXT_Y, "100")
legend_dot(LEGEND_500_DOT_X,  LEGEND_500_DOT_Y,  legend_size(500),  NOTE_COUNT_DOT_COLOR)
legend_text(LEGEND_500_TEXT_X, LEGEND_500_TEXT_Y, "500")
legend_dot(LEGEND_1500_DOT_X, LEGEND_1500_DOT_Y, legend_size(1500), NOTE_COUNT_DOT_COLOR)
legend_text(LEGEND_1500_TEXT_X, LEGEND_1500_TEXT_Y, "1,500")

plt.tight_layout(rect=[0, LEGEND_BOTTOM, 1, 1])

# ── Save ──────────────────────────────────────────────────────────────────────
fig.savefig(PDF_OUT, bbox_inches="tight", dpi=300)
fig.savefig(PNG_OUT, bbox_inches="tight", dpi=300)
print(f"Saved: {PDF_OUT}")
print(f"Saved: {PNG_OUT}")
plt.close(fig)
