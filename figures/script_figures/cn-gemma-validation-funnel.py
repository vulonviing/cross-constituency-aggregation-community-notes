"""
cn-gemma-validation-funnel.py
──────────────────────────────
Funnel view of the Gemma two-stage validation over the CCA hidden rescue pool.
Stage 1.5 (opinion-recall) is folded into Stage 1, as its outcome (+280 notes
recovered) only ever affects which notes reach Stage 2.

Two equally sized, aligned horizontal bars. Each bar uses its full width to
show that stage's own outcome breakdown; the right-edge labels report the
different stage populations:

  Row 1 — Stage 1 content screen, over the full 13,655-note rescue pool.
          Segments: pass (strict) / recovered via Stage 1.5 / four drop reasons.
  Row 2 — Stage 2 rescue-worthiness scoring, over the 10,376 notes that passed
          Stage 1. Segments: six score bins, three below the 50 threshold
          (grey, ascending severity) and three at or above it (green, ascending
          confidence).

All values are hardcoded from the frozen validation run summaries:
  data/llm_validation/runs/gemma-4-31b-it-scckn-v1/summary.json
  data/llm_validation/runs/gemma-4-31b-it-scckn-stage1-5-opinion-v1/summary.json
  data/llm_validation/runs/gemma-4-31b-it-scckn-stage2-expanded-v1/summary.json

Outputs (same basename triplet per figures/README.md):
  cn-gemma-validation-funnel.pdf
  cn-gemma-validation-funnel.png

Run:
  cd figures/script_figures
  python cn-gemma-validation-funnel.py
"""

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Output paths ────────────────────────────────────────────────────────────
HERE = pathlib.Path(__file__).parent
PDF_OUT = HERE / "cn-gemma-validation-funnel.pdf"
PNG_OUT = HERE / "cn-gemma-validation-funnel.png"

# ── Global style — matches fig3-rescue-panels.py for cross-figure consistency
mpl.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
    "savefig.edgecolor": "none",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "legend.frameon": False,
})

# ── Palette — reuses the paper's established hexes ─────────────────────────
PAPER_BG = "#ffffff"
PAPER_TEXT = "#111827"
MUTED = "#4b5563"

PASS_COLOR = "#5FA8A3"        # Stage 1 strict pass (teal — matches "Already shown")
RECOVER_COLOR = "#8FC7C2"     # Stage 1.5 recovered notes (lighter teal tint)
OPINION_COLOR = "#E5A823"     # opinion, no factual core (amber — matches "Content stop")
IRRELEVANT_COLOR = "#9CA3AF"  # irrelevant / trivial / spam (grey)
UNSOURCED_COLOR = "#f97316"   # unsourced context or claim (orange)
HOSTILE_COLOR = "#D70015"     # hostile / troll + 1 unresolved (red)

# Stage 2 score bins — sequential ramps (grey = below threshold, green = validated)
BIN_0_9 = "#E5E7EB"
BIN_10_39 = "#C4C8CE"
BIN_40_49 = "#9CA3AF"
BIN_50_69 = "#BBF7D0"
BIN_70_89 = "#4ADE80"
BIN_90_100 = "#16A34A"

EDGE_COL = "white"
EDGE_LW = 1.2

# ── Hardcoded pipeline numbers (frozen; see summary.json paths above) ──────
POOL_N = 13_655

# Stage 1 (incl. Stage 1.5 recall) — segments of the full pool
S1_PASS_STRICT = 10_096
S1_RECOVERED = 280        # Stage 1.5: sourced_factual_core_present
S1_OPINION_DROP = 1_423   # Stage 1.5: sourced_factual_core_absent
S1_IRRELEVANT = 1_340
S1_UNSOURCED = 373
S1_HOSTILE_UNRESOLVED = 142 + 1   # hostile_troll_or_derogatory + 1 unresolved
assert (S1_PASS_STRICT + S1_RECOVERED + S1_OPINION_DROP + S1_IRRELEVANT
        + S1_UNSOURCED + S1_HOSTILE_UNRESOLVED) == POOL_N

STAGE1_PASS_TOTAL = S1_PASS_STRICT + S1_RECOVERED   # 10,376 → enters Stage 2
STAGE1_DROP_TOTAL = POOL_N - STAGE1_PASS_TOTAL       # 3,279 content-screen stops

# Stage 2 — score bins over the 10,376 notes that passed Stage 1
S2_BIN_0_9 = 8
S2_BIN_10_39 = 1_547
S2_BIN_40_49 = 263
S2_BIN_50_69 = 1_212
S2_BIN_70_89 = 2_923
S2_BIN_90_100 = 4_423
assert (S2_BIN_0_9 + S2_BIN_10_39 + S2_BIN_40_49 + S2_BIN_50_69 + S2_BIN_70_89
        + S2_BIN_90_100) == STAGE1_PASS_TOTAL

STAGE2_BELOW_50 = S2_BIN_0_9 + S2_BIN_10_39 + S2_BIN_40_49   # 1,818
STAGE2_VALIDATED = S2_BIN_50_69 + S2_BIN_70_89 + S2_BIN_90_100  # 8,558

# Final reconciliation across the whole funnel
assert STAGE2_VALIDATED + STAGE2_BELOW_50 + STAGE1_DROP_TOTAL == POOL_N
assert STAGE2_VALIDATED == 8_558
assert STAGE1_DROP_TOTAL == 3_279
assert STAGE2_BELOW_50 == 1_818

# ── Bar widths (data units), centered — both stages use the same visual span
MAX_WIDTH = 100.0
ROW1_WIDTH = MAX_WIDTH
ROW2_WIDTH = MAX_WIDTH

# ── LAYOUT — tune these; everything below is derived ───────────────────────
# Canvas width is kept near the paper's other figures (5.2-6.4 in) so that text
# stays legible once the figure is scaled down to one column width.
FIG_W, FIG_H = 6.4, 3.19          # overall canvas
AX_RECT = [0.015, 0.015, 0.97, 0.97]    # one axes; every element sits in data space

FS_IN_BAR = 10.5                   # percentages printed inside the segments
FS_NLABEL = 9.8                   # right-edge n = ... labels
FS_FOOT = 9.5                     # below-bar summary annotations
FS_LEGEND = 9.5                    # matches Figure 3's manual legend text
FS_STAGE2_HEAD = 9.5               # transition heading above the Stage 2 legend

BAR_H = 0.50
ROW1_Y = 2.10                     # Stage 1 bar centre (data units)
ROW2_Y = 0.44                     # Stage 2 bar centre
XLIM = (-53.0, 74.0)              # tight left margin; right side holds n-labels
YLIM = (-0.34, 3.24)

NLABEL_DX = 2.4                   # right-edge n-label offset from bar end
FOOT_DY = 0.13                    # below-bar annotation offset

# Each legend is anchored in data coordinates so it tracks its own bar and is
# flush with that bar's left edge. Stage 2 adds a short transition heading
# above its legend; the two stage blocks retain a larger gap between them.
LEG1_ANCHOR = (-50.0, 3.03)
STAGE2_HEAD_Y = 1.55
LEG2_ANCHOR = (-50.0, 1.38)


def centered_span(width):
    return (-width / 2.0, width / 2.0)


# ── Figure — axes rectangle explicitly reserved so legends sit right under
#    the content with no wasted blank band (fig-fraction legends, not
#    data-space anchored) ──────────────────────────────────────────────────
fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=PAPER_BG)
ax = fig.add_axes(AX_RECT)
ax.set_facecolor(PAPER_BG)
ax.set_xlim(*XLIM)
ax.set_ylim(*YLIM)
ax.set_xticks([])
ax.set_yticks([])
for sp in ax.spines.values():
    sp.set_visible(False)

# ── Row 1 — Stage 1 content screen (pool = 13,655) ─────────────────────────
x0_1, x1_1 = centered_span(ROW1_WIDTH)
row1_segments = [
    (S1_PASS_STRICT / POOL_N * ROW1_WIDTH, PASS_COLOR, False),
    (S1_RECOVERED / POOL_N * ROW1_WIDTH, RECOVER_COLOR, True),
    (S1_OPINION_DROP / POOL_N * ROW1_WIDTH, OPINION_COLOR, False),
    (S1_IRRELEVANT / POOL_N * ROW1_WIDTH, IRRELEVANT_COLOR, False),
    (S1_UNSOURCED / POOL_N * ROW1_WIDTH, UNSOURCED_COLOR, False),
    (S1_HOSTILE_UNRESOLVED / POOL_N * ROW1_WIDTH, HOSTILE_COLOR, False),
]
row1_counts = [S1_PASS_STRICT, S1_RECOVERED, S1_OPINION_DROP, S1_IRRELEVANT,
               S1_UNSOURCED, S1_HOSTILE_UNRESOLVED]

x = x0_1
for (frac, color, hatch), n in zip(row1_segments, row1_counts):
    ax.barh(ROW1_Y, frac, left=x, height=BAR_H, color=color,
            edgecolor=EDGE_COL, linewidth=EDGE_LW, zorder=3,
            hatch="//" if hatch else None)
    pct = n / POOL_N * 100
    if frac >= ROW1_WIDTH * 0.045:
        ax.text(x + frac / 2, ROW1_Y, f"{pct:.0f}%", ha="center", va="center",
                 fontsize=FS_IN_BAR, fontweight="bold", color="white", zorder=4)
    x += frac

# Right-edge population label.
ax.text(x1_1 + NLABEL_DX, ROW1_Y, f"n = {POOL_N:,}\n(100% of pool)",
        ha="left", va="center", fontsize=FS_NLABEL, color=MUTED)

# ── Row 2 — Stage 2 rescue-worthiness (population = 10,376) ────────────────
x0_2, x1_2 = centered_span(ROW2_WIDTH)
row2_segments = [
    (S2_BIN_0_9, BIN_0_9),
    (S2_BIN_10_39, BIN_10_39),
    (S2_BIN_40_49, BIN_40_49),
    (S2_BIN_50_69, BIN_50_69),
    (S2_BIN_70_89, BIN_70_89),
    (S2_BIN_90_100, BIN_90_100),
]
x = x0_2
threshold_x = None
below50_x_mid = None
validated_x_mid = None
below50_start = x0_2
for i, (n, color) in enumerate(row2_segments):
    frac = n / STAGE1_PASS_TOTAL * ROW2_WIDTH
    # The 50-69 bin is a pale green; only the two darkest bins take white text.
    text_color = PAPER_TEXT if i < 4 else "white"
    ax.barh(ROW2_Y, frac, left=x, height=BAR_H, color=color,
            edgecolor=EDGE_COL, linewidth=EDGE_LW, zorder=3)
    pct = n / STAGE1_PASS_TOTAL * 100
    if frac >= ROW2_WIDTH * 0.05:
        ax.text(x + frac / 2, ROW2_Y, f"{pct:.0f}%", ha="center", va="center",
                 fontsize=FS_IN_BAR, fontweight="bold", color=text_color, zorder=4)
    x += frac
    if i == 2:  # boundary between 40-49 and 50-69 = the rescue threshold
        threshold_x = x
        below50_x_mid = (below50_start + x) / 2.0
        validated_x_mid = (x + x1_2) / 2.0

# Threshold marker — spans just the bar height; the below-50 annotation makes
# the boundary explicit without adding another label beside the bar.
ax.plot([threshold_x, threshold_x], [ROW2_Y - BAR_H / 2 - 0.05, ROW2_Y + BAR_H / 2 + 0.05],
        color=PAPER_TEXT, linewidth=1.3, linestyle="--", zorder=5)

# Right-edge population label.
ax.text(x1_2 + NLABEL_DX, ROW2_Y, f"n = {STAGE1_PASS_TOTAL:,}\n(76.0% of pool)",
        ha="left", va="center", fontsize=FS_NLABEL, color=MUTED)

# Below-bar summary annotations, centered under their own segment group
ax.text(below50_x_mid, ROW2_Y - BAR_H / 2 - FOOT_DY,
        f"{STAGE2_BELOW_50:,} below 50\n(13.3% of pool)",
        ha="center", va="top", fontsize=FS_FOOT, color=MUTED)
ax.text(validated_x_mid, ROW2_Y - BAR_H / 2 - FOOT_DY,
        f"{STAGE2_VALIDATED:,} validated\n(62.7% of pool)",
        ha="center", va="top", fontsize=FS_FOOT, fontweight="bold", color=BIN_90_100)

# ── Stage 2 transition heading ─────────────────────────────────────────────
# Reports how many notes enter Stage 2, then keeps the legend and bar beneath
# it visually close as one stage block.
ax.text(x0_2, STAGE2_HEAD_Y,
        f"{STAGE1_PASS_TOTAL:,} notes pass Stage 1 (76.0% of pool)",
        ha="left", va="top", fontsize=FS_STAGE2_HEAD,
        fontweight="bold", color=PASS_COLOR)

# ── Legends — each anchored in data space above the stage it explains ──────
stage1_patches = [
    mpatches.Patch(facecolor=PASS_COLOR, edgecolor=EDGE_COL, label="Pass (strict)"),
    mpatches.Patch(facecolor=RECOVER_COLOR, edgecolor=EDGE_COL, hatch="//",
                    label="Recovered via Stage 1.5 (+280)"),
    mpatches.Patch(facecolor=OPINION_COLOR, edgecolor=EDGE_COL, label="Opinion, no factual core"),
    mpatches.Patch(facecolor=IRRELEVANT_COLOR, edgecolor=EDGE_COL, label="Irrelevant or spam"),
    mpatches.Patch(facecolor=UNSOURCED_COLOR, edgecolor=EDGE_COL, label="Unsourced claim"),
    mpatches.Patch(facecolor=HOSTILE_COLOR, edgecolor=EDGE_COL, label="Hostile (+1 unresolved)"),
]
leg1 = ax.legend(handles=stage1_patches, fontsize=FS_LEGEND, loc="upper left",
                   bbox_to_anchor=LEG1_ANCHOR, bbox_transform=ax.transData,
                   ncol=3, frameon=True,
                   alignment="left",
                   handlelength=1.4, handletextpad=0.5,
                   columnspacing=1.4, labelspacing=0.45)
# Opaque white frame with no border keeps the legend block visually clean.
leg1.get_frame().set_facecolor(PAPER_BG)
leg1.get_frame().set_edgecolor("none")
ax.add_artist(leg1)

# Legends fill column-major, so this order renders as two readable rows:
# the three below-threshold bins on top, the three validated bins beneath.
# The two palest swatches take a grey edge; a white one would vanish.
PALE_EDGE = "#D1D5DB"
stage2_patches = [
    mpatches.Patch(facecolor=BIN_0_9, edgecolor=PALE_EDGE, label="0–9"),
    mpatches.Patch(facecolor=BIN_50_69, edgecolor=PALE_EDGE, label="50–69"),
    mpatches.Patch(facecolor=BIN_10_39, edgecolor=EDGE_COL, label="10–39"),
    mpatches.Patch(facecolor=BIN_70_89, edgecolor=EDGE_COL, label="70–89"),
    mpatches.Patch(facecolor=BIN_40_49, edgecolor=EDGE_COL, label="40–49"),
    mpatches.Patch(facecolor=BIN_90_100, edgecolor=EDGE_COL, label="90–100"),
]
leg2 = ax.legend(handles=stage2_patches, fontsize=FS_LEGEND, loc="upper left",
                   bbox_to_anchor=LEG2_ANCHOR, bbox_transform=ax.transData,
                   ncol=3, frameon=True,
                   alignment="left",
                   handlelength=1.4, handletextpad=0.5,
                   columnspacing=1.4, labelspacing=0.45)
leg2.get_frame().set_facecolor(PAPER_BG)
leg2.get_frame().set_edgecolor("none")
ax.add_artist(leg2)

# ── Save ─────────────────────────────────────────────────────────────────────
fig.savefig(PDF_OUT, facecolor=fig.get_facecolor(), edgecolor="none")
fig.savefig(PNG_OUT, facecolor=fig.get_facecolor(), edgecolor="none")
print(f"Saved: {PDF_OUT}")
print(f"Saved: {PNG_OUT}")
print(f"Reconciliation: pool={POOL_N:,} -> stage1 pass={STAGE1_PASS_TOTAL:,} "
      f"(drop {STAGE1_DROP_TOTAL:,}) -> stage2 validated={STAGE2_VALIDATED:,} "
      f"(below 50: {STAGE2_BELOW_50:,})")
plt.close(fig)
