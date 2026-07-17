#!/bin/bash

#####################################################################
# Some environment variables for Mallob
RDMAV_FORK_SAFE=1
# configured for AMD EPYC™ 7713
# of CPU Cores 64
# of Threads 128
# 16 x 8 increases the synchronisation of clauses
# useful for vivify only. Since it relies on clause sharing
NPROCS=16
THREADS_PER_PROC=8
PATH="build:$PATH"

: "${portfolio:?portfolio missing}"
: "${timeout:?timeout missing}"
: "${vivify:?vivify missing}"
: "${sublogdir:?sublogdir missing}"
: "${download_dir:?download_dir missing}"

max_timout="$(($timeout + 15))"

malloboptions="-watchdog=0 -t=$THREADS_PER_PROC -jwl=$timeout -T=$max_timout -v=3 -trace-dir=../trace -processes-per-host=$NPROCS -satsolver=$portfolio -vivi=$vivify"
#####################################################################

if [ -z $1 ]; then
    echo "Usage:"
    echo "Run a benchmark: bash $0 --run path/to/benchmark-file"
    exit 1
fi

# Set $1 to benchmarks file
shift 1
if [ -z $1 ]; then
    echo "Provide a benchmark file."
    exit 1
fi

setup_file="$sublogdir/setup.txt"

if [ ! -f "$setup_file" ]; then
    cat > "$setup_file" <<EOF
DATE $(date)
TOTAL_THREADS $(($NPROCS * $THREADS_PER_PROC))
MPI_PROCS $NPROCS
THREADS_PER_PROC $THREADS_PER_PROC
PORTFOLIO $portfolio
TIMEOUT $timeout
VIVIFY $vivify
EOF
fi

# Run experiments
i=1
for f in $(cat $1) ; do
        hash=$(echo "$f"|grep -oE "[0-9a-f]{32}"|head -1)

        matches=( "$download_dir"/"${hash}"* )
        if [ -e "${matches[0]}" ]; then
            file="${matches[0]}"
        else  
            echo "Cannot find file for hash \"$hash\" - trying to download from benchmark-database"
    
            max_retries=3
            retries=0
            downloaded=false

            while [ $retries -lt $max_retries ]; do
                if wget -q --content-disposition -P "$download_dir" "https://benchmark-database.de/file/$hash"; then
                    downloaded=true
                    break
                fi
                retries=$((retries + 1))
                echo "Download failed (attempt $retries/$max_retries), retrying in 5s..."
                sleep 5
            done
            
            if [ "$downloaded" = false ]; then
                echo "ERROR: Failed to download hash $hash after $max_retries attempts"
                echo "[]: skip this instance"
                i=$((i+1))
                # Option 2: Exit entirely
                # exit 1
            fi


            matches=( "$download_dir"/"${hash}"* )
            if [ -e "${matches[0]}" ]; then
                file="${matches[0]}"
            else
                echo "ERROR: download succeeded but no file matching $hash was found in $download_dir"
                echo "[]: skip this instance"
                i=$((i+1))
            fi
        fi

        echo "************************************************"
        echo "$i : $file"
        
        logdir="${sublogdir}/$i"
        if [ -d "$logdir" ]; then
            echo "Skipping instance $i: $logdir already exists"
            i=$((i+1))
            continue
        fi
        
        if ! mkdir "$logdir"; then
            echo "ERROR: Failed to create $logdir"
            exit 1
        fi

        # Run Mallob
        echo "$(date +%T) start mallob"
        time \
        timeout -s TERM $(($timeout + 60)) \
        mpirun -np "$NPROCS" --bind-to hwthread --map-by "ppr:${NPROCS}:node:pe=${nhwthreadsperproc}" build/mallob -mono="$file" -log="$logdir" -spd="$logdir" -spl=4 -sld="$logdir" -os $malloboptions 2>&1 > "${logdir}/OUT"
        RETCODE=$?
        echo "$(date +%T) end mallob"    

        if [ $RETCODE -eq 124 ]; then
            echo "CRITICAL ERROR: Mallob exceeded 6-minute timeout"
        elif [ $RETCODE -eq 127 ]; then
            echo "CRITICAL ERROR: Command not found"
            rm -r "$logdir"
            exit 1
        elif [ $RETCODE -eq 2 ]; then 
            echo "CRITICAL ERROR: no such file or directory"
            rm -r "$logdir"
            exit 1
        fi

        # Clean up
        # if $downloaded; then
        #     rm -rf "$f"
        # fi
        sleep 1

        i=$((i+1))
done
 
