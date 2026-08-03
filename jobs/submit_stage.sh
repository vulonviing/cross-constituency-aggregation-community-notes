#!/bin/bash

set -euo pipefail

usage() {
    cat >&2 <<'EOF'
Usage:
  jobs/submit_stage.sh [--dry-run] <stage>

Stages:
  ingest
  clustering
  scoring
  topics
  plots
  paper_visuals

Canonical note validation uses jobs/submit_llm_validation.sh; see
notebooks/llm_validation/README.md. TEST_MODE=1 writes stage outputs under
.artifacts/smoke/.
EOF
}

dry_run=0
if [ "${1:-}" = "--dry-run" ]; then
    dry_run=1
    shift
fi

stage="${1:-}"
case "$stage" in
    ingest|clustering|scoring|topics|plots|paper_visuals) ;;
    *)
        echo "Unknown stage: ${stage:-<missing>}" >&2
        usage
        exit 64
        ;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
cd "$project_root"
source jobs/_job_helpers.sh

test_mode="$(test_mode_from_config)"
full_profile="$(config_value FULL_RESOURCE_PROFILE large)"
case "$full_profile" in
    probe|standard|expanded|large) ;;
    *) full_profile="large" ;;
esac

case "${test_mode}:${stage}" in
    1:ingest)
        job_name="cn_ingest_test"; queue="scc"; slots="2"; h_vmem="8G"; h_rt="01:00:00"; mail=1 ;;
    1:clustering)
        job_name="cn_cluster_test"; queue="scc"; slots="2"; h_vmem="4G"; h_rt="01:00:00"; mail=1 ;;
    1:scoring)
        job_name="cn_scoring_test"; queue="scc"; slots="1"; h_vmem="4G"; h_rt="00:30:00"; mail=0 ;;
    1:topics)
        job_name="cn_topics_test"; queue="scc"; slots="2"; h_vmem="12G"; h_rt="02:00:00"; mail=1 ;;
    1:plots|1:paper_visuals)
        job_name="cn_${stage}_test"; queue="scc"; slots="2"; h_vmem="20G"; h_rt="01:00:00"; mail=0 ;;
    0:ingest)
        job_name="cn_ingest_${full_profile}"; queue="scc"; slots="8"; h_vmem="16G"; h_rt="06:00:00"; mail=1 ;;
    0:clustering)
        job_name="cn_cluster_${full_profile}"; mail=1
        case "$full_profile" in
            probe) queue="scc"; slots="4"; h_vmem="12G"; h_rt="08:00:00" ;;
            standard) queue="scc"; slots="7"; h_vmem="10G"; h_rt="24:00:00" ;;
            expanded) queue="scc"; slots="7"; h_vmem="12G"; h_rt="48:00:00" ;;
            large) queue="long"; slots="7"; h_vmem="16G"; h_rt="72:00:00" ;;
        esac
        ;;
    0:scoring)
        job_name="cn_scoring_${full_profile}"; queue="scc"; slots="2"; h_vmem="20G"; h_rt="02:00:00"; mail=0 ;;
    0:topics)
        job_name="cn_topics_${full_profile}"; mail=1
        case "$full_profile" in
            probe) queue="scc"; slots="4"; h_vmem="12G"; h_rt="02:00:00" ;;
            standard) queue="scc"; slots="7"; h_vmem="8G"; h_rt="04:00:00" ;;
            expanded|large) queue="long"; slots="7"; h_vmem="16G"; h_rt="08:00:00" ;;
        esac
        ;;
    0:plots|0:paper_visuals)
        job_name="cn_${stage}_${full_profile}"; queue="scc"; slots="2"; h_vmem="20G"; h_rt="01:00:00"; mail=0 ;;
esac

log_root="$(log_root_from_config)"
mkdir -p "$log_root"
rm -f "${log_root}/${stage}.out" "${log_root}/${stage}.err"

qsub_args=(
    -S /bin/bash
    -N "$job_name"
    -q "$queue"
    -pe smp "$slots"
    -l "h_vmem=${h_vmem},h_rt=${h_rt}"
    -o "${log_root}/${stage}.out"
    -e "${log_root}/${stage}.err"
    -cwd
    -v "CN_SUBMIT_HELPER=1"
)

if [ "$mail" = "1" ] && [ -n "${NOTIFY_EMAIL:-}" ]; then
    qsub_args+=(-m bea -M "$NOTIFY_EMAIL")
fi
qsub_args+=("jobs/${stage}.sh")

echo "[submit] stage=${stage} TEST_MODE=${test_mode}"
if [ "$test_mode" = "0" ]; then
    echo "[submit] FULL_RESOURCE_PROFILE=${full_profile}"
fi
echo "[submit] queue=${queue} slots=${slots} h_vmem=${h_vmem} h_rt=${h_rt}"

if [ "$dry_run" = "1" ]; then
    printf "[dry-run] qsub"
    printf " %q" "${qsub_args[@]}"
    printf "\n"
    exit 0
fi

qsub "${qsub_args[@]}"
