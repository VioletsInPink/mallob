#!/usr/bin/env python3

import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import statistics_extractor as st
from pathlib import Path
import re
from scipy.optimize import curve_fit

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    def cadical_sort_key(stat):
        name = stat.solver_name

        match = re.match(r"^(CaDiCaL)(.*)$", name)
        if not match:
            return (name,)

        suffix = match.group(2)

        if suffix == "":
            return (0, 0)
        if suffix == "-":
            return (1, 0)
        m = re.fullmatch(r"_v(\d+\.?\d*)%", suffix)
        if m:
            return (2, float(m.group(1)))

        if suffix.startswith("+"):
            m = re.search(r"_v(\d+)%", suffix)
            if m:
                return (3, int(m.group(1)))
            return (3, 0)

        return (4, suffix)

    stats = sorted(
        st.getStats(args.results),
        key=cadical_sort_key,
    )

    ##########################
    # Plot vivified vs busy time 
    #########################
    # plt.figure(figsize=(8, 6))
    # for s in stats:
    #     if s.solver_name == "CaDiCaL-":
    #         continue
    #
    #     ys = np.array([x.vivified for x in s.instance_stats if x.result != st.RESULT.UNKOWN])
    #     xs = np.array([y.busy_time for y in s.instance_stats if y.result != st.RESULT.UNKOWN])
    #
    #     plt.scatter(xs, ys, s=2, label=s.solver_name)
    #
    #     # Filter out non-positive values for log safety
    #     mask = (xs > 0) & (ys > 0)
    #     x_valid = xs[mask]
    #     y_valid = ys[mask]
    #
    #     if len(x_valid) == 0:
    #         continue
    #
    #     # np.polyfit fits y vs log(x)
    #     poly = np.polynomial.Polynomial.fit(x_valid, y_valid, deg=3)
    #
    #     # 2. Generate smooth curve points for plotting
    #     x_line = np.linspace(x_valid.min(), x_valid.max(), 200)
    #     y_line = poly(x_line)
    #
    #     plt.plot(
    #         x_line,
    #         y_line,
    #         linestyle="--",
    #         linewidth=2,
    #         label=f"Log fit ({s.solver_name})"
    #     )
    #
    # plt.ylabel("Vivified clauses (average per solver thread)")
    # plt.xlabel("busy time")
    # plt.yscale("log")
    # # plt.xscale("log")
    # plt.title("Vivified clauses vs. busy time")
    #
    # plt.legend()
    # plt.grid(alpha=0.3)
    # plt.tight_layout()
    # plt.savefig(args.out_dir  / "vivify_over_time.svg")
    # plt.close()

    ##########################
    # Plot percent vivify time vs busy time 
    #########################
    # plt.figure(figsize=(8, 6))
    # for s in stats:
    #     ys = np.array([100 * x.vivify_time / x.busy_time if x.busy_time > 0 else 0 for x in s.instance_stats])
    #     xs = np.array([y.busy_time for y in s.instance_stats])
    #
    #     plt.scatter(xs, ys, s=2, label=s.solver_name)
    #     a, b = np.polynomial.Polynomial.fit(x_valid, y_valid, deg=1)
    #
    #     # 2. Generate smooth curve points for plotting
    #     x_line = np.linspace(x_valid.min(), x_valid.max(), 200)
    #     y_line = a * np.log(x_line) + b
    #     #
    #     # plt.plot(
    #     #     x_line,
    #     #     y_line,
    #     #     linestyle="--",
    #     #     linewidth=2,
    #     #     label=f"Log fit ({s.solver_name})"
    #     # )
    #
    # plt.ylabel("% time spend Vivifying (avg per solver thread)")
    # plt.xlabel("busy time")
    # # plt.yscale("log")
    # # plt.xscale("log")
    # plt.title("Vivified clauses vs. busy time")
    #
    # plt.legend()
    # plt.grid(alpha=0.3)
    # plt.tight_layout()
    # plt.savefig(args.out_dir / "vivify_percent_over_time.svg")
    # plt.close()

    ##########################
    # cdf
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
    plt.savefig(args.out_dir / "cdf.svg")
    plt.ylim(200, None)
    plt.savefig(args.out_dir / "cdf_zoom_y200.svg")
    plt.close()

    ##########################
    # scheduled over busy_time
    #########################
    plt.figure(figsize=(8, 6))
    for s in stats:
        # if "+" in s.solver_name:
        #     continue
        busy_times = np.array([x.busy_time for x in s.instance_stats])
        if len(busy_times) == 0:
            continue

        sched = np.array([x.vivify_sched for x in s.instance_stats])
        if len(sched) == 0:
            continue

        xs = np.sort(busy_times)
        ys = np.sort(sched)
        plt.plot(xs, ys, label=s.solver_name, drawstyle="steps-post", linewidth=1)

    plt.xlabel("Busy Time (s)")
    plt.ylabel("Number of Instances Scheduled")
    plt.yscale("log")
    plt.title("number of Scheduled Clauses over solve time")
    
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_dir / "sched_over_busy_time.svg")
    plt.close()


    ##########################
    # sched over busy_time
    #########################
    xs = []
    ys = []
    max_threshold=0
    plt.figure(figsize=(8, 6))
    for s in stats:
        # if "+" in s.solver_name:
        #     continue

        x = s.percent.avg.vivify_time.avg.busy_time
        y = s.avg.vivify_sched / x if x > 0 else 0
        print(x, y, s.solver_name)

        if s.solver_name == "CaDiCaL" or s.solver_name == "2024_CaDiCaL":
            max_threshold = y
        else:
            if "v" in s.solver_name:
                xs.append(x)
                ys.append(y)

        plt.scatter(x, y, label=s.solver_name)

        if "-" in s.solver_name:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 5),
                textcoords="offset points",
                fontsize=8,
            )
        else:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, -5),
                textcoords="offset points",
                fontsize=8,
            )


    # plt.axhline(max_threshold, color="red", ls="--", lw=2, label="Maximum capacity")

    xs = np.array(xs)
    ys = np.array(ys)
    mask = xs > 0
    xs = xs[mask]
    ys = ys[mask]
    # 1/x model
    def inverse_fit(x, a, b):
        return a / x + b
    params, _ = curve_fit(inverse_fit, xs, ys)
    a, b = params
    x_fit = np.linspace(0.01, 100, 500)
    y_fit = inverse_fit(x_fit, a, b)
    # plt.scatter(xs, ys, label="data")
    plt.plot(
        x_fit,
        y_fit,
        label=f"fit: y={a:.2f}/x + {b:.2f}",
    )


    # Shade infeasible region
    # plt.fill_between(
    #     np.linspace(0, 100, 500),
    #     max_threshold,
    #     5000000,
    #     color="tab:red",
    #     alpha=0.15,
    # )
    # plt.text(
    #     5,
    #     max_threshold * 1.05,
    #     "approximately max capacity",
    #     color="tab:red",
    # )
    plt.xlabel("vivify time %")
    plt.ylabel("scheduled clauses per vivify sec")
    plt.xlim(0, max(xs) * 1.2)
    plt.ylim(0, max_threshold * 1.2)
    # plt.yscale("log")
    plt.title("scheduled clauses over vivify time")
    
    plt.grid(alpha=0.3)
    # plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_dir / "sched_per_vivi_sec.svg")
    plt.close()

    ##########################
    # vivified over vivi_time
    #########################
    xs = []
    ys = []
    plt.figure(figsize=(8, 6))
    for s in stats:
        # if "+" in s.solver_name:
        #     continue
            
        x = s.percent.avg.vivify_time.avg.busy_time
        y = s.avg.vivified / s.avg.vivify_time if s.avg.vivify_time > 0 else 0

        xs.append(x)
        ys.append(y)

        plt.scatter(x, y, label=s.solver_name)

        if "-" in s.solver_name:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 5),
                textcoords="offset points",
                fontsize=8,
            )
        else:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 2),
                textcoords="offset points",
                fontsize=8,
            )

    plt.xlabel("vivify time %")
    plt.ylabel("vivified clauses per vivify sec")
    plt.xlim(0, max(xs) * 1.2)
    plt.ylim(0, max(ys) * 1.3)
    # plt.yscale("log")
    plt.title("vivified clauses over vivify time")
    
    plt.grid(alpha=0.3)
    # plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_dir / "vivified_per_vivi_sec.svg")
    plt.close()

    ##########################
    # vivify strs over vivi_time
    #########################
    xs = []
    ys = []
    plt.figure(figsize=(8, 6))
    for s in stats:
        # if "+" in s.solver_name:
        #     continue
            
        x = s.percent.avg.vivify_time.avg.busy_time
        y = s.avg.vivify_strs
 
        xs.append(x)
        ys.append(y)

        plt.scatter(x, y, label=s.solver_name)

        if "-" in s.solver_name:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 5),
                textcoords="offset points",
                fontsize=8,
            )
        else:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 2),
                textcoords="offset points",
                fontsize=8,
            )

    plt.xlabel("vivify time %")
    plt.ylabel("strenghened clauses")
    plt.xlim(min(xs) * 0.9, max(xs) * 1.2)
    plt.ylim(min(ys) * 0.8, max(ys) * 1.3)
    # plt.yscale("log")
    plt.title("strenghened clauses over vivification percentage")
    
    plt.grid(alpha=0.3)
    # plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_dir / "strs_per_vivi_sec.svg")
    plt.close()

    ##########################
    # vivify strs over vivi_time
    #########################
    xs = []
    ys = []
    plt.figure(figsize=(8, 6))
    for s in stats:
        # if "+" in s.solver_name:
        #     continue
            
        x = s.percent.avg.vivify_time.avg.busy_time
        # y = 100* (s.avg.vivify_strs / s.avg.vivify_checked if s.avg.vivify_checked > 0 else 0)
        y = 100* (s.avg.vivify_strs / s.avg.vivify_time if s.avg.vivify_time > 0 else 0)
 
        if s.solver_name != "CaDiCaL":
            if s.solver_name != "CaDiCaL-":
                xs.append(x)
                ys.append(y)

        plt.scatter(x, y, label=s.solver_name)

        if "-" in s.solver_name:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 5),
                textcoords="offset points",
                fontsize=8,
            )
        else:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 2),
                textcoords="offset points",
                fontsize=8,
            )
    # plt.axhline(max_threshold, color="red", ls="--", lw=2, label="Maximum capacity")
    #
    # # 1/x model
    # def inverse_fit(x, a, b):
    #     return a / x + b
    # params, _ = curve_fit(inverse_fit, xs, ys)
    # a, b = params
    # x_fit = np.linspace(0.01, 100, 500)
    # y_fit = inverse_fit(x_fit, a, b)
    # # plt.scatter(xs, ys, label="data")
    # plt.plot(
    #     x_fit,
    #     y_fit,
    #     label=f"fit: y={a:.2f}/x + {b:.2f}",
    # )


    # Shade infeasible region
    # plt.fill_between(
    #     np.linspace(0, 100, 500),
    #     max_threshold,
    #     5000000,
    #     color="tab:red",
    #     alpha=0.15,
    # )
    # plt.text(
    #     5,
    #     max_threshold * 1.05,
    #     "approximately max capacity",
    #     color="tab:red",
    # )

    plt.xlabel("vivify time %")
    plt.ylabel("strengthened per second in ivification")
    plt.xlim(0, max(xs) * 1.2)
    plt.ylim(0, max(ys) * 1.3)
    # plt.yscale("log")
    plt.title("strenghened clauses per sec over percent vivification")
    
    plt.grid(alpha=0.3)
    # plt.legend()
    plt.savefig(args.out_dir / "efficiency_strs_per_vivi_sec.svg")
    plt.close()

    ##########################
    # subs over vivi_time
    #########################
    xs = []
    ys = []
    plt.figure(figsize=(8, 6))
    for s in stats:
        # if "+" in s.solver_name:
        #     continue
            
        x = s.percent.avg.vivify_time.avg.busy_time
        y = s.avg.vivify_subs

        xs.append(x)
        ys.append(y)

        plt.scatter(x, y, label=s.solver_name)

        if "-" in s.solver_name:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 5),
                textcoords="offset points",
                fontsize=8,
            )
        else:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 2),
                textcoords="offset points",
                fontsize=8,
            )

    plt.xlabel("vivify time %")
    plt.ylabel("subsumed clauses from vivification")
    plt.xlim(min(xs) * 0.9, max(xs) * 1.2)
    plt.ylim(min(ys) * 0.8, max(ys) * 1.3)
    # plt.yscale("log")
    plt.title("subsumed clauses from vivification over vivify percentage")
    
    plt.grid(alpha=0.3)
    # plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_dir / "subs_per_vivi_sec.svg")
    plt.close()

    ##########################
    # subsumed over vivi_time
    #########################
    xs = []
    ys = []
    plt.figure(figsize=(8, 6))
    for s in stats:
        if "+" in s.solver_name:
            continue
            
        x = s.percent.avg.vivify_time.avg.busy_time
        base = (s.avg.busy_time) / (s.avg.busy_time - s.avg.vivify_time) if s.avg.busy_time > 0 else 0
        y = (s.avg.subsumed) / (1 - (x / 100)) if x > 0 else 0

        xs.append(x)
        ys.append(y)

        plt.scatter(x, y, label=s.solver_name)

        if "-" in s.solver_name:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 5),
                textcoords="offset points",
                fontsize=8,
            )
        else:
            plt.annotate(
                s.solver_name,
                (x, y),
                xytext=(4, 2),
                textcoords="offset points",
                fontsize=8,
            )

    plt.xlabel("vivify time %")
    plt.ylabel("subsumed clauses per vivify sec")
    plt.xlim(min(xs) * 0.9, max(xs) * 1.2)
    plt.ylim(min(ys) * 0.8, max(ys) * 1.3)
    # plt.yscale("log")
    plt.title("subsumed clauses over vivify time")
    
    plt.grid(alpha=0.3)
    # plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_dir / "subsumed_per_vivi_sec.svg")
    plt.close()

    #####
    #print the number of scheduled clauses
    for s in stats:
        if (s.solver_name == "2024_CaDiCaL" or s.solver_name == "2024_CaDiCaL_dist") :
            print(s.solver_name, s.avg.vivify_sched)

if __name__ == "__main__":
    main()
