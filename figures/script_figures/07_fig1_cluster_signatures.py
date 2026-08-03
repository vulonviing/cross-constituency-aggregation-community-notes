#!/usr/bin/env python3
"""Render the conceptual rater-dominance schematic used as Figure 1."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch


FIG_DIR = Path(__file__).resolve().parent
FIG_NAME = "07_fig1_cluster_signatures"

TEXT = "#111827"
MUTED = "#4B5563"
DARK_GRAY = "#636366"
FAINT = "#AEAEB2"
RED = "#D70015"
GREEN = "#16A34A"
WHITE = "#FFFFFF"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.facecolor": WHITE,
    }
)


def draw_person(ax, x, y):
    ax.add_patch(Circle((x, y + 5.1), 0.9, facecolor=TEXT, edgecolor="none"))
    ax.plot([x, x], [y + 4.2, y + 0.2], color=TEXT, lw=1.8)
    ax.plot([x - 1.3, x + 1.3], [y + 2.8, y + 2.8], color=TEXT, lw=1.8)
    ax.plot([x, x - 1.25], [y + 0.2, y - 2.6], color=TEXT, lw=1.8)
    ax.plot([x, x + 1.25], [y + 0.2, y - 2.6], color=TEXT, lw=1.8)


def draw_arrow(ax, start, end, color=DARK_GRAY, lw=1.5):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=lw,
            color=color,
            shrinkA=0,
            shrinkB=0,
        )
    )


fig, ax = plt.subplots(figsize=(9.6, 3.5))
fig.patch.set_facecolor(WHITE)
ax.set_facecolor(WHITE)
ax.set_xlim(0, 94)
ax.set_ylim(2.5, 36.5)
ax.axis("off")

# Left: one rater contributes repeatedly to the observed matrix.
draw_person(ax, 5.8, 19.0)
draw_arrow(ax, (10.7, 22.0), (14.5, 22.0), color=DARK_GRAY, lw=1.4)
ax.text(5.8, 10.7, "ratings become\nbehavioral history", ha="center", va="top",
        fontsize=9.0, color=MUTED, linespacing=1.2)

# Middle: a regular population grid, with a few hyperactive raters highlighted.
cols, rows = 15, 8
x0, y0 = 17.0, 8.7
dx, dy = 3.35, 3.55
highlighted = {(2, 5), (4, 2), (6, 6), (8, 1), (10, 4), (12, 7)}
regular_with_edges = {
    (0, 0), (0, 4), (1, 7), (2, 2), (3, 6), (5, 0), (5, 4),
    (6, 2), (7, 7), (8, 5), (9, 0), (9, 3), (10, 7), (11, 2),
    (12, 5), (13, 1), (13, 6), (14, 3),
}
junction = (69.0, 22.0)

for col, row in sorted(regular_with_edges):
    x, y = x0 + col * dx, y0 + row * dy
    ax.plot([x, junction[0]], [y, junction[1]], color=FAINT, lw=0.9,
            alpha=0.72, zorder=1)

for col, row in sorted(highlighted):
    x, y = x0 + col * dx, y0 + row * dy
    ax.plot([x, junction[0]], [y, junction[1]], color=RED, lw=2.45,
            alpha=0.95, zorder=2)
    ax.add_patch(Circle((x, y), 0.48, facecolor=RED, edgecolor="none", zorder=5))

for col in range(cols):
    for row in range(rows):
        if (col, row) in highlighted:
            continue
        x, y = x0 + col * dx, y0 + row * dy
        ax.add_patch(Circle((x, y), 0.42, facecolor=TEXT, edgecolor="none", zorder=4))

# Compact legend embedded below the matrix.
legend_y = 5.5
ax.plot([23.0, 28.0], [legend_y, legend_y], color=FAINT, lw=1.1)
ax.text(29.0, legend_y, "sparse histories", va="center", fontsize=8.8, color=MUTED)
ax.plot([42.0, 47.0], [legend_y, legend_y], color=RED, lw=2.45)
ax.text(48.0, legend_y, "repeated observations", va="center", fontsize=8.8,
        color=RED)
# Profile junction: repeated observations have greater leverage on the fitted map.
ax.add_patch(Circle(junction, 0.68, facecolor=RED, edgecolor=WHITE,
                    linewidth=1.2, zorder=6))

# Right: a borderless hierarchy separates rater estimates from the note output.
block_x, label_x = 72.0, 75.2
ax.text(block_x, 31.0, "RATER-LEVEL ESTIMATES", ha="left", va="center",
        fontsize=8.3, fontweight="bold", color=MUTED, zorder=5)
ax.text(block_x, 26.0, r"$i_u$", ha="left", va="center",
        fontsize=12.5, fontweight="bold", color=TEXT, zorder=5)
ax.text(label_x, 26.0, "rater tendency", ha="left", va="center",
        fontsize=9.0, color=TEXT, zorder=5)
ax.text(block_x, 21.0, r"$f_u$", ha="left", va="center",
        fontsize=12.5, fontweight="bold", color=TEXT, zorder=5)
ax.text(label_x, 21.0, "inferred viewpoint", ha="left", va="center",
        fontsize=9.0, color=TEXT, zorder=5)
ax.plot([block_x, 89.5], [17.6, 17.6], color=GREEN, lw=1.6, zorder=5)
ax.text(block_x, 14.2, r"$i_n$", ha="left", va="center",
        fontsize=12.5, fontweight="bold", color=GREEN, zorder=5)
ax.text(label_x, 14.2, "note-level score", ha="left", va="center",
        fontsize=9.2, fontweight="bold", color=GREEN, zorder=5)

fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.03)
pdf_path = FIG_DIR / f"{FIG_NAME}.pdf"
png_path = FIG_DIR / f"{FIG_NAME}.png"
fig.savefig(pdf_path, facecolor=WHITE, edgecolor="none")
fig.savefig(png_path, facecolor=WHITE, edgecolor="none")
plt.close(fig)

print(f"saved -> {pdf_path}")
print(f"saved -> {png_path}")
