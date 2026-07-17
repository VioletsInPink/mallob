#!/usr/bin/env python3

import argparse
import glob
import os
import shutil
import subprocess
import re
from pathlib import Path

def read_setup(setup_file):
    setup = {}

    with open(setup_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            key, value = line.split(maxsplit=1)
            setup[key] = value

    return setup

def collect_solver_stats(instance_dir):
    stats = {
        "vivified": 0,
        "vivify_time": 0.0,
        "solve_time": 0.0,
        "threads": 0,
    }

    errors = 0

    # each process directory
    for proc_dir in instance_dir.iterdir():
        if not proc_dir.is_dir() or not proc_dir.name.isdigit():
            continue

        # CaDiCaL output files
        cadical_files = list(proc_dir.glob("cadical.out.#*"))
        profile_files = list(proc_dir.glob("profile.#*"))

        if not cadical_files:
            # print(f"ERROR: missing cadical.out.* in {proc_dir}")
            errors += 1

        if not profile_files:
            # print(f"ERROR: missing profile.* in {proc_dir}")
            errors += 1

        # Parse vivify statistics
        for logfile in cadical_files:
            stats["threads"] += 1

            with open(logfile, errors="ignore") as f:
                for line in f:
                    m = re.search(
                        r"c vivified:\s+(\d+)",
                        line
                    )
                    if m:
                        stats["vivified"] += int(m.group(1))

        # Parse profile statistics
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
                        stats["vivify_time"] += float(m.group(1))

                    # Example:
                    # 41.52   99.51% solve
                    m = re.match(
                        r"\s*([0-9.]+)\s+[0-9.]+%\s+solve",
                        line
                    )
                    if m:
                        stats["solve_time"] += float(m.group(1))

    if stats["solve_time"] > 0:
        stats["vivify_percent"] = (
            100.0 *
            stats["vivify_time"] /
            stats["solve_time"]
        )
    else:
        stats["vivify_percent"] = 0.0

    if stats["threads"] > 0:
        stats["vivified"] /= stats["threads"]
        stats["vivify_time"] /= stats["threads"]
        stats["solve_time"] /= stats["threads"]

    return stats, errors

def extract(results_dir):
    results_dir = Path(results_dir)

    setup_file = results_dir / "setup.txt"
    if not setup_file.exists():
        print(f"ERROR: missing {setup_file}")
        return

    setup = read_setup(setup_file)

    timeout = float(setup["TIMEOUT"])
    nprocs = int(setup["MPI_PROCS"])
    threads_per_proc = int(setup["THREADS_PER_PROC"])

    results_dir = Path(results_dir)

    qualified_file = results_dir / "qualified-runtimes-and-results.txt"
    if qualified_file.exists():
        print("results exist")
        return

    # Create output files
    (results_dir / "qualified-runtimes.txt").write_text("")
    (results_dir / "qualified-runtimes-sat.txt").write_text("")
    (results_dir / "qualified-runtimes-unsat.txt").write_text("")

    total_threads = nprocs * threads_per_proc


    nsat = 0
    nunsat = 0
    par2sum = 0.0

    total_vivified = 0
    total_vivify_time = 0.0
    total_solve_time = 0.0

    i = 1

    no_stats_found = []

    while (results_dir / str(i)).is_dir():

        if Path("STOP_IMMEDIATELY").exists():
            print("Stopping because STOP_IMMEDIATELY is present")
            return

        instance_dir = results_dir / str(i)

        solver_stats, stat_errors = collect_solver_stats(instance_dir)

        if stat_errors:
            no_stats_found.append(i);

        total_vivified += solver_stats["vivified"]
        total_vivify_time += solver_stats["vivify_time"]
        total_solve_time += solver_stats["solve_time"]

        logfiles = glob.glob(str(instance_dir / "*" / "log.*"))

        time = None
        time_valid = True

        # Extract RESPONSE_TIME
        for logfile in logfiles:
            with open(logfile, errors="ignore") as f:
                for line in f:
                    if "RESPONSE_TIME" in line:
                        fields = line.split()
                        if len(fields) >= 6:
                            time = fields[5]

        if time is None:
            timeout_found = False
            for logfile in logfiles:
                with open(logfile, errors="ignore") as f:
                    if "WALLCLOCK TIMEOUT: aborting" in f.read():
                        timeout_found = True
                        break

            if timeout_found:
                time = timeout
            else:
                time = 0
                time_valid = False

        time = float(time)

        result = "unknown"

        # Determine SAT/UNSAT
        sat = False
        unsat = False

        for logfile in logfiles:
            with open(logfile, errors="ignore") as f:
                for line in f:
                    if line.startswith("s SATISFIABLE"):
                        sat = True
                        break
                    elif line.startswith("s UNSATISFIABLE"):
                        unsat = True
                        break

        if sat:
            if not time_valid:
                print(f"ERROR::{instance_dir}: found solution but no response time fallback to t = 0")
            result = "sat"
            nsat += 1
            par2sum += time

        elif unsat:
            if not time_valid:
                print(f"ERROR::{instance_dir}: found solution but no response time fallback to t = 0")
            result = "unsat"
            nunsat += 1
            par2sum += time

        else:
            if not time_valid:
                print(f"ERROR::{instance_dir}: found no solution and no response time fallback to t = {timeout}")

            result = "unknown"
            time = timeout
            par2sum += 2 * timeout

        # Append results
        with open(results_dir / "qualified-runtimes.txt", "a") as f:
            f.write(f"{i} {time} {result} {total_threads}\n")

        with open(results_dir / f"qualified-runtimes-{result}.txt", "a") as f:
            f.write(f"{i} {time}\n")

        i += 1

    # Postprocess
    for suffix in ["", "-sat", "-unsat"]:
        infile = results_dir / f"qualified-runtimes{suffix}.txt"
        sortedfile = results_dir / f"sorted-runtimes{suffix}.txt"
        cdffile = results_dir / f"cdf-runtimes{suffix}.txt"

        runtimes = []

        if infile.exists():
            with open(infile) as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        t = float(parts[1])
                        if t < timeout:
                            runtimes.append(t)

        runtimes.sort()

        with open(sortedfile, "w") as f:
            for t in runtimes:
                f.write(f"{t}\n")

        with open(cdffile, "w") as f:
            for rank, t in enumerate(runtimes, start=1):
                f.write(f"{t} {rank}\n")

    shutil.move(
        results_dir / "qualified-runtimes.txt",
        qualified_file
    )

    instances = i - 1
    solved = nsat + nunsat
    par2 = round(par2sum / instances, 3) if instances else 0
    total_vivify_percent = round((
        100.0 * total_vivify_time / total_solve_time
        if total_solve_time > 0
        else 0
    ), 3)

    if len(no_stats_found) != 0:
        print(f"ERRORS found invalid statistics for instances {no_stats_found}")

    print(f"Experiments on {instances} instances found.")
    print(
        f"{solved} solved ({nsat} sat, {nunsat} unsat), "
        f"PAR-2 score: {par2}"
    )

    summary_file = results_dir.parent / "summary_table.txt"

    with open(summary_file, "a") as f:
        f.write(
            f"{results_dir.name} "
            f"{solved} "
            f"{nsat} "
            f"{nunsat} "
            f"{par2} "
            f"{round(total_vivified / instances, 3)} "
            f"{round(total_vivify_time / instances, 3)} "
            f"{round(total_solve_time / instances, 3)} "
            f"{round(total_vivify_percent, 3)}\n"
    )
    

def clean(results_dir):
    results_dir = Path(results_dir)

    print("clean")

    patterns = [
        "qualified-runtimes*",
        "cdf-runtimes*",
        "sorted-runtimes*",
        "table_entry.txt",
    ]

    for pattern in patterns:
        for file in results_dir.glob(pattern):
            if file.is_file():
                file.unlink()

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

    results_dir = Path(args.results_dir)

    if not results_dir.is_dir():
        print(f"ERROR: {results_dir} is not a directory")
        return 1

    if args.clean:
        summary_file = results_dir / "summary_table.txt"
        if summary_file.is_file():
            summary_file.unlink()

            with open(summary_file, "a") as f:
                f.write(
                    f"Name "
                    f"solved "
                    f"SAT "
                    f"UNSAT "
                    f"par2 "
                    f"avg_clauses_vivified "
                    f"avg_vivify_time "
                    f"avg_solve_time "
                    f"%time_vivify\n"
            )

    for portfolio_dir in sorted(results_dir.iterdir()):
        if not portfolio_dir.is_dir():
            continue

        # Skip non-portfolio directories if needed
        if not (portfolio_dir / "setup.txt").exists():
            print(f"Skipping {portfolio_dir}: no setup.txt")
            continue

        print(f"\n=== Processing {portfolio_dir.name} ===")

        if args.clean:
            clean(portfolio_dir)
        
        extract(portfolio_dir)

    return 0

if __name__ == "__main__":
    main()
