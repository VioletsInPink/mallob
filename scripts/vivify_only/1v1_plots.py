#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

import statistics_extractor
from statistics_extractor import RESULT


border_lo = 1
border_hi = 5000


def parse_args():
    p = argparse.ArgumentParser(
        description="Create scatter plots comparing per-instance solver statistics."
    )

    p.add_argument(
        "--solver",
        "-s",
        nargs=2,
        action="append",
        metavar=("LEFT", "RIGHT"),
        required=True,
        help="Compare LEFT against RIGHT (repeatable).",
    )

    p.add_argument(
        "--metric",
        "-m",
        nargs="+",
        metavar="stat",
        choices=statistics_extractor.InstanceStats.plotable(),
        default=["busy_time"],
        help="Per-instance metrics to plot.",
    )

    p.add_argument(
        "--all_stats",
        action="store_true",
        help="Generate a plot for every available statistic.",
    )

    p.add_argument(
        "--percent",
        "-p",
        metavar="stat",
        choices=statistics_extractor.InstanceStats.plotable(),
        default=None,
        help="percent to normalize.",
    )

    p.add_argument(
        "--uv_field",
        "--uv",
        metavar="stat",
        choices=statistics_extractor.InstanceStats.plotable(),
        default=None,
        help="color nodes after their position on the uv field.",
    )

    p.add_argument(
        "--uv_log",
        action="store_true",
        help="uv uses log scale.",
    )

    p.add_argument(
        "--timeout",
        "-T",
        type=float,
        required=True,
        help="Experiment timeout in seconds.",
    )

    p.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help=(
            "Write plot to FILE instead of showing it. "
            "When --all_stats is used, this is treated as an output directory."
        ),
    )

    p.add_argument(
        "--results_dir",
        "-r",
        metavar="FILE",
        required=True,
        help="The directory with the stats.",
    )

    p.add_argument(
        "--results_dir2",
        "-r2",
        metavar="FILE",
        help="The second directory with the stats.",
    )

    p.add_argument(
        "--title",
        "-t",
        help="Figure title.",
    )

    p.add_argument(
        "--xlabel",
        help="X-axis label (defaults to left solver).",
    )

    p.add_argument(
        "--ylabel",
        help="Y-axis label (defaults to right solver).",
    )

    p.add_argument(
        "--logscale",
        "--log",
        "-l",
        action="store_true",
        help="Use logarithmic axes.",
    )

    p.add_argument(
        "--out_range",
        "--or",
        action="store_false",
        help="Use the outside scale.",
    )

    p.add_argument(
        "--sat_unsat",
        action="store_false",
        help="Differentiate between sat and unsat.",
    )

    p.add_argument(
        "--bounds_lo",
        "-b_lo",
        type=float,
        help="The lower bound for the axes.",
    )

    p.add_argument(
        "--bounds_hi",
        "-b_hi",
        type=float,
        help="The upper bound for the axes.",
    )

    p.add_argument(
        "--per_thread",
        "-pt",
        action="store_true",
        help="Devide by the number of threads.",
    )

    return p.parse_args()


def get_metric(obj, metric, percent):
    if percent:
        obj = getattr(obj, "percent")
        obj = getattr(obj, metric)
        obj = getattr(obj, percent)
    else:
        obj = getattr(obj, metric)

    return obj


def build_scatter(left_stats, right_stats, metric, percent, timeout, per_thread):
    x = []
    y = []

    sat_x = []
    sat_y = []

    unsat_x = []
    unsat_y = []

    unknown_x = []
    unknown_y = []

    for a, b in zip(
        left_stats.instance_stats,
        right_stats.instance_stats,
    ):
        xv = get_metric(a, metric, percent)
        yv = get_metric(b, metric, percent)

        if per_thread:
            xt = get_metric(a, "num_active_threads", None)
            yt = get_metric(a, "num_active_threads", None)

            xv /= xt
            yv /= yt

        x.append(xv)
        y.append(yv)

        if getattr(a, "result") == RESULT.SAT:
            sat_x.append(xv)
            sat_y.append(yv)

        elif getattr(a, "result") == RESULT.UNSAT:
            unsat_x.append(xv)
            unsat_y.append(yv)

        else:
            if getattr(b, "result") == RESULT.SAT:
                sat_x.append(xv)
                sat_y.append(yv)

            elif getattr(b, "result") == RESULT.UNSAT:
                unsat_x.append(xv)
                unsat_y.append(yv)
            else: 
                unknown_x.append(xv)
                unknown_y.append(yv)

    return (
        x,
        y,
        sat_x,
        sat_y,
        unsat_x,
        unsat_y,
        unknown_x,
        unknown_y,
    )


def plot_summary(stats_list, metric):
    plt.figure(figsize=(6, 4))

    plt.bar(
        [s.solver_name for s in stats_list],
        [getattr(s, metric) for s in stats_list],
    )

    plt.ylabel(metric)
    plt.tight_layout()


def normalize_uv(values):
    """
    Normalize an array to [0, 1].

    If all values are equal, return 0.5 for every value.
    """
    values = np.asarray(values, dtype=float)

    if values.size == 0:
        return values

    value_min = values.min()
    value_max = values.max()

    if value_max == value_min:
        return np.full_like(values, 0.5)

    return (values - value_min) / (value_max - value_min)


def plot_metric(
    args,
    stats,
    left,
    right,
    metric,
    output=None,
):
    fig, ax = plt.subplots(figsize=(5, 5))

    if args.logscale:
        ax.set_xscale("log")
        ax.set_yscale("log")

    (
        x,
        y,
        sx,
        sy,
        usx,
        usy,
        unkx,
        unky,
    ) = build_scatter(
        stats[left],
        stats[right],
        metric,
        args.percent,
        args.timeout,
        args.per_thread
    )

    if not x or not y:
        print(
            f"Skipping {left} vs {right} ({metric}): "
            "no data points."
        )
        plt.close(fig)
        return

    if args.uv_field is not None:
        (
            u,
            v,
            _,
            _,
            _,
            _,
            _,
            _,
        ) = build_scatter(
            stats[left],
            stats[right],
            args.uv_field,
            args.percent,
            args.timeout,
            args.per_thread
        )

        u = np.asarray(u, dtype=float)
        v = np.asarray(v, dtype=float)

        if args.uv_log:
            eps = 1e-12

            u = np.log10(np.maximum(u, eps))
            v = np.log10(np.maximum(v, eps))

        u = normalize_uv(u)
        v = normalize_uv(v)

        # Hue from angle, saturation from radius.
        angle = (
            np.arctan2(
                v - 0.5,
                u - 0.5,
            )
            + np.pi
        ) / (2 * np.pi)

        radius = np.sqrt(
            (u - 0.5) ** 2
            + (v - 0.5) ** 2
        )

        if radius.size > 0 and radius.max() != 0:
            radius /= radius.max()

        colors = mcolors.hsv_to_rgb(
            np.column_stack(
                [
                    angle,
                    radius,
                    np.ones_like(angle),
                ]
            )
        )

        ax.scatter(
            x,
            y,
            color=colors,
            marker="o",
            facecolors="None",
            label=(
                f"{stats[left].solver_name} vs "
                f"{stats[right].solver_name}"
            ),
        )

    else:
        if not args.sat_unsat:
            ax.scatter(
                x,
                y,
                marker="o",
                label=(
                    f"{stats[left].solver_name} vs "
                    f"{stats[right].solver_name}"
                ),
            )

        else:
            print(
                left,
                len(stats[left].instance_stats),
                right,
                len(stats[right].instance_stats),
                metric,
            )

            if usx:
                ax.scatter(
                    usx,
                    usy,
                    marker="o",
                    facecolors="blue",
                    label="unsat",
                )

            if unkx:
                ax.scatter(
                    unkx,
                    unky,
                    marker=".",
                    facecolors="green",
                    label="unknown",
                )

            if sx:
                ax.scatter(
                    sx,
                    sy,
                    marker="x",
                    facecolors="red",
                    label="sat",
                )

    hi_x = max(x)
    lo_x = min(x)
    hi_y = max(y)
    lo_y = min(y)

    hi_avg = max(hi_x, hi_y)
    lo_avg = min(lo_x, lo_y)

    if args.bounds_hi:
        hi_avg = args.bounds_hi

    if args.bounds_lo:
        lo_avg = args.bounds_lo

    lo = 0

    if args.logscale:
        factor = 1.1
        hi_hi = hi_avg * factor
        hi_lo = hi_avg / factor
    else:
        hi_hi = hi_avg + 10
        hi_lo = hi_avg - 10

    if args.logscale:
        ax.set_xlim(
            left=max(
                0.001,
                min(lo_avg, 1),
            ),
            right=hi_hi,
        )

        ax.set_ylim(
            bottom=max(
                0.001,
                min(lo_avg, 1),
            ),
            top=hi_hi,
        )

    else:
        ax.set_xlim(
            left=0,
            right=hi_hi,
        )

        ax.set_ylim(
            bottom=0,
            top=hi_hi,
        )

    # Diagonal line.
    #
    # For logscale, starting at zero is invalid, so use the
    # lower axis bound instead.
    if args.logscale:
        diagonal_lo = max(
            0.001,
            min(lo_avg, 1),
        )
    else:
        diagonal_lo = 0

    ax.plot(
        [diagonal_lo, hi_hi],
        [diagonal_lo, hi_hi],
        "black",
        alpha=0.3,
        linestyle="--",
    )

    if args.out_range:
        ax.plot(
            [lo, hi_lo],
            [hi_lo, hi_lo],
            "black",
            alpha=1,
        )

        ax.plot(
            [hi_lo, hi_lo],
            [lo, hi_lo],
            "black",
            alpha=1,
        )

        ax.fill_between(
            [lo, hi_hi],
            hi_hi,
            hi_lo,
            alpha=0.3,
            color="gray",
            zorder=0,
        )

        ax.fill_between(
            [hi_lo, hi_hi],
            lo,
            hi_hi,
            alpha=0.3,
            color="gray",
            zorder=0,
        )

    if args.uv_field:
        from mpl_toolkits.axes_grid1.inset_locator import inset_axes

        ax_uv = inset_axes(
            ax,
            width="25%",
            height="25%",
            loc="upper left",
        )

        ax_uv.scatter(
            u,
            v,
            c=colors,
            s=8,
        )

        ax_uv.set_xlabel("u")
        ax_uv.set_ylabel("v")

    if args.title:
        ax.set_title(args.title)

    ax.set_xlabel(
        args.xlabel
        or stats[left].solver_name
    )

    ax.set_ylabel(
        args.ylabel
        or stats[right].solver_name
    )

    # When generating all stats, the metric should be visible
    # in the title even if the user did not specify --title.
    if args.all_stats and not args.title:
        ax.set_title(metric)

    ax.legend()

    plt.tight_layout()

    if output:
        plt.savefig(output)
        plt.close(fig)
    else:
        plt.show()


def main():
    args = parse_args()

    stats_list = statistics_extractor.getStats(
        args.results_dir
    )

    stats = {
        s.solver_name: s
        for s in stats_list
    }

    # If a second result directory is provided, load its
    # solvers separately.
    if args.results_dir2:
        stats_list2 = statistics_extractor.getStats(
            args.results_dir2
        )

        stats.update(
            {
                s.solver_name: s
                for s in stats_list2
            }
        )

    available_stats = statistics_extractor.InstanceStats.plotable()

    if args.all_stats:
        metrics = available_stats

        if args.output:
            os.makedirs(
                args.output,
                exist_ok=True,
            )
    else:
        metrics = args.metric

    for left, right in args.solver:
        if left not in stats:
            raise ValueError(
                f"Unknown solver '{left}'. "
                f"Available solvers: {', '.join(stats.keys())}"
            )

        if right not in stats:
            raise ValueError(
                f"Unknown solver '{right}'. "
                f"Available solvers: {', '.join(stats.keys())}"
            )

        for metric in metrics:
            if args.output:
                output = os.path.join(
                    args.output,
                    f"{stats[left].solver_name}"
                    f"_vs_"
                    f"{stats[right].solver_name}"
                    f"_{metric}.svg",
                )
            else:
                output = (
                    f"{stats[left].solver_name}"
                    f"_vs_"
                    f"{stats[right].solver_name}"
                    f"_{metric}.svg"
                )

            print(
                f"Plotting "
                f"{stats[left].solver_name} vs "
                f"{stats[right].solver_name}: "
                f"{metric}"
            )

            print(output)
            plot_metric(
                args,
                stats,
                left,
                right,
                metric,
                output,
            )


if __name__ == "__main__":
    main()
