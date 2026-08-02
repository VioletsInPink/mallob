#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from dataclasses import fields
import matplotlib.pyplot as plt
import statistics_extractor
import numpy as np
import matplotlib.colors as mcolors

border_lo = 1
border_hi = 5000

def parse_args():
    p = argparse.ArgumentParser(description="Create scatter plots comparing per-instance solver statistics.")

    p.add_argument("--solver", "-s", nargs=2, action="append", metavar=("LEFT", "RIGHT"), required=True,
                   help="Compare LEFT against RIGHT (repeatable).")
    p.add_argument("--metric", "-m", metavar="stat", choices=statistics_extractor.InstanceStats.plotable(), default="busy_time",
                   help="Per-instance metric to plot.")
    p.add_argument("--uv_field", "--uv", metavar="stat", choices=statistics_extractor.InstanceStats.plotable(), default=None,
                   help="color nodes after theyr position on the uv field") 
    p.add_argument("--uv_log", action="store_true",
                   help="uv uses log scale") 
    p.add_argument("--timeout", "-T", type=float, required=True,
                   help="Experiment timeout in seconds.")
    p.add_argument("--output", "-o", metavar="FILE",
                   help="Write plot to FILE instead of showing it.")
    p.add_argument("--results_dir", "-r", metavar="FILE", required=True,
                   help="the directory whith the stats")
    p.add_argument("--title",
                   help="Figure title.")
    p.add_argument("--xlabel",
                   help="X-axis label (defaults to left solver).")
    p.add_argument("--ylabel",
                   help="Y-axis label (defaults to right solver).")
    p.add_argument("--logscale", "--log", "-l", action="store_true",
                   help="Use logarithmic axes.")

    return p.parse_args()


def build_scatter(left_stats, right_stats, metric, timeout):
    x, y = [], []
    out = math.exp((math.log(timeout) + math.log(timeout * 2)) / 2)

    for a, b in zip(left_stats.instance_stats, right_stats.instance_stats):
        xv = getattr(a, metric)
        yv = getattr(b, metric)
        x.append(xv if xv <= timeout else out)
        y.append(yv if yv <= timeout else out)

    return x, y


def plot_summary(stats_list, metric):
    plt.figure(figsize=(6,4))
    plt.bar([s.solver_name for s in stats_list],
            [getattr(s, metric) for s in stats_list])
    plt.ylabel(metric)
    plt.tight_layout()


def main():
    args = parse_args()

    stats_list = statistics_extractor.getStats(args.results_dir)

    stats = {s.solver_name: s for s in stats_list}


    if args.metric in statistics_extractor.InstanceStats.plotable():
        fig, ax = plt.subplots(figsize=(5,5))
        if args.logscale:
            ax.set_xscale("log")
            ax.set_yscale("log")

        hi_x = hi_y = float('-inf')
        lo_x = lo_y = float('inf')

        for left, right in args.solver:
            x, y = build_scatter(stats[left], stats[right], args.metric, args.timeout)
            if args.uv_field is not None:
                u, v = build_scatter(stats[left], stats[right], args.uv_field, args.timeout)

                u = np.asarray(u)
                v = np.asarray(v)

                # Normalize to [0,1]
                if args.uv_log:
                    eps = 1e-12
                    u = np.log10(np.maximum(u, eps))
                    v = np.log10(np.maximum(v, eps))

                u = (u - u.min()) / (u.max() - u.min())
                v = (v - v.min()) / (v.max() - v.min())

                # Hue from angle, saturation from radius
                angle = (np.arctan2(v - 0.5, u - 0.5) + np.pi) / (2 * np.pi)
                radius = np.sqrt((u - 0.5)**2 + (v - 0.5)**2)
                radius /= radius.max()

                colors = mcolors.hsv_to_rgb(
                    np.column_stack([angle, radius, np.ones_like(angle)])
                )
                ax.scatter(x, y, color=colors, cmap="viridis", marker="o", facecolors="None",
                        label=f"{stats[left].solver_name} vs {stats[right].solver_name}")
            else: 
                ax.plot(x, y, "o", fillstyle="none",
                        label=f"{stats[left].solver_name} vs {stats[right].solver_name}")
            hi_x = max(hi_x, max(x))
            lo_x = min(lo_x, min(x))
            hi_y = max(hi_y, max(y))
            lo_y = min(lo_y, min(y))

        hi_avg = max(hi_x, hi_y)
        lo = 0
        if args.logscale:
            factor = 1.1
            hi_lo = hi_avg / factor
            hi_hi = hi_avg * factor
        else:
            hi_lo = hi_avg - 10
            hi_hi = hi_avg + 10

        ax.set_xlim(left=1, right=hi_hi)
        ax.set_ylim(bottom=1, top=hi_hi)

        ax.plot([0, hi_lo], [0, hi_lo], 'black', alpha=0.3, linestyle="--")
        ax.plot([lo, hi_lo], [hi_lo, hi_lo], 'black', alpha=1)
        ax.plot([hi_lo, hi_lo], [lo, hi_lo], 'black', alpha=1)
        ax.fill_between([lo, hi_hi], hi_hi, hi_lo, alpha=0.3, color='gray', zorder=0)
        ax.fill_between([hi_lo, hi_hi], lo, hi_hi, alpha=0.3, color='gray', zorder=0)

        if args.uv_field:
            from mpl_toolkits.axes_grid1.inset_locator import inset_axes

            ax_uv = inset_axes(ax, width="25%", height="25%", loc="upper left")
            ax_uv.scatter(u, v, c=colors, s=8)
            ax_uv.set_xlabel("u")
            ax_uv.set_ylabel("v")

        ax.legend()
        ax.set_xlabel(args.xlabel or args.solver[0][0])
        ax.set_ylabel(args.ylabel or args.solver[0][1])

    if args.output:
        plt.savefig(args.output)
    else:
        plt.show()


if __name__ == "__main__":
    main()
