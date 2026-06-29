#!/usr/bin/env bash

set -e  # stop on error

NPROCS=4

FILES=("r3unsat_200" "r3unsat_250" "r3unsat_300" "r3sat_200" "r3sat_300")
VIVI_VALUES=(0 1)

for file in "${FILES[@]}"; do
  for vivi in "${VIVI_VALUES[@]}"; do

    echo "=============================="
    echo "Running file=$file with vivi=$vivi"
    echo "=============================="

    # clean log directory
    rm -rf log
    mkdir -p log

    # export environment variables properly
    export RDMAV_FORK_SAFE=1
    export NPROCS=$NPROCS

    # run MPI job
    mpirun -np 4 --bind-to core \
      build/mallob \
      -mono="instances/${file}.cnf" \
      -t=8 \
      -satsolver='(v){3}(c)*' \
      -log=log \
      -spl=4 \
      -spd=log \
      -sld=log \
      -vivi=${vivi} \
      -quiet

    # define output name for plotting
    if [ "$vivi" -eq 1 ]; then
      OUTNAME="../../Bachelorarbeit: Obsidian Vault/${file}_withCadical_"
    else
      OUTNAME="../../Bachelorarbeit: Obsidian Vault/${file}_"
    fi

    # run plotting script
    python scripts/vivify_only/plot_vivi_clause_size_over_time.py \
      log "${OUTNAME}"

    python scripts/vivify_only/plot_vivifys_over_time.py \
      log "${OUTNAME}"

  done
done
