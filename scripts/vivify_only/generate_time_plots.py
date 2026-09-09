#!/usr/bin/env python3

from matplotlib.pylab import xlim
import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

import statistics_extractor as st


# ===========================================================================
# Solver selection and fitting
# ===========================================================================

@dataclass
class SolverGroup:
    """
    A group of solvers to plot.

    pattern:
        Regular expression matching solver names.

        '*' is supported as a convenient shorthand for '.*'.

        Examples:
            *_dist
            .*_dist
            2024_CaDiCaL_v\\d+%
            yyyy_CaDiCaL_v\\d+%

    fit:
        Name of the fit to apply to this group.

        Supported:
            None
            "linear"
            "inverse"
    """
    name: str
    pattern: str
    fit: Optional[str] = None
    rotation: Optional[int] = None
    ha: str = "left"
    va: str = "bottom"


@dataclass
class PlotDefinition:
    """
    Definition of a plot.

    groups may contain multiple solver groups. Each group is plotted
    independently and can have its own fitted line.
    """
    name: str
    groups: list[SolverGroup]


def regex_matches(pattern: str, solver_name: str) -> bool:
    """
    Match a solver name against a regex.

    '*' is accepted as shorthand for '.*', making patterns such as
    '*_dist' convenient.
    """
    pattern = pattern.replace("*", ".*")

    try:
        return re.fullmatch(pattern, solver_name) is not None
    except re.error as exc:
        raise ValueError(
            f"Invalid solver regex {pattern!r}: {exc}"
        ) from exc


def select_stats(stats, pattern: str):
    """Return statistics whose solver name matches pattern."""
    return [
        stat
        for stat in stats
        if regex_matches(pattern, stat.solver_name)
    ]


# ===========================================================================
# Fits
# ===========================================================================

def linear_fit(x, a, b):
    return a * x + b


def inverse_fit(x, a, b, c):
    return a / (x + c) + b

def log_fit(x, a, b, c):
    return a * np.log(x + c) + b

def m_log_fit(x, a, b, c):
    return a * np.log(c - x) + b

FIT_FUNCTIONS = {
    "linear": linear_fit,
    "inverse": inverse_fit,
    "log": log_fit,
    "mlog": m_log_fit,
}


def draw_fit(
    xs,
    ys,
    fit_name,
    *,
    label_prefix="",
    xlim=None,
):
    """
    Draw a fitted line.

    Returns the matplotlib line label, or None if no fit was requested.
    """
    if fit_name is None:
        return None

    if fit_name not in FIT_FUNCTIONS:
        raise ValueError(
            f"Unknown fit {fit_name!r}. "
            f"Available fits: {', '.join(FIT_FUNCTIONS)}"
        )

    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)

    mask = np.isfinite(xs) & np.isfinite(ys)

    if fit_name == "inverse" or fit_name == "log":
        mask &= xs > 0

    xs = xs[mask]
    ys = ys[mask]

    if len(xs) < 2:
        return None

    fit_function = FIT_FUNCTIONS[fit_name]

    try:
        if fit_name =="log" or fit_name=="inverse" or fit_name=="mlog" :
            params, _ = curve_fit(fit_function, xs, ys, 
                bounds=(
                [-np.inf, -np.inf, 0 + 1e-9],
                [ np.inf,  np.inf,  np.inf]
                    ),)
        else:
            params, _ = curve_fit(fit_function, xs, ys)

    except (RuntimeError, ValueError):
        return None

    if xlim is not None:
        x_min, x_max = xlim
    else:
        x_min = np.min(xs)
        x_max = np.max(xs)

    if fit_name == "inverse":
        x_min = max(x_min, 0.01)

    if x_max <= x_min:
        return None

    x_fit = np.linspace(x_min, x_max, 500)
    y_fit = fit_function(x_fit, *params)

    plt.plot(
        x_fit,
        y_fit,
        linestyle="--",
    )


# ===========================================================================
# General helpers
# ===========================================================================

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

    match = re.fullmatch(r"_v(\d+\.?\d*)%", suffix)
    if match:
        return (2, float(match.group(1)))

    if suffix.startswith("+"):
        match = re.search(r"_v(\d+)%", suffix)
        if match:
            return (3, int(match.group(1)))
        return (3, 0)

    return (4, suffix)


def get_stats(results):
    return sorted(
        st.getStats(results),
        key=cadical_sort_key,
    )


def save_plot(output_dir, filename):
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.tight_layout()
    plt.savefig(output_dir / filename)
    plt.close()


def annotate_point(stat, x, y, angle=0, ha="left", va="bottom"):
    offset_y = 5 if "-" in stat.solver_name else 2

    plt.annotate(
        stat.solver_name,
        (x, y),
        xytext=(4, offset_y),
        textcoords="offset points",
        fontsize=8,
        rotation=angle,
        ha=ha,
        va=va,
        rotation_mode="anchor"
    )


def setup_plot(title, xlabel, ylabel):
    plt.figure(figsize=(8, 6))
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)


# ===========================================================================
# Generic scatter plot
# ===========================================================================

def plot_scatter(
    stats,
    output_dir,
    *,
    x,
    y,
    title,
    xlabel,
    ylabel,
    output,
    groups=None,
    skip=None,
    yscale=None,
    xlim=None,
    ylim=None,
    annotate=True,
    legend=True,
):
    """
    Create a scatter plot.

    Every SolverGroup gets its own set of points and optional fit.
    """

    setup_plot(title, xlabel, ylabel)

    any_points = False
    all_xs = []
    all_ys = []

    if not groups:
        groups = [
            SolverGroup (
                name="all",
                pattern="*"
            )
        ]

    for group in groups:
        group_stats = select_stats(stats, group.pattern)

        xs = []
        ys = []

        for stat in group_stats:
            if skip is not None and skip(stat):
                continue

            x_value = x(stat)
            y_value = y(stat)

            if x_value is None or y_value is None:
                continue

            if not np.isfinite(x_value) or not np.isfinite(y_value):
                continue

            xs.append(x_value)
            ys.append(y_value)

            any_points = True

            plt.scatter(
                x_value,
                y_value,
                label=stat.solver_name,
            )

            if annotate:
                if group.rotation: 
                    annotate_point(stat, x_value, y_value, angle=group.rotation, ha=group.ha, va=group.va)
                else:
                    annotate_point(stat, x_value, y_value, ha=group.ha, va=group.va)

        if not xs:
            continue

        all_xs.extend(xs)
        all_ys.extend(ys)

        draw_fit(
            xs,
            ys,
            group.fit,
        )

    if not any_points:
        plt.close()
        return

    if xlim is not None:
        plt.xlim(*xlim)
    else:
        if all_xs:
            x_min = min(all_xs)
            x_max = max(all_xs)

            if x_min == x_max:
                x_min -= 1
                x_max += 1

            plt.xlim(x_min * 0.9, x_max * 1.2)

    if ylim is not None:
        plt.ylim(*ylim)
    else:
        if all_ys:
            y_min = min(all_ys)
            y_max = max(all_ys)

            if y_min == y_max:
                y_min -= 1
                y_max += 1

            plt.ylim(y_min * 0.8, y_max * 1.3)

    if yscale is not None:
        plt.yscale(yscale)

    plt.grid(alpha=0.3)
    if legend:
        plt.legend()

    save_plot(output_dir, output)


# ===========================================================================
# Generic step plot
# ===========================================================================
def plot_steps(
    stats,
    output_dir,
    *,
    x,
    y,
    title,
    xlabel,
    ylabel,
    output,
    groups=None,
    average_solvers=None,
    yscale=None,
    xlim=None,
    ylim=None,
    drawstyle="steps-post",
    unique_styles=False,
):
    """
    Create a step plot.

    Each solver group is plotted separately.

    Parameters
    ----------
    groups : iterable, optional
        Solver groups to plot. Each group is expected to have a
        ``pattern`` attribute.

    average_solvers : iterable of tuple[str, str], optional
        Pairs of solver names whose values should be averaged and
        plotted as an additional curve.

        Example:
            average_solvers=[
                ("solver_a", "solver_b"),
                ("solver_c", "solver_d"),
            ]

        The two solvers in each pair must have matching x-values.
    """

    setup_plot(title, xlabel, ylabel)

    plotted = False

    # Select the statistics to plot.
    if groups:
        g_stats = []
        for group in groups:
            g_stats.extend(select_stats(stats, group.pattern))
    else:
        g_stats = select_stats(stats, "*")

    markers = ["o", "s", "^", "D", "v", "<", ">", "P", "X", "*", "h", "p"]
    linestyles = ["-", "--", "-.", ":"]

    for i, stat in enumerate(g_stats):
        x_values = x(stat)
        y_values = y(stat)

        if len(x_values) == 0 or len(y_values) == 0:
            continue

        style = {}
        if unique_styles:
            marker = markers[i % len(markers)]
            linestyle = linestyles[
                (i // len(markers)) % len(linestyles)
            ]
            style.update(
                marker=marker,
                linestyle=linestyle,
                markersize=4,
                markevery=max(1, len(x_values) // 20),
            )

        plt.plot(
            x_values,
            y_values,
            label=stat.solver_name,
            drawstyle=drawstyle,
            linewidth=1,
            **style,
        )

        plotted = True

    # Plot averages of solver pairs.
    if average_solvers:
        stats_by_solver = {
            stat.solver_name: stat
            for stat in g_stats
        }

        for solver_a, solver_b in average_solvers:
            stat_a = stats_by_solver.get(solver_a)
            stat_b = stats_by_solver.get(solver_b)

            if stat_a is None or stat_b is None:
                continue

            x_a = x(stat_a)
            y_a = y(stat_a)
            x_b = x(stat_b)
            y_b = y(stat_b)

            if len(x_a) == 0 or len(x_b) == 0:
                continue

            if x_a != x_b:
                raise ValueError(
                    f"Cannot average {solver_a} and {solver_b}: "
                    "their x-values do not match."
                )

            if len(y_a) != len(y_b):
                raise ValueError(
                    f"Cannot average {solver_a} and {solver_b}: "
                    "their y-values have different lengths."
                )

            y_avg = [
                (value_a + value_b) / 2
                for value_a, value_b in zip(y_a, y_b)
            ]

            plt.plot(
                x_a,
                y_avg,
                label=f"{solver_a} + {solver_b} (avg)",
                drawstyle=drawstyle,
                linewidth=1,
                linestyle="--",
            )

            plotted = True

    if not plotted:
        plt.close()
        return

    if xlim is not None:
        plt.xlim(*xlim)

    if ylim is not None:
        plt.ylim(*ylim)

    if yscale is not None:
        plt.yscale(yscale)

    plt.grid(alpha=0.3)
    plt.legend()

    save_plot(output_dir, output)

# ===========================================================================
# Specific data functions
# ===========================================================================

def vivify_percentage(stat):
    return stat.percent.avg.vivify_time.avg.solve_time


def scheduled(stat):
    return stat.avg.vivify_sched

def scheduled_per_vivify_second(stat):
    if stat.percent.avg.vivify_time.avg.busy_time <= 0:
        return 0

    return (
        stat.avg.vivify_sched
        / stat.percent.avg.vivify_time.avg.busy_time
    )

def vivified(stat):
    return stat.avg.vivified

def vivified_per_vivify_second(stat):
    if stat.avg.vivify_time <= 0:
        return 0

    return stat.avg.vivified / stat.avg.vivify_time


def strengthened_per_vivify_second(stat):
    if stat.avg.vivify_time <= 0:
        return 0

    return 100 * stat.avg.vivify_strs / stat.avg.vivify_time


def subsumed_per_vivify_second(stat):
    if stat.avg.vivify_time <= 0:
        return 0

    return 100 * stat.avg.vivify_subs / stat.avg.vivify_time


def normalized_subsumed(stat):
    x = vivify_percentage(stat)

    if x <= 0:
        return 0

    return stat.avg.subsumed / (1 - x / 100)


def instance_solve_times(stat):
    return np.array([
        x.busy_time
        for x in stat.instance_stats
        if x.result != st.RESULT.UNKOWN
    ])


# ===========================================================================
# Solver groups
# ===========================================================================

# ---------------------------------------------------------------------------
# These are the important configuration knobs.
#
# '*' is accepted as shorthand for '.*'.
#
# For example:
#
#     "*_dist"
#
# matches:
#
#     2024_CaDiCaL_dist_v1%
#     2024_CaDiCaL_dist_v2%
#     2025_CaDiCaL_dist_v10%
#
# ---------------------------------------------------------------------------
#
# BASE_SOLVERS = SolverGroup(
#     name="CaDiCaL",
#     pattern=r"yyyy_CaDiCaL_v\d+%",
# )
#
# DIST_SOLVERS = SolverGroup(
#     name="CaDiCaL-dist",
#     pattern=r"yyyy_CaDiCaL_dist_v\d+%",
# )


# If the year is actually variable, e.g. 2024, 2025, ...
# use this instead:

BASE_SOLVERS = SolverGroup(
    name="CaDiCaL",
    pattern=r"\d{4}_CaDiCaL",
)

DIST_SOLVERS = SolverGroup(
    name="CaDiCaL-dist",
    pattern=r"\d{4}_CaDiCaL_dist",
)

DEDICATED_SOLVERS = SolverGroup(
    name="CaDiCaL",
    pattern=r"\d{4}_CaDiCaL_v\d+%",
)

DEDICATED_DIST_SOLVERS = SolverGroup(
    name="CaDiCaL-dist",
    pattern=r"\d{4}_CaDiCaL_dist_v\d+%",
)

DEDICATED_DIST_SUBSUME_SOLVERS = SolverGroup(
    name="CaDiCaL-dist",
    pattern=r"\d{4}_CaDiCaL_dist_v\d+%",
)


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()

    stats = get_stats(args.results)

    # =======================================================================
    # Configure the solvers for each plot here.
    #
    # A plot may have one or multiple groups.
    #
    # Examples:
    #
    # groups=[
    #     SolverGroup("normal", r"*CaDiCaL_v\d+%", fit="linear"),
    #     SolverGroup("dist", r"*CaDiCaL_dist_v\d+%", fit="inverse"),
    # ]
    #
    # =======================================================================

    # -----------------------------------------------------------------------
    # CDF
    # -----------------------------------------------------------------------

    groups=[
            SolverGroup (
                name="dedicated",
                pattern=r"\d{4}_CaDiCaL_v\d+\%",
                fit="linear",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"pdCad_*",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"pdCad-L_*",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="cadical",
                pattern=r"Cad",
                va="top",
            ),
            SolverGroup (
                name="partitioned",
                pattern="pCad*",
                va="top",
            ),        
        ]

    def valid_solve_times(stat):
        times = instance_solve_times(stat)
        return times[times > 0]

    def cdf_x(stat):
        return np.sort(valid_solve_times(stat))

    def cdf_y(stat):
        times = valid_solve_times(stat)
        return np.arange(1, len(times) + 1)

    plot_steps(
        stats,
        args.out_dir,
        x=cdf_x,
        y=cdf_y,
        title="cumulative solved instances over time",
        xlabel="solve time (seconds)",
        ylabel="number of instances solved (time <= x)",
        output="cdf.svg",
        unique_styles=True,
        groups=groups
    )

    plot_steps(
        stats,
        args.out_dir,
        x=cdf_x,
        y=cdf_y,
        title="cumulative solved instances over time",
        xlabel="solve time (seconds)",
        ylabel="number of instances solved (time <= x)",
        ylim=[200],
        output="cdf_zoom_y200.svg",
        unique_styles=True,
        groups=groups
    )

    # -----------------------------------------------------------------------
    # SAT CDF
    # -----------------------------------------------------------------------

    def valid_sat_solve_times(stat):
        times = np.array([
            x.busy_time
            for x in stat.instance_stats
            if x.result == st.RESULT.SAT
        ])
        return times[times > 0]

    def cdf_x_sat(stat):
        return np.sort(valid_sat_solve_times(stat))

    def cdf_y_sat(stat):
        times = valid_sat_solve_times(stat)
        return np.arange(1, len(times) + 1)

    plot_steps(
        stats,
        args.out_dir,
        x=cdf_x_sat,
        y=cdf_y_sat,
        title="cumulative solved sat instances over time",
        xlabel="solve time (seconds)",
        ylabel="number of instances solved (time <= x)",
        output="cdf_sat.svg",
        unique_styles=True,
    )

    plot_steps(
        stats,
        args.out_dir,
        x=cdf_x_sat,
        y=cdf_y_sat,
        title="cumulative solved sat instances over time",
        xlabel="solve time (seconds)",
        ylabel="number of instances solved (time <= x)",
        ylim=[100],
        output="cdf_sat_zoom_y100.svg",
        unique_styles=True,
    )

    # -----------------------------------------------------------------------
    # UNSAT CDF
    # -----------------------------------------------------------------------

    def valid_unsat_solve_times(stat):
        times = np.array([
            x.busy_time
            for x in stat.instance_stats
            if x.result == st.RESULT.UNSAT
        ])
        return times[times > 0]

    def cdf_x_unsat(stat):
        return np.sort(valid_unsat_solve_times(stat))

    def cdf_y_unsat(stat):
        times = valid_unsat_solve_times(stat)
        return np.arange(1, len(times) + 1)

    plot_steps(
        stats,
        args.out_dir,
        x=cdf_x_unsat,
        y=cdf_y_unsat,
        title="cumulative solved unsat instances over time",
        xlabel="solve time (seconds)",
        ylabel="number of instances solved (time <= x)",
        output="cdf_unsat.svg",
        unique_styles=True,
    )

    plot_steps(
        stats,
        args.out_dir,
        x=cdf_x_unsat,
        y=cdf_y_unsat,
        title="cumulative solved unsat instances over time",
        xlabel="solve time (seconds)",
        ylabel="number of instances solved (time <= x)",
        ylim=[100],
        output="cdf_unsat_zoom_y100.svg",
        unique_styles=True,
    )

    # -----------------------------------------------------------------------
    # Scheduled clauses over busy time
    # -----------------------------------------------------------------------

    def scheduled_x(stat):
        return np.sort(np.array([
            x.busy_time
            for x in stat.instance_stats
            if x.result != st.RESULT.UNKOWN
        ]))

    def scheduled_y(stat):
        return np.sort(np.array([
            x.vivify_sched
            for x in stat.instance_stats
            if x.result != st.RESULT.UNKOWN
        ]))

    plot_steps(
        stats,
        args.out_dir,
        x=scheduled_x,
        y=scheduled_y,
        title="Scheduled clauses per solve time",
        xlabel="solve time (seconds)",
        ylabel="number of scheduled clauses",
        output="sched_over_busy_time.svg",
        drawstyle="default",
    )

    # -----------------------------------------------------------------------
    # Subsumed clauses over busy time
    # -----------------------------------------------------------------------

    def subs_y(stat):
        return np.sort(np.array([
            x.vivify_subs
            for x in stat.instance_stats
            if x.result != st.RESULT.UNKOWN
        ]))

    plot_steps(
        stats,
        args.out_dir,
        x=scheduled_x,
        y=subs_y,
        title="subsumed clauses per solve time",
        xlabel="solve time (seconds)",
        ylabel="number of subsumed clauses",
        output="subs_over_busy_time.svg",
        drawstyle="default",
    )

    # -----------------------------------------------------------------------
    # Strengthened clauses over busy time
    # -----------------------------------------------------------------------

    def strs_y(stat):
        return np.sort(np.array([
            x.vivify_strs
            for x in stat.instance_stats
            if x.result != st.RESULT.UNKOWN
        ]))

    plot_steps(
        stats,
        args.out_dir,
        x=scheduled_x,
        y=strs_y,
        title="strengthened clauses per solve time",
        xlabel="solve time (seconds)",
        ylabel="number of strengthened clauses",
        output="strs_over_busy_time.svg",
        drawstyle="default",
    )

    # =======================================================================
    # Scatter plots
    # =======================================================================

    # -----------------------------------------------------------------------
    # Scheduled clauses per vivify second
    #
    # Here we compare:
    #
    #   yyyy_CaDiCaL_vN%
    #   yyyy_CaDiCaL_dist_vN%
    #
    # and fit each group independently.
    # -----------------------------------------------------------------------

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=scheduled_per_vivify_second,
        title="scheduled clauses",
        xlabel="vivify time %",
        ylabel="scheduled clauses per vivify sec",
        output="sched_per_vivi_sec.svg",
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=vivified_per_vivify_second,
        title="vivified clauses",
        xlabel="vivify time %",
        ylabel="vivified clauses per vivify sec",
        output="vivified_per_vivi_sec.svg",
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_strs,
        title="strengthened clauses",
        xlabel="vivify time %",
        ylabel="strengthened clauses",
        output="strs_per_vivi_sec.svg",
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=strengthened_per_vivify_second,
        title="strengthened clauses per sec",
        xlabel="vivify time %",
        ylabel="strengthened per second in vivification",
        output="strs_per_vivi_sec.svg",
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=subsumed_per_vivify_second,
        title="subsumed clauses from vivification",
        xlabel="vivify time %",
        ylabel="subsumed clauses from vivification",
        output="subs_per_vivi_sec.svg",
    )

    #
    # dedicated distributed variant
    #

    groups=[
            SolverGroup (
                name="dedicated",
                pattern=r"\d{4}_CaDiCaL_v\d+\%",
                fit="linear",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"pdCad_*",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"pdCad-L_*",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="cadical",
                pattern=r"Cad",
                va="top",
            ),
            SolverGroup (
                name="partitioned",
                pattern="pCad*",
                va="top",
            ),        
        ]

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=scheduled,
        title="",
        xlabel="vivify time %",
        ylabel="scheduled clauses",
        output="all_sched.svg",
        legend=False,
        ylim=[0],
        xlim=[0,13],
        groups=groups
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_checked,
        title="",
        xlabel="vivify time %",
        ylabel="checked clauses",
        output="all_checked.svg",
        legend=False,
        ylim=[0],
        xlim=[0, 13],
        groups=groups   
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=vivified,
        title="",
        xlabel="vivify time %",
        ylabel="vivified clauses",
        output="all_vivified.svg",
        legend=False,
        ylim=[0],
        xlim=[0,13],
        groups=groups
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_strs,
        title="",
        xlabel="vivify time %",
        ylabel="strengthened clauses",
        output="all_strs.svg",
        legend=False,
        ylim=[0],
        xlim=[0, 13],
        groups=groups
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_rat,
        title="",
        xlabel="vivify time %",
        ylabel="by vivification subsumed clauses",
        output="all_rat.svg",
        legend=False,
        ylim=[0],
        xlim=[0,13],
        groups=groups
    )

    ### effektiveness

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda x : x.avg.vivified / x.avg.vivify_checked,
        title="",
        xlabel="vivify time %",
        ylabel="strengthened per second in vivification",
        output="all_eff_vivify.svg",
        legend=False,
        xlim=[0, 13],
        groups=groups
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda x : x.avg.vivify_strs / x.avg.vivify_checked,
        title="",
        xlabel="vivify time %",
        ylabel="strengthened per second in vivification",
        output="all_eff_strs.svg",
        legend=False,
        xlim=[0, 13],
        groups=groups
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda x : x.avg.vivify_rat / x.avg.vivify_checked,
        title="",
        xlabel="vivify time %",
        ylabel="strengthened per second in vivification",
        output="all_eff_rat.svg",
        legend=False,
        xlim=[0, 13],
        groups=groups
    )

    #
    # dedicated distributed subsume variant
    #

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=scheduled,
        title="",
        xlabel="vivify time %",
        ylabel="scheduled clauses",
        output="dedicated_dist_subs_sched.svg",
        legend=False,
        ylim=[0],
        xlim=[0,13],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL_dist_vs\d+\%",
                fit="inverse",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="linear",
                rotation=-25,
                va="top",
            ),
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_checked,
        title="",
        xlabel="vivify time %",
        ylabel="checked clauses",
        output="dedicated_dist_subs_checked.svg",
        legend=False,
        xlim=[0, 13],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL_dist_vs\d+\%",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="log",
                va="top",
            ),
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=vivified,
        title="",
        xlabel="vivify time %",
        ylabel="vivified clauses",
        output="dedicated_dist_subs_vivified.svg",
        legend=False,
        ylim=[0],
        xlim=[0,13],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL_dist_vs\d+\%",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="log",
                va="top",
            ),
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_strs,
        title="",
        xlabel="vivify time %",
        ylabel="strengthened clauses",
        output="dedicated_dist_subs_strs.svg",
        legend=False,
        xlim=[0, 13],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL_dist_vs\d+\%",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="log",
                va="top",
            ),
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_subs,
        title="",
        xlabel="vivify time %",
        ylabel="by vivification subsumed clauses",
        output="dedicated_dist_subs_subs.svg",
        legend=False,
        ylim=[0],
        xlim=[0,13],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL_dist_vs\d+\%",
                fit="inverse",
                va="top"
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="inverse",
            ),
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=strengthened_per_vivify_second,
        title="",
        xlabel="vivify time %",
        ylabel="strengthened per second in vivification",
        output="dedicated_dist_subs_strs_per_vivi_sec.svg",
        legend=False,
        xlim=[0, 13],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL_dist_vs\d+\%",
                fit="inverse",
                va="top"
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="inverse"
            ),
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=subsumed_per_vivify_second,
        title="",
        xlabel="vivify time %",
        ylabel="by vivification subsumed clauses per second in vivification",
        output="dedicated_dist_subs_subs_per_vivi_sec.svg",
        legend=False,
        xlim=[0,13],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL_dist_vs\d+\%",
                fit="inverse",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="inverse"
            ),
        ]
    )

    #
    # dedicated distributed variant + normal
    #

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=scheduled,
        title="",
        xlabel="vivify time %",
        ylabel="scheduled clauses",
        output="normal_dedicated_dist_sched.svg",
        legend=False,
        ylim=[0],
        xlim=[0],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL\+_dist_v\d+\%",
                fit="inverse",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="linear",
                rotation=-25,
                va="top",
            ),
            BASE_SOLVERS
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_checked,
        title="",
        xlabel="vivify time %",
        ylabel="checked clauses",
        output="normal_dedicated_dist_checked.svg",
        legend=False,
        xlim=[0],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL\+_dist_v\d+\%",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="log",
                va="top",
            ),
            BASE_SOLVERS
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=vivified,
        title="",
        xlabel="vivify time %",
        ylabel="vivified clauses",
        output="normal_dedicated_dist_vivified.svg",
        legend=False,
        ylim=[0],
        xlim=[0],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL\+_dist_v\d+\%",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="log",
                va="top",
            ),
            BASE_SOLVERS
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_strs,
        title="",
        xlabel="vivify time %",
        ylabel="strengthened clauses",
        output="normal_dedicated_dist_strs.svg",
        legend=False,
        xlim=[0],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL\+_dist_v\d+\%",
                fit="log",
                va="top",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="log",
                va="top",
            ),
            BASE_SOLVERS
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=lambda s: s.avg.vivify_subs,
        title="",
        xlabel="vivify time %",
        ylabel="by vivification subsumed clauses",
        output="normal_dedicated_dist_subs.svg",
        legend=False,
        ylim=[0],
        xlim=[0],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL\+_dist_v\d+\%",
                fit="inverse",
                va="top"
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="inverse",
            ),
            BASE_SOLVERS
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=strengthened_per_vivify_second,
        title="",
        xlabel="vivify time %",
        ylabel="strengthened per second in vivification",
        output="normal_dedicated_dist_strs_per_vivi_sec.svg",
        legend=False,
        xlim=[0],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL\+_dist_v\d+\%",
                fit="inverse",
                va="top"
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="inverse"
            ),
            BASE_SOLVERS
        ]
    )

    plot_scatter(
        stats,
        args.out_dir,
        x=vivify_percentage,
        y=subsumed_per_vivify_second,
        title="",
        xlabel="vivify time %",
        ylabel="by vivification subsumed clauses per second in vivification",
        output="normal_dedicated_dist_subs_per_vivi_sec.svg",
        legend=False,
        xlim=[0],
        groups=[
            SolverGroup (
                name="dedicated distributed subsume",
                pattern=r"\d{4}_CaDiCaL\+_dist_vs\d+\%",
                fit="inverse",
            ),
            SolverGroup (
                name="dedicated distributed",
                pattern=r"\d{4}_CaDiCaL_dist_v\d+\%",
                fit="inverse"
            ),
            BASE_SOLVERS
        ]
    )


if __name__ == "__main__":
    main()
