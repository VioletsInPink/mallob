#!/bin/bash

#####################################################################
# 8 for normal utilization, keeping hardware threads idle
# 4 for full utilization, spawning a solver at each hardware thread
nhwthreadsperproc=4

# Some environment variables for Mallob
RDMAV_FORK_SAFE=1
NPROCS="$(($(nproc)/$nhwthreadsperproc))"
THREADS_PER_PROC=4
PATH="build:$PATH"

# Clause buffering decay factor. Usually 1.0 for modestly parallel setups
# and 0.9 for massively parallel setups.
# cbdf=1.0

# Run all instances from this index up to the end
# (Default: 1; set to another number i if continuing an interrupted 
# experiment where i-1 instances were run successfully)
startinstance=1

: "${portfolio:?portfolio missing}"
: "${timeout:?timeout missing}"
: "${vivify:?vivify missing}"
: "${sublogdir:?sublogdir missing}"
: "${download_dir:?download_dir missing}"


max_timout="$(($timeout + 15))"

# TODO Add further options to these arguments Mallob is called with.
malloboptions="-t=$THREADS_PER_PROC -jwl=$timeout -T=$max_timout -v=3 -trace-dir=../trace -processes-per-host=$NPROCS -satsolver=$portfolio -vivi=$vivify"
# echo $malloboptions
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
 
