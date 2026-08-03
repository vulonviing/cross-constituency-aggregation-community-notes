#!/usr/bin/env python3
"""Reproduce the historical 07_fig3_pool_and_topics paper figure exactly.

Source: archive/scale-up/pre-root-executed/07_paper_visuals.executed.ipynb
Historical paper baseline: commit 40826c6
"""

import matplotlib

matplotlib.use("Agg")

# Historical notebook setup cell. Keep plotting defaults unchanged.
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.colors import LinearSegmentedColormap, to_rgba
import seaborn as sns

warnings.filterwarnings('ignore')

def find_project_root() -> Path:
    """Anchor on config.txt — safe from any subdir depth."""
    for p in [Path.cwd().resolve(), *Path.cwd().resolve().parents]:
        if (p / "config.txt").exists():
            return p
    raise RuntimeError("config.txt not found")

PROJECT_ROOT = find_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.io import (
    get_figure_dir,
    get_gabriel_dir,
    get_interim_dir,
    get_processed_dir,
    get_topic_dir,
)

INTERIM     = get_interim_dir()
PROCESSED   = get_processed_dir()
GABRIEL_DIR = get_gabriel_dir()
TOPIC_DIR   = get_topic_dir()
FIG_DIR     = get_figure_dir()
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ── Global style ─────────────────────────────────────────────────────────────
mpl.rcParams.update({
    'figure.dpi':           120,
    'savefig.dpi':          300,
    'savefig.bbox':        'tight',
    'savefig.facecolor':   'white',
    'savefig.edgecolor':   'none',
    'pdf.fonttype':         42,   # editable text in vector PDFs
    'ps.fonttype':          42,
    'font.family':          'sans-serif',
    'font.sans-serif':      ['Helvetica', 'Arial', 'DejaVu Sans'],
    'font.size':            11,
    'axes.titlesize':       13,
    'axes.titleweight':    'bold',
    'axes.labelsize':       11,
    'axes.spines.top':      False,
    'axes.spines.right':    False,
    'axes.grid':            False,
    'legend.frameon':       False,
})

PAPER_BG    = '#ffffff'
PAPER_TEXT  = '#111827'
PAPER_MUTED = '#4b5563'
PAPER_GRID  = '#e5e7eb'

# Cluster colour anchors — three distinct, print-friendly hues for a white paper page.
CLUSTER_ANCHORS = {
    0: '#2b6cb0',   # blue
    1: '#c2413f',   # red
    2: '#238b45',   # green
}

RESCUE_THRESHOLD = 50
RANDOM_SEED      = 42
rng = np.random.default_rng(RANDOM_SEED)


def save_fig(fig, name: str) -> None:
    pdf = FIG_DIR / f'{name}.pdf'
    png = FIG_DIR / f'{name}.png'
    fig.savefig(pdf, facecolor=fig.get_facecolor(), edgecolor='none')
    fig.savefig(png, facecolor=fig.get_facecolor(), edgecolor='none')
    print(f'  saved → {pdf.name} + {png.name}')

# Historical notebook data-loading cell. Keep derived values unchanged.
user_stats      = pd.read_parquet(INTERIM   / 'user_stats.parquet')
# Figure 7 only needs the rating-edge count. Reading parquet metadata keeps the
# 200k representative notebook light on 8GB machines.
ratings_clustered_path = INTERIM / 'ratings_clustered.parquet'
try:
    import pyarrow.parquet as pq
    ratings_clustered_n_rows = int(pq.ParquetFile(ratings_clustered_path).metadata.num_rows)
except Exception:
    ratings_clustered_n_rows = int(len(pd.read_parquet(ratings_clustered_path, columns=['noteId'])))
ratings_clustered = None
cluster_summary = pd.read_parquet(INTERIM   / 'cluster_summary.parquet')
scores          = pd.read_parquet(PROCESSED / 'scores.parquet')
selection_log   = pd.read_parquet(PROCESSED / 'selection_log.parquet')
topic_notes     = pd.read_parquet(TOPIC_DIR / 'topic_notes.parquet')
topic_super_parent_notes = pd.read_parquet(TOPIC_DIR / 'topic_super_parent_notes.parquet')

# ── Gabriel data availability guard ──────────────────────────────────────
import re

GABRIEL_LABEL_COL = 'predicted_classes'
GABRIEL_SCORE_COL = 'rescue_worthiness'
GABRIEL_CLUSTER_IDS = []


def _approval_cluster_ids(df: pd.DataFrame) -> list[int]:
    if df is None:
        return []
    ids = []
    for col in df.columns:
        m = re.fullmatch(r'cluster_(\d+)_approval', str(col))
        if m and f'cluster_{m.group(1)}_count' in df.columns:
            ids.append(int(m.group(1)))
    return sorted(set(ids))


_gabriel_path = GABRIEL_DIR / 'gabriel_merged.parquet'
if _gabriel_path.exists():
    gabriel_merged = pd.read_parquet(_gabriel_path)
    missing = [c for c in ('noteId', GABRIEL_LABEL_COL, GABRIEL_SCORE_COL) if c not in gabriel_merged.columns]
    if missing:
        print(f'Gabriel data found but missing columns {missing}; Gabriel-dependent sections will be skipped.')
        gabriel_merged = None
        HAS_GABRIEL = False
    else:
        gabriel_merged['noteId'] = gabriel_merged['noteId'].astype(str)
        gabriel_merged[GABRIEL_LABEL_COL] = gabriel_merged[GABRIEL_LABEL_COL].astype('string')
        gabriel_merged[GABRIEL_SCORE_COL] = pd.to_numeric(gabriel_merged[GABRIEL_SCORE_COL], errors='coerce')
        GABRIEL_CLUSTER_IDS = _approval_cluster_ids(gabriel_merged)
        HAS_GABRIEL = len(GABRIEL_CLUSTER_IDS) > 0
        if not HAS_GABRIEL:
            print('Gabriel data found but no cluster approval/count columns were detected; Gabriel-dependent sections will be skipped.')
else:
    print(f'Gabriel data not available ({_gabriel_path}). Gabriel-dependent sections will be skipped.')
    gabriel_merged = None
    HAS_GABRIEL = False

# Normalise every noteId column to str up front — upstream parquets store
# int64 in some, str in others, and pandas-3 refuses to merge across types.
for df in (ratings_clustered, scores, topic_notes, topic_super_parent_notes, gabriel_merged):
    if df is not None and 'noteId' in df.columns:
        df['noteId'] = df['noteId'].astype(str)
selection_log['selected_noteId'] = selection_log['selected_noteId'].astype(str)

# Representative pool (NMR + passes the bridge threshold)
rep_pool = (
    selection_log[
        (selection_log['strategy'] == 'Representative')
        & selection_log['passes_bridge_threshold'].fillna(False)
        & (selection_log['status'] != 'CURRENTLY_RATED_HELPFUL')
    ]
    .drop_duplicates('selected_noteId')
    .rename(columns={'selected_noteId': 'noteId'})
    .copy()
)
rep_pool = rep_pool.merge(
    topic_notes[['noteId', 'topic_label']].drop_duplicates('noteId'),
    on='noteId', how='left',
)

print(f'user_stats         : {len(user_stats):>7,}')
print(f'representative pool: {len(rep_pool):>7,}')
print(f'gabriel_merged     : {len(gabriel_merged) if HAS_GABRIEL else "N/A":>7}')
print(f'super-parent notes : {len(topic_super_parent_notes):>7,}')
if HAS_GABRIEL:
    sourced_mask = gabriel_merged[GABRIEL_LABEL_COL].eq('sourced_factual_information')
    scored_mask = sourced_mask & gabriel_merged[GABRIEL_SCORE_COL].notna()
    rescued_mask = scored_mask & gabriel_merged[GABRIEL_SCORE_COL].ge(RESCUE_THRESHOLD)
    print(f'Gabriel clusters   : {GABRIEL_CLUSTER_IDS}')
    print(f'Gabriel sourced    : {int(sourced_mask.sum()):>7,}')
    print(f'Gabriel scored     : {int(scored_mask.sum()):>7,}')
    print(f'Gabriel rescued ≥{RESCUE_THRESHOLD}: {int(rescued_mask.sum()):>7,}')

# Standalone scripts write their same-named PDF/PNG triplet beside the script.
FIG_DIR = Path(__file__).resolve().parent

# Historical figure cell 10. Keep visual constants and layout unchanged.
from matplotlib.patches import Rectangle, Circle
from matplotlib.colors import to_rgba

# ── Figure 3 base aliases ────────────────────────────────────────────────────
BG = PAPER_BG
TEXT = PAPER_TEXT
MUTED = PAPER_MUTED
GRID = '#cbd5e1'

# ── FIGURE 3 TUNE THESE: colours, lines, ticks, labels, matrix ───────────────
# Keep these independent from Figure 1 so you can tune this panel separately.
# Defaults reproduce the old Figure 3 as closely as possible.
FIG3_FIGURE_BG_COLOR = BG
FIG3_AXES_BG_COLOR = BG

# Optional figure title. Leave blank to keep the current no-title layout.
FIG3_TITLE = ''
FIG3_TITLE_COLOR = TEXT
FIG3_TITLE_FONTSIZE = 11.0
FIG3_TITLE_PAD = 8

# Main horizontal pipeline bars.
FIG3_STAGE_BAR_COLORS = {
    'english': '#1C2540',
    'valid': '#1A3F7A',
    'eligible': '#0A84FF',
}
FIG3_STAGE_BAR_EDGE_COLOR = 'none'
FIG3_STAGE_BAR_EDGE_WIDTH = 0.0
FIG3_STAGE_LABEL_COLOR = '#ffffff'
FIG3_STAGE_SUBTITLE_COLOR = '#ffffff'
FIG3_STAGE_LABEL_ALPHA = 1.0
FIG3_STAGE_SUBTITLE_ALPHA = 1.0

# Dense-core overlay inside the eligible-notes bar.
FIG3_DENSE_CORE_FILL_COLOR = '#1C1C1E'
FIG3_DENSE_CORE_ALPHA = 1.0
FIG3_DENSE_CORE_EDGE_COLOR = 'none'
FIG3_DENSE_CORE_EDGE_WIDTH = 0.0

# Top-20% annotation near the dense-core cut.
FIG3_TOP_LABEL_COLOR = '#1C1C1E'
FIG3_TOP_LABEL_FONTSIZE = 7.7
FIG3_TOP_LABEL_FONTWEIGHT = 'bold'
FIG3_ARROW_COLOR = '#1C1C1E'
FIG3_ARROW_LINE_WIDTH = 1.05
FIG3_ARROW_STYLE = '-|>'

# Main x-axis and manual bottom tick labels.
FIG3_BOTTOM_TICK_MARK_COLOR = '#1C1C1E'
FIG3_BOTTOM_TICK_LABEL_COLOR = '#2C2C2E'
FIG3_BOTTOM_TICK_WIDTH = 1.0
FIG3_BOTTOM_TICK_LENGTH = 5
FIG3_BOTTOM_SPINE_COLOR = '#1C1C1E'
FIG3_BOTTOM_SPINE_WIDTH = 1.0
FIG3_XLABEL_COLOR = '#1C1C1E'
FIG3_XLABEL_FONTSIZE = 9.0

# Top percentage axis.
FIG3_TOP_TICK_MARK_COLOR = '#1C1C1E'
FIG3_TOP_TICK_LABEL_COLOR = '#2C2C2E'
FIG3_TOP_TICK_WIDTH = 1.0
FIG3_TOP_TICK_LENGTH = 4
FIG3_TOP_SPINE_COLOR = '#1C1C1E'
FIG3_TOP_SPINE_WIDTH = 1.0

# Vertical guide lines at eligible / English note counts.
# Core / 100k guide line removed.
FIG3_GUIDE_LINE_COLOR = '#F2F2F7'
FIG3_GUIDE_LINE_STYLE = '-'
FIG3_GUIDE_LINE_WIDTH = 0.8
FIG3_GUIDE_LINE_ALPHA = 1.0

# Connector from dense-core bar segment to the matrix inset.
FIG3_CONNECTOR_COLOR = '#1C1C1E'
FIG3_CONNECTOR_STYLE = (0, (1.2, 2.0))
FIG3_CONNECTOR_WIDTH = 1.0
FIG3_CONNECTOR_ALPHA = 1.0

# Matrix inset text.
FIG3_MATRIX_TITLE_COLOR = TEXT
FIG3_MATRIX_NOTE_TEXT_COLOR = MUTED
FIG3_MATRIX_AXIS_LABEL_COLOR = MUTED

# Matrix inset frame, fill, grid, and dots.
FIG3_MATRIX_FACE_COLOR = '#ffffff'
FIG3_MATRIX_BORDER_COLOR = '#111827'
FIG3_MATRIX_TINT_COLOR = '#dbeafe'
FIG3_MATRIX_TINT_ALPHA = 0.25
FIG3_MATRIX_GRID_COLOR = '#111827'
FIG3_MATRIX_GRID_ALPHA = 0.16
FIG3_MATRIX_DOT_COLOR = '#2563eb'
FIG3_MATRIX_DOT_EDGE_COLOR = 'none'
FIG3_MATRIX_DOT_EDGE_WIDTH = 0.0

# Manual tick-label text values and colours.
# 100k bottom tick label removed.
FIG3_BOTTOM_TICK_LABELS = {
    'zero': '0',
    'eligible': '510k',
    'english': '1.7M',
}
FIG3_TOP_TICK_LABELS = {
    'eligible': '30.1%',
    'english': '100%',
}

english_notes = 1_693_711
valid_notes = 533_510
eligible_notes = 510_212
core_notes = 100_000
visual_core_notes = 100_000
DENSE_CORE_BAR_BLACK_ALPHA = FIG3_DENSE_CORE_ALPHA
selected_users = int(user_stats['raterParticipantId'].nunique()) if 'user_stats' in globals() else 200_000
core_share_eligible = core_notes / eligible_notes
core_share_english = core_notes / english_notes

# More compact vertical figure.
fig = plt.figure(figsize=(7.2, 2.65), facecolor=FIG3_FIGURE_BG_COLOR)
ax = fig.add_axes([0.075, 0.27, 0.60, 0.58])
ax.set_facecolor(FIG3_AXES_BG_COLOR)

if FIG3_TITLE:
    ax.set_title(FIG3_TITLE, color=FIG3_TITLE_COLOR, fontsize=FIG3_TITLE_FONTSIZE, pad=FIG3_TITLE_PAD)

stages = [
    ('English notes', english_notes, 'analytic baseline after language filtering', FIG3_STAGE_BAR_COLORS['english']),
    ('Valid notes', valid_notes, '>=3 English notes/tweet', FIG3_STAGE_BAR_COLORS['valid']),
    ('Eligible notes', eligible_notes, '>=3 ratings within 48h', FIG3_STAGE_BAR_COLORS['eligible']),
]

# Bars brought closer together vertically.
ys = [1.70, 0.85, 0.0]
bar_h = 0.60

# Shared left text anchor for all bar labels.
# Smaller = more left.
BAR_TEXT_X = 18_000

for y, (label, count, subtitle, color) in zip(ys, stages):
    ax.barh(
        y, count, height=bar_h, color=color,
        edgecolor=FIG3_STAGE_BAR_EDGE_COLOR, linewidth=FIG3_STAGE_BAR_EDGE_WIDTH,
        zorder=2,
    )

    # English notes was previously pushed right because count * 0.035 was large.
    # Now all stage labels use the same left anchor.
    ax.text(
        BAR_TEXT_X, y + 0.10, label,
        ha='left', va='center',
        fontsize=8.8, fontweight='bold',
        color=FIG3_STAGE_LABEL_COLOR,
        alpha=FIG3_STAGE_LABEL_ALPHA
    )
    ax.text(
        BAR_TEXT_X, y - 0.10, subtitle,
        ha='left', va='center',
        fontsize=6.7,
        color=FIG3_STAGE_SUBTITLE_COLOR,
        alpha=FIG3_STAGE_SUBTITLE_ALPHA
    )

# Highlight the dense-core note cut inside Bar 3 instead of drawing a separate Bar 4.
visual_core_x0 = eligible_notes - visual_core_notes
ax.add_patch(Rectangle(
    (visual_core_x0, ys[-1] - bar_h / 2),
    visual_core_notes,
    bar_h,
    facecolor=to_rgba(FIG3_DENSE_CORE_FILL_COLOR, DENSE_CORE_BAR_BLACK_ALPHA),
    edgecolor=FIG3_DENSE_CORE_EDGE_COLOR,
    linewidth=FIG3_DENSE_CORE_EDGE_WIDTH,
    zorder=4,
))

# --- Manual tuning knobs for the top-20% label and arrow ---------------------
# Slightly moved right on the x-axis.
TOP_LABEL_DX = 14_000
TOP_LABEL_DY = -bar_h * 0.28
ARROW_HEAD_DX = 5_000
ARROW_HEAD_DY = -bar_h * 0.28
ARROW_TAIL_DX_FROM_LABEL = -14_000

label_x = eligible_notes + TOP_LABEL_DX
label_y = ys[-1] + TOP_LABEL_DY
ax.text(
    label_x, label_y, 'top 20%',
    ha='left', va='center',
    fontsize=FIG3_TOP_LABEL_FONTSIZE,
    fontweight=FIG3_TOP_LABEL_FONTWEIGHT,
    color=FIG3_TOP_LABEL_COLOR
)
# Arrow removed; the compact label now sits immediately right of the dense-core segment.

ax.set_xlim(-25_000, 1_800_000)

# More compact vertical limits.
ax.set_ylim(-0.62, 2.18)

ax.set_yticks([])

# Core / 100k vertical guide line removed.
for x in [eligible_notes, english_notes]:
    ax.axvline(
        x,
        color=FIG3_GUIDE_LINE_COLOR,
        linestyle=FIG3_GUIDE_LINE_STYLE,
        linewidth=FIG3_GUIDE_LINE_WIDTH,
        alpha=FIG3_GUIDE_LINE_ALPHA,
        zorder=0,
    )

# Core / 100k tick mark removed from bottom x-axis.
ax.set_xticks([0, eligible_notes, english_notes])
ax.set_xticklabels(['', '', ''])
ax.tick_params(
    axis='x',
    length=FIG3_BOTTOM_TICK_LENGTH,
    width=FIG3_BOTTOM_TICK_WIDTH,
    color=FIG3_BOTTOM_TICK_MARK_COLOR,
    labelcolor=FIG3_BOTTOM_TICK_LABEL_COLOR,
)

for spine in ['left', 'right', 'top']:
    ax.spines[spine].set_visible(False)
ax.spines['bottom'].set_color(FIG3_BOTTOM_SPINE_COLOR)
ax.spines['bottom'].set_linewidth(FIG3_BOTTOM_SPINE_WIDTH)

# Bottom manual ticks. 100k label removed.
trans = ax.get_xaxis_transform()
manual_ticks = [
    (0, FIG3_BOTTOM_TICK_LABELS['zero'], -0.115, 'center'),
    (eligible_notes, FIG3_BOTTOM_TICK_LABELS['eligible'], -0.115, 'center'),
    (english_notes, FIG3_BOTTOM_TICK_LABELS['english'], -0.115, 'center'),
]

for x, label, yoff, ha in manual_ticks:
    if label:
        ax.text(
            x, yoff, label,
            transform=trans,
            ha=ha,
            va='top',
            fontsize=8.4,
            color=FIG3_BOTTOM_TICK_LABEL_COLOR
        )

# Bottom x-axis label removed:
# ax.set_xlabel('Absolute note count', fontsize=FIG3_XLABEL_FONTSIZE,
#               color=FIG3_XLABEL_COLOR, labelpad=16)

ax_top = ax.twiny()
ax_top.set_xlim(ax.get_xlim())

# Core / 5.9% top tick removed.
ax_top.set_xticks([eligible_notes, english_notes])
ax_top.set_xticklabels(
    [FIG3_TOP_TICK_LABELS['eligible'], FIG3_TOP_TICK_LABELS['english']],
    fontsize=8.4,
    color=FIG3_TOP_TICK_LABEL_COLOR,
)

ax_top.tick_params(
    axis='x',
    colors=FIG3_TOP_TICK_MARK_COLOR,
    labelcolor=FIG3_TOP_TICK_LABEL_COLOR,
    length=FIG3_TOP_TICK_LENGTH,
    width=FIG3_TOP_TICK_WIDTH,
)
ax_top.spines['top'].set_color(FIG3_TOP_SPINE_COLOR)
ax_top.spines['top'].set_linewidth(FIG3_TOP_SPINE_WIDTH)

for spine in ['left', 'right', 'bottom']:
    ax_top.spines[spine].set_visible(False)

# Schematic matrix drawn inside the bar-plot whitespace, not as a separate panel.
# --- Manual tuning knobs for the matrix inset -----------------------------
# MATRIX_X/Y move the whole matrix block. MATRIX_W/H resize it on x/y axes.
# MATRIX_SCALE grows/shrinks all matrix-related text, ticks, dots, borders,
# and grid lines together after you change MATRIX_W/H.
MATRIX_X = 1_130_000

# Matrix bottom aligned with the bottom edge of the lowest bar.
MATRIX_Y = ys[-1] - bar_h / 2

# Matrix made very slightly larger.
MATRIX_W = 530_000
MATRIX_H = 1.16
MATRIX_SCALE = 1.0

MATRIX_TITLE_SIZE = 9.2 * MATRIX_SCALE
MATRIX_NOTE_SIZE = 7.0 * MATRIX_SCALE
MATRIX_AXIS_SIZE = 6.6 * MATRIX_SCALE
MATRIX_DOT_SIZE = 13 * (MATRIX_SCALE ** 2)
MATRIX_BORDER_LW = 0.9 * MATRIX_SCALE
MATRIX_GRID_LW = 0.45 * MATRIX_SCALE

# Position knobs for matrix text labels. X offsets are note-count units;
# Y offsets are chart bar-y units. Increase DX to move right, DY to move up.
DENSE_CORE_TITLE_DX = 0

# Dense core title vertical controls.
# Increase DENSE_CORE_TITLE_Y_SHIFT to move up, decrease to move down.
DENSE_CORE_TITLE_DY = 0.35 * MATRIX_SCALE
DENSE_CORE_TITLE_Y_SHIFT = 0.00

MATRIX_NOTE_DX = 0
MATRIX_NOTE_DY = 0.35 * MATRIX_SCALE

# Switched: users on top, notes on the left.
USERS_LABEL_TOP_DX = 0
USERS_LABEL_TOP_DY = 0.010 * MATRIX_SCALE
NOTES_LABEL_LEFT_DX = -0.10 * MATRIX_SCALE
NOTES_LABEL_LEFT_DY = 0

# Connector tuning.
# CONNECTOR_MATRIX_END_DX controls where the dotted connector ends on the x-axis.
# Negative values move the endpoint left of the matrix edge; positive values move it right.
CONNECTOR_MATRIX_END_DX = -43_000

# 0.50 means the endpoint is vertically centered within the matrix.
# 0.00 = matrix bottom, 1.00 = matrix top.
CONNECTOR_MATRIX_END_Y_FRAC = 0.50

# Connector from dense-core cut to matrix inset.
ax.plot(
    [visual_core_x0 + visual_core_notes, MATRIX_X + CONNECTOR_MATRIX_END_DX],
    [ys[-1], MATRIX_Y + MATRIX_H * CONNECTOR_MATRIX_END_Y_FRAC],
    color=FIG3_CONNECTOR_COLOR,
    alpha=FIG3_CONNECTOR_ALPHA,
    linestyle=FIG3_CONNECTOR_STYLE,
    linewidth=FIG3_CONNECTOR_WIDTH * MATRIX_SCALE,
    zorder=4,
)

ax.text(
    MATRIX_X + DENSE_CORE_TITLE_DX,
    MATRIX_Y + MATRIX_H + DENSE_CORE_TITLE_DY + DENSE_CORE_TITLE_Y_SHIFT,
    'Dense core',
    ha='left',
    va='top',
    fontsize=MATRIX_TITLE_SIZE,
    fontweight='bold',
    color=FIG3_MATRIX_TITLE_COLOR
)

# Matrix count text removed; counts are now carried by the matrix axis labels.
MATRIX_NOTE_X = MATRIX_X + MATRIX_NOTE_DX
MATRIX_NOTE_Y = MATRIX_Y + MATRIX_H + MATRIX_NOTE_DY

ax.add_patch(Rectangle(
    (MATRIX_X, MATRIX_Y),
    MATRIX_W,
    MATRIX_H,
    facecolor=FIG3_MATRIX_FACE_COLOR,
    edgecolor=FIG3_MATRIX_BORDER_COLOR,
    lw=MATRIX_BORDER_LW,
    zorder=5
))

ax.add_patch(Rectangle(
    (MATRIX_X, MATRIX_Y),
    MATRIX_W,
    MATRIX_H,
    facecolor=to_rgba(FIG3_MATRIX_TINT_COLOR, FIG3_MATRIX_TINT_ALPHA),
    edgecolor='none',
    zorder=5
))

for i in range(1, 6):
    x = MATRIX_X + MATRIX_W * i / 6
    ax.plot(
        [x, x],
        [MATRIX_Y, MATRIX_Y + MATRIX_H],
        color=to_rgba(FIG3_MATRIX_GRID_COLOR, FIG3_MATRIX_GRID_ALPHA),
        lw=MATRIX_GRID_LW,
        zorder=6
    )

for j in range(1, 5):
    y_grid = MATRIX_Y + MATRIX_H * j / 5
    ax.plot(
        [MATRIX_X, MATRIX_X + MATRIX_W],
        [y_grid, y_grid],
        color=to_rgba(FIG3_MATRIX_GRID_COLOR, FIG3_MATRIX_GRID_ALPHA),
        lw=MATRIX_GRID_LW,
        zorder=6
    )

filled = [
    (0, 0), (0, 1), (0, 2), (0, 4),
    (1, 0), (1, 1), (1, 3), (1, 5),
    (2, 0), (2, 2), (2, 3), (2, 4),
    (3, 1), (3, 2), (3, 4), (3, 5),
    (4, 0), (4, 2), (4, 3), (4, 5)
]

for r, c in filled:
    cx = MATRIX_X + MATRIX_W * (c + 0.5) / 6
    cy = MATRIX_Y + MATRIX_H * (5 - r - 0.5) / 5
    ax.scatter(
        [cx],
        [cy],
        s=MATRIX_DOT_SIZE,
        color=FIG3_MATRIX_DOT_COLOR,
        edgecolors=FIG3_MATRIX_DOT_EDGE_COLOR,
        linewidths=FIG3_MATRIX_DOT_EDGE_WIDTH,
        zorder=7
    )

# Switched labels:
# users is now on top.
ax.text(
    MATRIX_X + MATRIX_W / 2 + USERS_LABEL_TOP_DX,
    MATRIX_Y + MATRIX_H + USERS_LABEL_TOP_DY,
    'users - 200.000',
    ha='center',
    va='bottom',
    fontsize=MATRIX_AXIS_SIZE,
    color=FIG3_MATRIX_AXIS_LABEL_COLOR
)

# notes is now on the left.
ax.text(
    MATRIX_X + NOTES_LABEL_LEFT_DX,
    MATRIX_Y + MATRIX_H / 2 + NOTES_LABEL_LEFT_DY,
    'notes - 100.000',
    ha='right',
    va='center',
    rotation=90,
    fontsize=MATRIX_AXIS_SIZE,
    color=FIG3_MATRIX_AXIS_LABEL_COLOR
)

# No bottom explanatory paragraph; caption text should live in LaTeX.
save_fig(fig, '07_fig3_pool_and_topics')
plt.show()
