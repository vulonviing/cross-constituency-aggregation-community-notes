#!/usr/bin/env python3
"""Render the CCA and Gemma rescue panels used as Figure 3 of the paper.

The panel layout is ported from the historical 07_paper_visuals notebook; the
values it plots are the canonical pipeline and Gemma validation outcomes.
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
    get_expanded_stage2_validation_dir,
    get_processed_dir,
)

PROCESSED = get_processed_dir()
STAGE2_DIR = get_expanded_stage2_validation_dir()
FIG_DIR = Path(__file__).resolve().parent
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

scores = pd.read_parquet(PROCESSED / 'scores.parquet')
selection_log = pd.read_parquet(PROCESSED / 'selection_log.parquet')
stage2_results = pd.read_parquet(STAGE2_DIR / 'stage2_results.parquet')

# Upstream parquets mix integer and string note IDs.
scores['noteId'] = scores['noteId'].astype(str)
selection_log['selected_noteId'] = selection_log['selected_noteId'].astype(str)
stage2_results['noteId'] = stage2_results['noteId'].astype(str)

# Historical figure cell 12. Keep visual constants and layout unchanged.
import numpy as np
from matplotlib.patches import Rectangle

# --------------------------------------------------------------------
# GROUP 1 LEFT TICKER POSITION CONTROLS
# --------------------------------------------------------------------
# Row 1: CN square + Hidden square
GROUP1_ROW1_CN_X = -4
GROUP1_ROW1_PLUS_X = -6
GROUP1_ROW1_HIDDEN_X = -10

# Row 2: CN square + Rescue Pool square + Hidden square
GROUP1_ROW2_CN_X = -4
GROUP1_ROW2_PLUS_1_X = -6
GROUP1_ROW2_RESCUE_X = -10
GROUP1_ROW2_PLUS_2_X = -12
GROUP1_ROW2_HIDDEN_X = -16

# --------------------------------------------------------------------
# GROUP 3 LEFT TICKER POSITION CONTROLS
# --------------------------------------------------------------------
# Row 1: Rescue Pool square + By both square
GROUP3_ROW1_RESCUE_X = -10
GROUP3_ROW1_PLUS_X = -6
GROUP3_ROW1_BY_BOTH_X = -4

# Row 2: CCR Pool square
GROUP3_ROW2_CCR_X = -4

# --------------------------------------------------------------------
# Colors
# --------------------------------------------------------------------
COLOR_SHOWN_BY_CN = '#636366'
COLOR_RESCUED     = '#7A3FF2'
COLOR_HIDDEN      = '#AEAEB2'
COLOR_HIDDEN_TEXT = '#374151'
COLOR_TEXT        = '#111827'
COLOR_ON_DARK     = 'white'
COLOR_BG          = 'white'

# Group 1 left ticker colors
GROUP1_LABEL_CN_COLOR = COLOR_SHOWN_BY_CN
GROUP1_LABEL_RESCUE_COLOR = COLOR_RESCUED
GROUP1_LABEL_HIDDEN_COLOR = COLOR_HIDDEN
GROUP1_LABEL_PLUS_COLOR = COLOR_TEXT

# Group 2 left ticker colors
GROUP2_LABEL_CN_COLOR = COLOR_SHOWN_BY_CN
GROUP2_LABEL_RESCUE_COLOR = COLOR_RESCUED
GROUP2_LABEL_PLUS_COLOR = COLOR_TEXT

# Group 3 left ticker colors
GROUP3_LABEL_RESCUE_COLOR = COLOR_RESCUED
GROUP3_LABEL_CCR_COLOR = COLOR_RESCUED

CLUSTER_COLORS = {
    0: '#0A84FF',
    1: '#D70015',
}
CLUSTER_LABELS = {
    0: 'Cluster 1',
    1: 'Cluster 2',
}

# --------------------------------------------------------------------
# THIRD BLOCK COLORS
# --------------------------------------------------------------------
# Row 1: already shown + hidden rescue candidates.
# Row 2: Gemma validation outcomes within the hidden rescue pool.
THIRD_BLOCK_COLORS = {
    'baseline_by_both': '#5FA8A3',
    'rescue_pool': COLOR_RESCUED,

    'cca_rescued': '#16A34A',
    'subjective_opinion': '#E5A823',
    'irrelevant': '#9CA3AF',
}

THIRD_BLOCK_LABELS = {
    'baseline_by_both': 'Already\nshown',
    'cca_rescued': 'Gemma\nvalidated',
    'subjective_opinion': 'Content\nstop',
    'irrelevant': 'Below 50',
}

# --- Data ---
rep_all = (
    selection_log[selection_log['strategy'] == 'Representative']
    .drop_duplicates('selected_noteId')
    .copy()
)
rep_all['selected_noteId'] = rep_all['selected_noteId'].astype(str)

n_total = int(len(rep_all))
qualified_mask = rep_all['passes_bridge_threshold'].fillna(False).astype(bool)
shown_mask = rep_all['status'].eq('CURRENTLY_RATED_HELPFUL')
shown_qualified_mask = qualified_mask & shown_mask
mask_rescue = qualified_mask & ~shown_mask

n_helpful = int(shown_qualified_mask.sum())
n_rescued = int(mask_rescue.sum())
n_ours = int(qualified_mask.sum())
n_below_threshold = n_total - n_ours

expected_counts = {
    'representative': 44_722,
    'qualified': 20_405,
    'shown_qualified': 6_750,
    'hidden_candidates': 13_655,
    'below_threshold': 24_317,
}
actual_counts = {
    'representative': n_total,
    'qualified': n_ours,
    'shown_qualified': n_helpful,
    'hidden_candidates': n_rescued,
    'below_threshold': n_below_threshold,
}
if actual_counts != expected_counts:
    raise ValueError(f'CCA count contract changed: {actual_counts} != {expected_counts}')

pct_cn = round(100 * n_helpful / n_total)
pct_rescued = round(100 * n_rescued / n_total)
pct_ours = round(100 * n_ours / n_total)
pct_hidden_cn = 100 - pct_cn
pct_hidden_ours = 100 - pct_cn - pct_rescued
pct_lift = pct_ours - pct_cn

scores_local = scores.copy()
scores_local['noteId'] = scores_local['noteId'].astype(str)

helpful_ids = set(rep_all.loc[shown_qualified_mask, 'selected_noteId'])
our_rule_ids = set(rep_all.loc[qualified_mask, 'selected_noteId'])

cluster_ids = [0, 1]
approval_cols = [f'cluster_{c}_approval' for c in cluster_ids]
missing_cols = [c for c in approval_cols if c not in scores_local.columns]
if missing_cols:
    raise ValueError(f'Missing required cluster approval columns: {missing_cols}')


def champion_shares(note_ids):
    sub = scores_local[scores_local['noteId'].isin(note_ids)]
    if len(sub) == 0:
        return [0, 0], 0

    approvals = sub[approval_cols].to_numpy()
    top = np.nanargmax(approvals, axis=1)
    n = len(top)
    shares = [round(100 * (top == i).sum() / n) for i in range(len(cluster_ids))]
    shares[-1] += 100 - sum(shares)
    return shares, n


pct_help_clusters, n_help = champion_shares(helpful_ids)
pct_our_clusters, n_our_cluster = champion_shares(our_rule_ids)

# --------------------------------------------------------------------
# Third block data
# --------------------------------------------------------------------
ccr_pool_ids = set(rep_all.loc[mask_rescue, 'selected_noteId'])

def pct_from_counts(counts):
    total = sum(counts)
    if total == 0:
        return [0 for _ in counts]
    pct = [round(100 * c / total) for c in counts]
    pct[-1] += 100 - sum(pct)
    return pct

# Row 1: baseline notes approved by both + rescue pool over visible notes.
third_row1_keys = ['baseline_by_both', 'rescue_pool']
third_row1_counts = {
    'baseline_by_both': n_helpful,
    'rescue_pool': len(ccr_pool_ids),
}
n_third_block_row1 = sum(third_row1_counts.values())
pct_third_block_row1 = dict(zip(
    third_row1_keys,
    pct_from_counts([third_row1_counts[k] for k in third_row1_keys])
))
pct_third_block_row1_display = pct_third_block_row1.copy()

# Stage 2 contains every note admitted after Stage 1/1.5. The remainder of the
# hidden candidate pool stopped before scoring.
if stage2_results['noteId'].duplicated().any():
    raise ValueError('Stage 2 results contain duplicate noteId values.')
stage2_ids = set(stage2_results['noteId'])
if not stage2_ids.issubset(ccr_pool_ids):
    raise ValueError('Stage 2 contains notes outside the hidden CCA candidate pool.')

n_ccr_gemma_validated = int(stage2_results['passes_rescue_threshold'].fillna(False).sum())
n_ccr_below_50 = int((~stage2_results['passes_rescue_threshold'].fillna(False).astype(bool)).sum())
n_ccr_content_stop = len(ccr_pool_ids) - len(stage2_results)

third_row2_keys = ['cca_rescued', 'subjective_opinion', 'irrelevant']
third_row2_counts = {
    'cca_rescued': n_ccr_gemma_validated,
    'subjective_opinion': n_ccr_content_stop,
    'irrelevant': n_ccr_below_50,
}
n_third_block_row2 = len(ccr_pool_ids)
expected_validation_counts = {
    'validated': 8_558,
    'content_stop': 3_279,
    'below_50': 1_818,
    'candidate_pool': 13_655,
}
actual_validation_counts = {
    'validated': n_ccr_gemma_validated,
    'content_stop': n_ccr_content_stop,
    'below_50': n_ccr_below_50,
    'candidate_pool': n_third_block_row2,
}
if actual_validation_counts != expected_validation_counts:
    raise ValueError(
        f'Gemma validation contract changed: '
        f'{actual_validation_counts} != {expected_validation_counts}'
    )
pct_third_block_row2 = dict(zip(
    third_row2_keys,
    pct_from_counts([third_row2_counts[k] for k in third_row2_keys])
))
pct_third_block_row2_display = pct_third_block_row2.copy()

print(f'Universe: Representative-picked notes n = {n_total:,}')
print(
    f'Coverage: {n_helpful:,} shown notes meet the CCA threshold; '
    f'{n_rescued:,} hidden candidates raise the qualified set to {n_ours:,} '
    f'({pct_ours}% of representative picks, +{pct_lift} pp).'
)
print(
    f'Cluster composition: shown-qualified n = {n_help:,}; '
    f'all qualified n = {n_our_cluster:,}.'
)
print(
    f'Gemma outcomes: {n_ccr_gemma_validated:,} validated, '
    f'{n_ccr_content_stop:,} content stops, {n_ccr_below_50:,} below 50.'
)

# --- Manual layout ---
fig, ax = plt.subplots(figsize=(6.4, 4.45))
fig.patch.set_facecolor(COLOR_BG)
ax.set_facecolor(COLOR_BG)
ax.set_xlim(-12, 124)
ax.set_xticks([])
ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(False)

bar_h = 0.22
bar_x = 0
right_x = 103

row_gap = 0.20
legend_to_bar_gap = 0.25
group_gap = 0.13
coverage_legend_y = 3.85

legend_x = bar_x
coverage_legend_x_shift = 0.30
cluster_legend_x_shift = 0.30
third_legend_x_shift = 0.30
pp_y_shift = 0.05

legend_cov_y = coverage_legend_y
cov_cn_y = legend_cov_y - legend_to_bar_gap
cov_ours_y = cov_cn_y - row_gap

right_label_subline_gap = bar_h * 0.68

# 2nd block
legend_cluster_y = cov_ours_y - right_label_subline_gap - group_gap
cluster_cn_y = legend_cluster_y - legend_to_bar_gap
cluster_ours_y = cluster_cn_y - row_gap

# 3rd block: two bars
legend_third_y = cluster_ours_y - group_gap - 0.18
third_bar1_y = legend_third_y - legend_to_bar_gap
third_bar2_y = third_bar1_y - row_gap

pp_y = cov_ours_y - right_label_subline_gap + pp_y_shift

legend_cov_x = legend_x + coverage_legend_x_shift
legend_cluster_x = legend_x + cluster_legend_x_shift
legend_third_x = legend_x + third_legend_x_shift

legend_dot_w = 1.3 * 1.75
legend_dot_h = 0.08 * 0.75

ax.set_ylim(third_bar2_y - 0.22, legend_cov_y + 0.16)


def draw_stacked_bar(y, segments):
    left = bar_x
    for segment in segments:
        if len(segment) == 3:
            width, color, label_color = segment
            label = f'{width}%'
        else:
            width, color, label_color, label = segment
        ax.barh(
            y,
            width,
            left=left,
            height=bar_h,
            color=color,
            edgecolor='white',
            linewidth=1.0
        )
        if width >= 6:
            ax.text(
                left + width / 2,
                y,
                label,
                ha='center',
                va='center',
                fontsize=10,
                fontweight='bold',
                color=label_color
            )
        left += width


def draw_manual_legend(x, y, items):
    cursor = x
    for color, label, step in items:
        ax.add_patch(
            Rectangle(
                (cursor, y - legend_dot_h / 2),
                legend_dot_w,
                legend_dot_h,
                color=color,
                clip_on=False
            )
        )
        ax.text(
            cursor + 3.1,
            y,
            label,
            ha='left',
            va='center',
            fontsize=9.5,
            color=COLOR_TEXT
        )
        cursor += step


def draw_small_square(x, y, color):
    square_w = 1.3 * 1.75
    square_h = 0.08 * 0.75
    ax.add_patch(
        Rectangle(
            (x, y - square_h / 2),
            square_w,
            square_h,
            color=color,
            clip_on=False
        )
    )


def draw_plus(x, y, color=COLOR_TEXT):
    ax.text(
        x,
        y,
        '+',
        ha='center',
        va='center',
        fontsize=9.5,
        fontweight='bold',
        color=color
    )


def draw_coverage_ticker_row(y, include_rescue=False):
    """
    Group 1 only.

    Row 1:
        CN square + Hidden square

    Row 2:
        CN square + Rescue Pool square + Hidden square
    """
    if include_rescue:
        draw_small_square(GROUP1_ROW2_CN_X, y, GROUP1_LABEL_CN_COLOR)
        draw_plus(GROUP1_ROW2_PLUS_1_X, y, GROUP1_LABEL_PLUS_COLOR)

        draw_small_square(GROUP1_ROW2_RESCUE_X, y, GROUP1_LABEL_RESCUE_COLOR)
        draw_plus(GROUP1_ROW2_PLUS_2_X, y, GROUP1_LABEL_PLUS_COLOR)

        draw_small_square(GROUP1_ROW2_HIDDEN_X, y, GROUP1_LABEL_HIDDEN_COLOR)

    else:
        draw_small_square(GROUP1_ROW1_CN_X, y, GROUP1_LABEL_CN_COLOR)
        draw_plus(GROUP1_ROW1_PLUS_X, y, GROUP1_LABEL_PLUS_COLOR)
        draw_small_square(GROUP1_ROW1_HIDDEN_X, y, GROUP1_LABEL_HIDDEN_COLOR)


def draw_cluster_ticker_row(y, include_rescue=False):
    cluster_ticker_box_x_scale = 1.75
    cluster_ticker_box_y_scale = 0.75

    cluster_ticker_box_x = -4.0
    cluster_ticker_plus_x = -6
    cluster_ticker_rescue_box_x = -10.0
    cluster_ticker_box_w = 1.3 * cluster_ticker_box_x_scale
    cluster_ticker_box_h = 0.08 * cluster_ticker_box_y_scale

    ax.add_patch(
        Rectangle(
            (cluster_ticker_box_x, y - cluster_ticker_box_h / 2),
            cluster_ticker_box_w,
            cluster_ticker_box_h,
            color=GROUP2_LABEL_CN_COLOR,
            clip_on=False
        )
    )

    if include_rescue:
        ax.text(
            cluster_ticker_plus_x,
            y,
            '+',
            ha='center',
            va='center',
            fontsize=9.5,
            fontweight='bold',
            color=GROUP2_LABEL_PLUS_COLOR
        )
        ax.add_patch(
            Rectangle(
                (cluster_ticker_rescue_box_x, y - cluster_ticker_box_h / 2),
                cluster_ticker_box_w,
                cluster_ticker_box_h,
                color=GROUP2_LABEL_RESCUE_COLOR,
                clip_on=False
            )
        )


def draw_third_ticker_row(y, row='rescue'):
    """
    Group 3 ticker rows.
    Row 1: Rescue Pool square + already-shown square
    Row 2: CCA candidate pool square
    """
    if row == 'ccr':
        draw_small_square(
            GROUP3_ROW2_CCR_X,
            y,
            GROUP3_LABEL_CCR_COLOR
        )
    else:
        draw_small_square(
            GROUP3_ROW1_RESCUE_X,
            y,
            THIRD_BLOCK_COLORS['rescue_pool']
        )
        draw_plus(GROUP3_ROW1_PLUS_X, y)
        draw_small_square(
            GROUP3_ROW1_BY_BOTH_X,
            y,
            THIRD_BLOCK_COLORS['baseline_by_both']
        )


def draw_cluster_block(legend_y, cn_y, ours_y):
    draw_manual_legend(
        legend_cluster_x,
        legend_y,
        [
            (CLUSTER_COLORS[0], CLUSTER_LABELS[0], 22),
            (CLUSTER_COLORS[1], CLUSTER_LABELS[1], 22),
        ],
    )

    draw_cluster_ticker_row(cn_y, include_rescue=False)
    draw_cluster_ticker_row(ours_y, include_rescue=True)

    draw_stacked_bar(
        cn_y,
        [
            (pct_help_clusters[0], CLUSTER_COLORS[0], COLOR_ON_DARK),
            (pct_help_clusters[1], CLUSTER_COLORS[1], COLOR_ON_DARK),
        ],
    )
    draw_stacked_bar(
        ours_y,
        [
            (pct_our_clusters[0], CLUSTER_COLORS[0], COLOR_ON_DARK),
            (pct_our_clusters[1], CLUSTER_COLORS[1], COLOR_ON_DARK),
        ],
    )

    ax.text(
        right_x,
        cn_y,
        f'n = {n_help:,}',
        ha='left',
        va='center',
        fontsize=9.5,
        color=COLOR_TEXT
    )
    ax.text(
        right_x,
        ours_y,
        f'n = {n_our_cluster:,}',
        ha='left',
        va='center',
        fontsize=9.5,
        color=COLOR_TEXT
    )


def draw_third_block(legend_y, bar1_y, bar2_y):
    draw_manual_legend(
        legend_third_x,
        legend_y,
        [
            (
                THIRD_BLOCK_COLORS['baseline_by_both'],
                THIRD_BLOCK_LABELS['baseline_by_both'],
                21,
            ),
            (
                THIRD_BLOCK_COLORS['cca_rescued'],
                THIRD_BLOCK_LABELS['cca_rescued'],
                28,
            ),
            (
                THIRD_BLOCK_COLORS['subjective_opinion'],
                THIRD_BLOCK_LABELS['subjective_opinion'],
                30,
            ),
            (
                THIRD_BLOCK_COLORS['irrelevant'],
                THIRD_BLOCK_LABELS['irrelevant'],
                20,
            ),
        ],
    )

    # Row 1 ticker: Rescue Pool square + already-shown square
    draw_third_ticker_row(bar1_y, row='rescue')

    draw_stacked_bar(
        bar1_y,
        [
            (
                pct_third_block_row1_display['baseline_by_both'],
                THIRD_BLOCK_COLORS['baseline_by_both'],
                COLOR_ON_DARK,
                f"{pct_third_block_row1['baseline_by_both']}%",
            ),
            (
                pct_third_block_row1_display['rescue_pool'],
                THIRD_BLOCK_COLORS['rescue_pool'],
                COLOR_ON_DARK,
                f"{pct_third_block_row1['rescue_pool']}%",
            ),
        ],
    )

    ax.text(
        right_x,
        bar1_y,
        f'n = {n_third_block_row1:,}',
        ha='left',
        va='center',
        fontsize=9.5,
        color=COLOR_TEXT
    )

    # Row 2 ticker: CCA candidate pool square
    draw_third_ticker_row(bar2_y, row='ccr')

    draw_stacked_bar(
        bar2_y,
        [
            (
                pct_third_block_row2_display['cca_rescued'],
                THIRD_BLOCK_COLORS['cca_rescued'],
                COLOR_ON_DARK,
                f"{pct_third_block_row2['cca_rescued']}%",
            ),
            (
                pct_third_block_row2_display['subjective_opinion'],
                THIRD_BLOCK_COLORS['subjective_opinion'],
                COLOR_ON_DARK,
                f"{pct_third_block_row2['subjective_opinion']}%",
            ),
            (
                pct_third_block_row2_display['irrelevant'],
                THIRD_BLOCK_COLORS['irrelevant'],
                COLOR_ON_DARK,
                f"{pct_third_block_row2['irrelevant']}%",
            ),
        ],
    )

    ax.text(
        right_x,
        bar2_y,
        f'n = {n_third_block_row2:,}',
        ha='left',
        va='center',
        fontsize=9.5,
        color=COLOR_TEXT
    )


# -------------------------
# Block 1: Coverage
# -------------------------

draw_manual_legend(
    legend_cov_x,
    legend_cov_y,
    [
        (COLOR_SHOWN_BY_CN, 'Already shown', 30),
        (COLOR_RESCUED, 'Rescue Pool', 28),
        (COLOR_HIDDEN, 'Below threshold', 29),
    ],
)

draw_coverage_ticker_row(cov_cn_y, include_rescue=False)
draw_coverage_ticker_row(cov_ours_y, include_rescue=True)

draw_stacked_bar(
    cov_cn_y,
    [
        (pct_cn, COLOR_SHOWN_BY_CN, COLOR_ON_DARK),
        (pct_hidden_cn, COLOR_HIDDEN, COLOR_HIDDEN_TEXT),
    ],
)
draw_stacked_bar(
    cov_ours_y,
    [
        (pct_cn, COLOR_SHOWN_BY_CN, COLOR_ON_DARK),
        (pct_rescued, COLOR_RESCUED, COLOR_ON_DARK),
        (pct_hidden_ours, COLOR_HIDDEN, COLOR_HIDDEN_TEXT),
    ],
)

ax.text(
    right_x,
    cov_cn_y,
    f'{pct_cn}% shown',
    ha='left',
    va='center',
    fontsize=9.5,
    color=COLOR_TEXT
)
ax.text(
    right_x - 2,
    cov_ours_y,
    f'{pct_ours}% qualified',
    ha='left',
    va='center',
    fontsize=9.5,
    fontweight='bold',
    color=COLOR_TEXT
)
ax.text(
    right_x - 2,
    pp_y,
    f'(+{pct_lift} pp)',
    ha='left',
    va='center',
    fontsize=9.5,
    fontweight='bold',
    color=COLOR_RESCUED
)

# -------------------------
# Block 2: Cluster composition
# -------------------------

draw_cluster_block(
    legend_y=legend_cluster_y,
    cn_y=cluster_cn_y,
    ours_y=cluster_ours_y
)

# -------------------------
# Block 3: Two stacked bars
# -------------------------

draw_third_block(
    legend_y=legend_third_y,
    bar1_y=third_bar1_y,
    bar2_y=third_bar2_y
)

save_fig(fig, 'fig3-rescue-panels')
plt.show()
