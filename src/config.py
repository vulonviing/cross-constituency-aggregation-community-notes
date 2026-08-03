from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    project_root: Path = Path(".")
    master_csv: Path = Path("master_sample.csv")
    notebook_dir: Path = Path("notebooks")
    figure_dir: Path = Path("figures")
    data_dir: Path = Path("data")
    interim_dir: Path = Path("data/interim")
    processed_dir: Path = Path("data/processed")


@dataclass(frozen=True)
class ClusteringConfig:
    target_note_count: int = 5000
    target_user_count: int = 10000
    min_note_ratings: int = 3
    hours_window: int = 48
    k_min: int = 2
    k_max: int = 7
    random_state: int = 42
    stability_runs: int = 10
    stability_subsample_frac: float = 0.8
    similarity_method: str = "pearson"  # "pearson" (mean-centered cosine) or "cosine_raw"
    # Sparse k-NN affinity graph (Von Luxburg 2007 standard recommendation).
    # Each user is connected to its top-`knn_neighbors` peers by centered
    # cosine similarity; the resulting sparse Laplacian eigendecomp is O(nnz)
    # instead of O(n^2), which is the main runtime gain over a dense affinity.
    knn_neighbors: int = 15
    silhouette_sample_size: int = 5000


@dataclass(frozen=True)
class ScoringConfig:
    bridge_threshold: float = 0.5
    min_note_ratings: int = 3
    min_cluster_ratings: int = 3  # per-cluster minimum for bridge score
    eps: float = 1e-6


@dataclass(frozen=True)
class TopicConfig:
    embedding_model_name: str = "all-MiniLM-L6-v2"
    umap_components: int = 5
    umap_neighbors: int = 15
    random_state: int = 42
    top_k_topics: int = 10
    top_k_exemplars: int = 5
    salience_top_n: int = 30

