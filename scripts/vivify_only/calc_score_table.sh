#!/bin/bash
set -euo pipefail

# Path to the benchmark script
BENCHMARK_SCRIPT="./scripts/vivify_only/sat_benchmark.sh"

# Benchmark file (one CNF per line)
BENCHMARK_FILE="$1"
OUT_FILE="$2"

# Clean up other running experiments
if [ "$1" == "--stop" ]; then
    touch STOP_IMMEDIATELY
    sleep 3
    rm STOP_IMMEDIATELY
    echo "Stopped experiments."
    exit 0
fi

mkdir -p "$OUT_FILE/results"

if [[ -z "${BENCHMARK_FILE:-}" ]]; then
    echo "Usage: $0 benchmark-file"
    exit 1
fi

if [[ -z "${OUT_FILE:-}" ]]; then
    echo "Usage: $0 $1 OUT_FILE"
    exit 1
fi

# Solver configurations to evaluate
declare -A PORTFOLIOS

CONFIGS=(
"CaDiCaL|c|1"
"CaDiCaL-|c|0"
"CaDiCaL_v1|(v){1}(c)*|0"
"CaDiCaL_v2|(v){2}(c)*|0"
"CaDiCaL_v3|(v){3}(c)*|0"
"CaDiCaL_v4|(v){4}(c)*|0"
"CaDiCaL_v5|(v){5}(c)*|0"
"CaDiCaL_v6|(v){6}(c)*|0"
"CaDiCaL+_v2|(v){2}(c)*|1"
"CaDiCaL+_v3|(v){3}(c)*|1"
)

TIMEOUT=300

{
  echo "=== DATE ==="
  date
  echo

  echo "=== HOST ==="
  hostnamectl 2>/dev/null || hostname
  echo

  echo "=== CPU ==="
  lscpu
  echo

  echo "=== MEMORY ==="
  free -h
  echo

  echo "=== OS / KERNEL ==="
  uname -a
  cat /etc/os-release 2>/dev/null
  echo

  echo "=== NUMA ==="
  numactl --hardware 2>/dev/null || true
  echo

  echo "=== LIMITS ==="
  ulimit -a
} > "${OUT_FILE}/results/system-info.txt"

for entry in "${CONFIGS[@]}"; do

    IFS='|' read -r solver portfolio vivify <<< "$entry"

    echo "======================================="
    echo "Running configuration: $solver"
    echo "======================================="

    export portfolio="$portfolio"
    export timeout="$TIMEOUT"
    export sublogdir="${OUT_FILE}/results/${solver}"
    export vivify=$vivify
    export download_dir="${OUT_FILE}/downloads"

    bash "$BENCHMARK_SCRIPT" --run "$BENCHMARK_FILE"

    if [ -f STOP_IMMEDIATELY ]; then
        # Signal to stop
        echo "Stopping because STOP_IMMEDIATELY is present"
        exit
    fi

    echo
    echo "Extracting statistics for $solver ..."
    bash "$BENCHMARK_SCRIPT" --extract "${OUT_FILE}/results/${solver}"

    if [ -f STOP_IMMEDIATELY ]; then
        # Signal to stop
        echo "Stopping because STOP_IMMEDIATELY is present"
        exit
    fi

    echo "${solver} $(cat "${OUT_FILE}/results/${solver}/table_entry.txt")" >> "${OUT_FILE}/results/summary_table.txt"
done

echo "All experiments finished."
