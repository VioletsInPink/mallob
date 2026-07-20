#!/usr/bin/env python3

# This script extracts relevant stats from a given results directory
# All extracted stats are an average over the amount of solver threads used by that instance

from enum import Enum
import numpy as np
import argparse
import re
from pathlib import Path
from dataclasses import dataclass, field
from tqdm import tqdm
import pickle

class RESULT(Enum):
    UNKOWN = 1
    SAT = 2
    UNSAT = 3

@dataclass
class InstanceStats:
    busy_time: float = 0
    result: RESULT = RESULT.UNKOWN
    num_active_threads: int = 0
    num_active_threads_per_proc: int = 0

    vivified: float = 0
    vivify_time: float = 0
    solve_time: float = 0

@dataclass
class Stats:
    solver_name: str = ""
    num_instances: int = 0
    solved: int = 0
    sat: int = 0
    unsat: int = 0
    par2: float = 0
 
    busy_time_per_instance: float = 0
    vivified_per_instance: float = 0
    vivify_time_per_instance: float = 0
    vivified_throughput: float = 0

    instance_stats: list[InstanceStats] = field(default_factory=list)

@dataclass
class Setup:
    num_threads: int
    nprocs: int
    threads_per_proc: int
    timeout: int
    vivify: bool

def warn(msg):
    tqdm.write(f"\033[93mWARNING: {msg}\033[0m")

def read_setup(results_dir: Path):
    setup = Setup

    setup_file = results_dir / "setup.txt"
    if not setup_file.exists():
        print(f"ERROR: missing {setup_file}")
        exit(1)

    with open(setup_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            key, value = line.split(maxsplit=1)
            match key:
                case "TOTAL_THREADS":
                    setup.num_threads = int(value)
                case "MPI_PROCS":
                    setup.nprocs = int(value)
                case "THREADS_PER_PROC":
                    setup.threads_per_proc = int(value)
                case "TIMEOUT":
                    setup.timeout = int(value)
                case "VIVIFY": 
                    setup.vivify = (value == "1")

        # validate
        if setup.num_threads != setup.nprocs * setup.threads_per_proc:
            print(f"Invalid setup in {setup_file}")
            exit(1)

    return setup

def get_busy_time_and_result(instance_dir, setup: Setup, stats: InstanceStats):
    outfile = Path(str(instance_dir / "OUT"))

    stats.result = RESULT.UNKOWN
    busy_time : list[float]  = []

    # Extract stats
    with open(outfile) as f:
        for line in f:
            if "busytime" in line:
                fields = line.split("=")
                busy_time.append(float(fields[1].strip()))

            if line.startswith("s SATISFIABLE"):
                stats.result = RESULT.SAT
            elif line.startswith("s UNSATISFIABLE"):
                stats.result = RESULT.UNSAT

            if "literal threshold exceeded - cut down #threads to" in line:
                fields = line.split()
                cut_threads = int(fields.pop().strip())
                stats.num_active_threads_per_proc = cut_threads
                stats.num_active_threads = cut_threads * setup.nprocs
        
    if stats.num_active_threads == 0:
        stats.num_active_threads = setup.num_threads
        stats.num_active_threads_per_proc = setup.threads_per_proc

    if len(busy_time) != setup.nprocs:
        warn(f"expected {setup.nprocs} threads got {len(busy_time)} in {instance_dir}")
    
    if len(busy_time) > 0:
        stats.busy_time = np.average(busy_time)
    else:
        warn(f"no busy time found in {instance_dir}")
        stats.busy_time = 0.0

def get_cadical_vivi_stats(instance_dir: Path, stats: InstanceStats):
    found_threads = 0

    # each process directory
    for proc_dir in instance_dir.iterdir():
        if not proc_dir.is_dir() or not proc_dir.name.isdigit():
            continue

        # CaDiCaL output files
        cadical_files = list(proc_dir.glob("cadical.out.#*"))
        if not cadical_files:
            return False

        for logfile in cadical_files:
            found_threads += 1
            with open(logfile, errors="ignore") as f:
                for line in f:
                    m = re.search(
                        r"c vivified:\s+(\d+)",
                        line
                    )
                    if m:
                        stats.vivified += int(m.group(1))

        # Parse profile statistics
        profile_files = list(proc_dir.glob("profile.#*"))
        if not profile_files:
            return False

        for profile in profile_files:
            with open(profile, errors="ignore") as f:
                for line in f:

                    # Example:
                    # 0.32    0.77% vivify
                    m = re.match(
                        r"\s*([0-9.]+)\s+[0-9.]+%\s+vivify",
                        line
                    )
                    if m:
                        stats.vivify_time += float(m.group(1))

                    # Example:
                    # 41.52   99.51% solve
                    m = re.match(
                        r"\s*([0-9.]+)\s+[0-9.]+%\s+solve",
                        line
                    )
                    if m:
                        stats.solve_time += float(m.group(1))

    if found_threads > 0:
        stats.vivified /= found_threads
        stats.vivify_time /= found_threads
        stats.solve_time /= found_threads

    if found_threads != stats.num_active_threads:
        warn(f"found results for {found_threads}, expected {stats.num_active_threads} in {instance_dir.name}")

    return True

def createStats(solver_name: str, instance_stats: list[InstanceStats], setup: Setup):

    sat = 0
    unsat = 0
    par2 = 0

    vivified = 0
    vivi_time = 0
    busy_time = 0
    for instance in instance_stats:
        match instance.result:
            case RESULT.SAT:
                sat +=1
                par2 += instance.busy_time
            case RESULT.UNSAT:
                unsat +=1
                par2 += instance.busy_time
            case RESULT.UNKOWN:
                par2 += 2*setup.timeout

        vivified += instance.vivified
        vivi_time += instance.vivify_time
        busy_time += instance.busy_time


    par2 /= len(instance_stats)
    vivified /= len(instance_stats)
    vivi_time /= len(instance_stats)
    busy_time /= len(instance_stats)
    return Stats(solver_name, len(instance_stats), sat + unsat, sat, unsat, par2, busy_time, vivified, vivi_time, vivified / vivi_time if vivi_time > 0 else 0, instance_stats)

def extract(results_dir):
    results_dir = Path(results_dir)
    setup = read_setup(results_dir)

    instance_stats = []
    no_stats_found = []

    dirs = [d for d in results_dir.iterdir() if d.is_dir()]
    for instance_dir in tqdm(dirs, desc="Extracting statistics"):
        stats = InstanceStats()

        get_busy_time_and_result(instance_dir, setup, stats)
        if not get_cadical_vivi_stats(instance_dir, stats):
            no_stats_found.append(instance_dir.name)

        instance_stats.append(stats)

    stats = createStats(results_dir.name, instance_stats, setup)
    
    if any(i.num_active_threads_per_proc != setup.threads_per_proc for i in stats.instance_stats):
        warn("Experiments exist with reduced thread count.")

    print(f"Experiments on {stats.num_instances} instances found.")
    print(
        f"{stats.solved} solved ({stats.sat} sat, {stats.unsat} unsat), "
        f"PAR-2 score: {stats.par2}"
    )

    return stats

def clean(results_dir):
    results_dir = Path(results_dir)
    print("cleaning")

def getStats(results_dir):
    results_dir = Path(results_dir)
        
    if Path(results_dir/"stats.pickle").is_file():
        with open(results_dir/"stats.pickle", 'rb') as cache:
            warn("using cached results")
            return pickle.load(cache)

    if not results_dir.is_dir():
        print(f"ERROR: {results_dir} is not a directory")
        exit(1)

    stats = []

    for portfolio_dir in sorted(results_dir.iterdir()):
        if not portfolio_dir.is_dir():
            continue

        # Skip non-portfolio directories if needed
        if not (portfolio_dir / "setup.txt").exists():
            print(f"Skipping {portfolio_dir}: no setup.txt")
            continue

        print(f"\n=== Processing {portfolio_dir.name} ===")
        stats.append(extract(portfolio_dir))

    with open(results_dir/"stats.pickle", 'ab') as cache:
        pickle.dump(stats, cache)
    return stats


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "results_dir",
        help="Directory containing the experiment results."
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove generated summary files before extracting."
    )

    args = parser.parse_args()
    if args.clean:
        clean(args.results_dir)
    else:
        getStats(args.results_dir)

if __name__ == "__main__":
    main()
