#!/usr/bin/env python3

import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import statistics_extractor as st
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    stats = st.getStats(args.results)

    ##########################
    # Plot vivified vs busy time 
    #########################
    plt.figure(figsize=(8, 6))
    for s in stats:
        if s.solver_name == "CaDiCaL-":
            continue

        ys = np.array([x.vivified for x in s.instance_stats if x.result != st.RESULT.UNKOWN])
        xs = np.array([y.busy_time for y in s.instance_stats if y.result != st.RESULT.UNKOWN])

        plt.scatter(xs, ys, s=2, label=s.solver_name)
        
        # Filter out non-positive values for log safety
        mask = (xs > 0) & (ys > 0)
        x_valid = xs[mask]
        y_valid = ys[mask]

        if len(x_valid) == 0:
            continue

        # np.polyfit fits y vs log(x)
        poly = np.polynomial.Polynomial.fit(x_valid, y_valid, deg=3)

        # 2. Generate smooth curve points for plotting
        x_line = np.linspace(x_valid.min(), x_valid.max(), 200)
        y_line = poly(x_line)

        plt.plot(
            x_line,
            y_line,
            linestyle="--",
            linewidth=2,
            label=f"Log fit ({s.solver_name})"
        )

    plt.ylabel("Vivified clauses (average per solver thread)")
    plt.xlabel("busy time")
    plt.yscale("log")
    # plt.xscale("log")
    plt.title("Vivified clauses vs. busy time")
    
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out_dir  / "vivify_over_time.svg")
    plt.close()

    ##########################
    # Plot percent vivify time vs busy time 
    #########################
    plt.figure(figsize=(8, 6))
    for s in stats:
        ys = np.array([100 * x.vivify_time / x.busy_time if x.busy_time > 0 else 0 for x in s.instance_stats])
        xs = np.array([y.busy_time for y in s.instance_stats])

        plt.scatter(xs, ys, s=2, label=s.solver_name)
        a, b = np.polynomial.Polynomial.fit(x_valid, y_valid, deg=1)

        # 2. Generate smooth curve points for plotting
        x_line = np.linspace(x_valid.min(), x_valid.max(), 200)
        y_line = a * np.log(x_line) + b
        #
        # plt.plot(
        #     x_line,
        #     y_line,
        #     linestyle="--",
        #     linewidth=2,
        #     label=f"Log fit ({s.solver_name})"
        # )

    plt.ylabel("% time spend Vivifying (avg per solver thread)")
    plt.xlabel("busy time")
    # plt.yscale("log")
    # plt.xscale("log")
    plt.title("Vivified clauses vs. busy time")
    
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out_dir / "vivify_percent_over_time.svg")
    plt.close()

    ##########################
    # Plot percent vivify time vs busy time 
    #########################
    plt.figure(figsize=(8, 6))
    for s in stats:
        solve_times = np.array([x.busy_time for x in s.instance_stats if x.result != st.RESULT.UNKOWN ])
        valid_times = solve_times[solve_times > 0]
        if len(valid_times) == 0:
            continue

        xs = np.sort(valid_times)
        ys = np.arange(1, len(xs) + 1)
        plt.plot(xs, ys, label=s.solver_name, drawstyle="steps-post", linewidth=1)

    plt.xlabel("Solve Time / Busy Time (seconds)")
    plt.ylabel("Number of Instances Solved (time <= x)")
    plt.title("Cumulative Solved Instances over Time")
    
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_dir / "vivify_percent_over_time.svg")
    plt.close()




if __name__ == "__main__":
    main()
