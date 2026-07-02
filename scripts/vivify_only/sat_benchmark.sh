#!/bin/bash

# This script should be called as follows (after setting all options below as needed):
# nohup bash run_sat_benchmark.sh --run path/to/benchmark-file 2>&1 > OUT &
# After executing this command, you can press Ctrl+C and later log out of the server 
# PROPERLY, i.e., with "exit" and not due to a connection timeout.
# 
# The progress can be monitored in real time with:
# tail -f OUT
# Also check with `htop` that the machine's cores are actually busy.
# 
# To stop/cancel an experiment running in the background, run:
# bash run_sat_benchmark.sh --stop
# 
# You can extract basic coverage / run time information from finished experiments like so:
# bash sat_benchmark.sh --extract path/to/my/experiment
# The provided path must contain a folder named i for each instance index i.
# In that path, some text files with raw information will be created.
# - qualified-runtimes-and-results.txt: 
#   Contains one line for each instance with its ID, the run time (= time limit if 
#   unsolved) and the found result ("sat" or "unsat" or "unknown").
# - qualified-runtimes-{sat,unsat}.txt:
#   Contains one line for each instance found {SAT, UNSAT} with its ID and the run time.
# - cdf-runtimes.txt, cdf-runtimes-{sat,unsat}.txt:
#   Using one of these files as a sequence of x- and y-coordinates, you will get a 
#   performance plot as commonly used by the SAT community. The x-coordinate is the time 
#   limit per instance and the y-coordinate is the number of instances solved in that 
#   limit.

#####################################################################
# TODO Configuration of your experiments

# 8 for normal utilization, keeping hardware threads idle
# 4 for full utilization, spawning a solver at each hardware thread
nhwthreadsperproc=8

# Some environment variables for Mallob
RDMAV_FORK_SAFE=1
NPROCS="$(($(nproc)/$nhwthreadsperproc))"
THREADS_PER_PROC=4
PATH="build:$PATH"

# TODO Set the portfolio of solvers to cycle through
# (k=Kissat, c=CaDiCaL, l=Lingeling, g=Glucose)
# portfolio="kkclkkclkkclkkclccgg"
#portfolio="k"
#portfolio="c"

# Clause buffering decay factor. Usually 1.0 for modestly parallel setups
# and 0.9 for massively parallel setups.
# cbdf=1.0

# Timeout per instance in seconds
# timeout=300

# Run all instances from this index up to the end
# (Default: 1; set to another number i if continuing an interrupted 
# experiment where i-1 instances were run successfully)
startinstance=1

# TODO Base log directory; use a descriptive name for each experiment. No spaces.
# baselogdir="myexperiment"

# TODO Add any further options to the name of this log directory as well.
# Results from older experiments with the same sublogdir will be overwritten!
# sublogdir="${baselogdir}/${portfolio}-cbdf${cbdf}-T${timeout}"

: "${portfolio:?portfolio missing}"
: "${timeout:?timeout missing}"
: "${CBDF:?CBDF missing}"
: "${vivify:?vivify missing}"
: "${sublogdir:?sublogdir missing}"
: "${download_dir:?download_dir missing}"

# TODO Add further options to these arguments Mallob is called with.
malloboptions="-t=$THREADS_PER_PROC -jwl=$timeout -T=$(($timeout + 30)) -v=3 -sleep=1000 -trace-dir=. -pipe-large-solutions=0 -processes-per-host=$NPROCS -regular-process-allocation -max-lits-per-thread=50000000 -strict-clause-length-limit=20 -clause-filter-clear-interval=500 -max-lbd-partition-size=2 -export-chunks=20 -clause-buffer-discount=$cbdf -satsolver=$portfolio -vivi=$vivify"

#####################################################################


if [ -z $1 ]; then
    echo "Usage:"
    echo "Run a benchmark: bash $0 --run path/to/benchmark-file"
    echo "Extract benchmark results: bash $0 --extract path/to/experiments"
    exit 1
fi

# Extract run time results
if [ "$1" == "--extract" ]; then

    # Set $1 to results directory
    shift 1
    if [ -z $1 ]; then
        echo "Provide a results directory."
        exit 1
    fi

    > $1/qualified-runtimes.txt
    > $1/qualified-runtimes-sat.txt
    > $1/qualified-runtimes-unsat.txt

    total_threads=$((NPROCS * THREADS_PER_PROC))
    echo "TOTAL_THREADS $total_threads" >> $1/setup.txt
    echo "MPI_PROCS $NPROCS" >> $1/setup.txt
    echo "THREADS_PER_PROC $THREADS_PER_PROC" >> $1/setup.txt

    nsat=0
    nunsat=0
    par2sum=0
    i=1
    while [ -d "$1/$i" ]; do
    
        if [ -f STOP_IMMEDIATELY ]; then
            # Signal to stop
            echo "Stopping because STOP_IMMEDIATELY is present"
            exit
        fi
        
        # Log files to parse
        dir="$1/$i"
        logfiles=$(echo $dir/*/log.*)
        echo $dir
        
        # Extract run time and result
        time=$(grep "RESPONSE_TIME" $logfiles | awk '{print $6}' | tail -n1)

        if [ -z "$time" ]; then
            echo "ERROR: No RESPONSE_TIME found in:"
            echo "  $logfiles"
            exit 0
        fi

        # Determine result
        if grep -q "^s SATISFIABLE" $logfiles; then
            result="sat"
            nsat=$((nsat+1))
            par2sum=$(echo "$par2sum + $time" | bc -l)

        elif grep -q "^s UNSATISFIABLE" $logfiles; then
            result="unsat"
            nunsat=$((nunsat+1))
            par2sum=$(echo "$par2sum + $time" | bc -l)

        else
            result="unknown"
            time="$timeout"
            par2sum=$(echo "$par2sum + 2*$timeout" | bc -l)
        fi
        
        # Write run time and result to files
        echo "$i $time $result $total_threads" >> $1/qualified-runtimes.txt
        echo "$i $time" >> $1/qualified-runtimes-$result.txt
        
        python scripts/vivify_only/plot_vivi_clause_size_over_time.py \
        $dir "${dir}/"

        python scripts/vivify_only/plot_vivifies_total_over_time.py \
        $dir "${dir}/"

        i=$((i+1))
    done
    
    # Postprocess and reformat files
    for res in "" -sat -unsat ; do
        cat $1/qualified-runtimes${res}.txt|awk '$2 < '$timeout' {print $2}'|sort -g > $1/sorted-runtimes${res}.txt
        cat $1/sorted-runtimes${res}.txt|awk '{print $1,NR}' > $1/cdf-runtimes${res}.txt
    done
    mv $1/qualified-runtimes.txt $1/qualified-runtimes-and-results.txt
    
    echo "Experiments on $((i-1)) instances found."
    echo "$((nsat+nunsat)) solved ($nsat sat, $nunsat unsat), PAR-2 score: $(echo "$par2sum / (${i}-1)"|bc -l)"

    echo "$((nsat+nunsat)) $nsat $nunsat $(echo "$par2sum / (${i}-1)"|bc -l)" >> $1/table_entry.txt
    exit 0
fi

# Set $1 to benchmarks file
shift 1
if [ -z $1 ]; then
    echo "Provide a benchmark file."
    exit 1
fi

# Run experiments
i=1
for f in $(cat $1) ; do

        if [ -f STOP_IMMEDIATELY ]; then
            # Signal to stop
            echo "Stopping because STOP_IMMEDIATELY is present"
            exit
        fi

        # Skip any instances that should be skipped
        if [ $i -lt $startinstance ]; then 
                i=$((i+1))
                continue 
        fi

        hash=$(echo "$f"|grep -oE "[0-9a-f]{32}"|head -1)

        matches=( "$download_dir"/"${hash}"* )
        if [ -e "${matches[0]}" ]; then
            file="${matches[0]}"
        else  
            # Download file if necessary
            # downloaded=false
            echo "Cannot find file for hash \"$hash\" - trying to download from benchmark-database"
            # downloaded=true
            while ! wget -q --content-disposition -P "$download_dir" https://benchmark-database.de/file/$hash ; do sleep 1; done


            matches=( "$download_dir"/"${hash}"* )
            if [ -e "${matches[0]}" ]; then
                file="${matches[0]}"
            else
                echo "ERROR: download succeeded but no file matching $hash was found in $download_dir"
                exit 1
            fi
        fi

        echo "************************************************"
        echo "$i : $file"
        
        logdir="${sublogdir}/$i"
        rm -rf $logdir 2>/dev/null
        mkdir -p $logdir
        
        # Run Mallob
        mpirun -np $NPROCS --bind-to hwthread --map-by ppr:${NPROCS}:node:pe=$nhwthreadsperproc build/mallob -mono=$file -log=$logdir -spd=$logdir -spl=4 -sld=$logdir -os $malloboptions 2>&1 > $logdir/OUT
        
        # Clean up
        # if $downloaded; then
        #     rm -rf "$f"
        # fi
        sleep 1

        i=$((i+1))
        echo ""
done
 
