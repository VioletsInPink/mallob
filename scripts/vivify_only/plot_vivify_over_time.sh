#!/usr/bin/env bash

set -e

RES_DIR="$1"
OUT_DIR="$2"

if [[ -z "$RES_DIR" || -z "$OUT_DIR" ]]; then
    echo "Usage: $0 <results_dir> <output_dir>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$OUT_DIR"

# Each portfolio directory
for portfolio_dir in "$RES_DIR"/*; do

    if [[ ! -d "$portfolio_dir" ]]; then
        continue
    fi

    # Skip plot directories
    if [[ "$name" == "plot" || "$name" == "plots" ]]; then
        continue
    fi

    name=$(basename "$portfolio_dir")

    echo "=============================="
    echo "Portfolio: ${name}"


    for file_dir in "$portfolio_dir"/*; do
        filename=$(basename "$file_dir")

        if [[ ! -d "$file_dir" ]]; then
            continue
        fi

        echo "Running ${name}:${filename}"

        OUTNAME="${name}-${filename}"

        python "${SCRIPT_DIR}/plot_vivi_clause_size_over_time.py" \
            "$portfolio_dir/$filename" \
            "${OUT_DIR}" \
            "${OUTNAME}"

        python "${SCRIPT_DIR}/plot_vivifies_total_over_time.py" \
            "$portfolio_dir/$filename" \
            "${OUT_DIR}" \
            "${OUTNAME}"
    done
done
