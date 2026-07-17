#!/usr/bin/env python3

import argparse
import re
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gmean

RESPONSE_RE = re.compile(r"RESPONSE_TIME.*?([0-9]+(?:\.[0-9]+)?)$")

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

def parse_response_time(instance_dir):
    response_time = None

    for proc_dir in instance_dir.iterdir():
        if not proc_dir.is_dir():
            continue

        for logfile in proc_dir.glob("log.*"):
            if not logfile.is_file():
                    continue

            if not re.fullmatch(r"log\.\d+", logfile.name):
                continue

            with open(logfile, errors="ignore") as f:
                for line in f:
                    m = RESPONSE_RE.search(line)
                    if m:
                        response_time = float(m.group(1))

    return response_time


def add_data(portfolio, plt):
    xs = []
    ys = []

    for instance in sorted(
        portfolio.iterdir(),
        key=lambda p: int(p.name) if p.name.isdigit() else 10**9,
    ):
        if not instance.is_dir() or not instance.name.isdigit():
            continue

        # response_time = parse_response_time(instance)
        #
        # if response_time is None:
        #     continue

        stats, errors = collect_solver_stats(instance)

        if errors:
            print(f"{portfolio.name}/{instance.name}: {errors} missing files")

        ys.append(stats["vivified"])
        xs.append(stats["solve_time"])

    plt.scatter(xs, ys, s=3, label=portfolio.name)

    order = np.argsort(xs)

    x_sorted = np.array(xs)[order]
    y_sorted = np.array(ys)[order]

    mask = (x_sorted > 0) & (y_sorted > 0)

    x_sorted = x_sorted[mask]
    y_sorted = y_sorted[mask]

    bins = 30
    x_avg = []
    y_avg = []

    start = x_sorted.min()
    end = x_sorted.max()

    for chunk in np.array_split(range(len(x_sorted)), bins):
            x_avg.append(gmean(x_sorted[chunk]))
            y_avg.append(gmean(y_sorted[chunk]))

    plt.plot(
        x_avg,
        y_avg,
        linestyle="--",
        linewidth=2,
        label="Binned average"
    )



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    args = parser.parse_args()

    plt.figure(figsize=(8, 6))

    solvers = [
        "CaDiCaL",
        "CaDiCaL_v1",
        "CaDiCaL_v2",
        "CaDiCaL_v3",
        "CaDiCaL_v4",
        # "CaDiCaL_v5",
    ]

    results_dir = Path(args.results)
    for portfolio_dir in sorted(results_dir.iterdir()):
        if portfolio_dir.name not in solvers:
            continue
        if portfolio_dir.is_dir():
            add_data(portfolio_dir, plt)

    plt.ylabel("Vivified clauses (average per solver thread)")
    plt.xlabel("percent time spend in vivify")
    plt.yscale("log")
    plt.title("Vivified clauses vs. solve time")
    
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
