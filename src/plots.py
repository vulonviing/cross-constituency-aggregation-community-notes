from __future__ import annotations

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


def set_notebook_plot_style() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def plot_consensus_map(scores: pd.DataFrame, sample_size: int = 2000):
    sample = scores.sample(n=min(sample_size, len(scores)), random_state=42).copy()
    cluster_cols = sorted(
        [col for col in scores.columns if col.startswith("cluster_") and col.endswith("_approval")],
        key=lambda col: int(col.split("_")[1]),
    )
    sample["mean_approval"] = sample[cluster_cols].mean(axis=1)
    sample["disagreement"] = sample[cluster_cols].std(axis=1)

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.scatterplot(
        data=sample,
        x="mean_approval",
        y="disagreement",
        hue="currentStatus",
        style="currentStatus",
        alpha=0.6,
        s=60,
        ax=ax,
    )
    ax.set_title("Consensus Map: Mean Approval vs Disagreement")
    ax.set_xlabel("Mean cluster approval")
    ax.set_ylabel("Disagreement across clusters (std)")
    return fig, ax
