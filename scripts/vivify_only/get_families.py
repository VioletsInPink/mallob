import sqlite3
from pathlib import Path
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt

from statistics_extractor import getStats


DB = Path("~/Downloads/meta.db").expanduser()
URI_FILE = Path("~/Downloads/track_main_2024.uri").expanduser()
RESULTS_DIR = Path("results")


def get_hashes():
    """Read hashes from the URI file."""
    hashes = []

    with open(URI_FILE) as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            hashes.append(line.rstrip("/").split("/")[-1])

    return hashes


def get_families(hashes):
    """Map hash -> family using meta.db."""
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    result = {}

    for h in hashes:
        cursor.execute(
            "SELECT family FROM features WHERE hash = ?",
            (h,)
        )

        row = cursor.fetchone()

        if row is None:
            print(f"WARNING: hash not found: {h}")
            result[h] = "UNKNOWN"
        else:
            result[h] = row[0]

    conn.close()

    return result


def main():

    # ---------------------------------------------------------
    # Load solver statistics
    # ---------------------------------------------------------

    stats = getStats(RESULTS_DIR)

    # ---------------------------------------------------------
    # Load URI hashes and families
    # ---------------------------------------------------------

    hashes = get_hashes()
    hash_to_family = get_families(hashes)

    # One family for each instance
    instance_families = [
        hash_to_family[h]
        for h in hashes
    ]

    # ---------------------------------------------------------
    # Calculate solve time per solver/family
    # ---------------------------------------------------------

    solver_family_times = {}

    for solver in stats:

        family_times = defaultdict(list)

        for i, instance in enumerate(solver.instance_stats):

            if i >= len(instance_families):
                print(
                    f"WARNING: solver {solver.solver_name} "
                    f"has fewer instances than URI file"
                )
                break

            family = instance_families[i]

            family_times[family].append(
                (instance.vivified / instance.vivify_time if instance.vivify_time > 0 else 0) / instance.num_active_threads
            )

        solver_family_times[solver.solver_name] = family_times

    # ---------------------------------------------------------
    # Create matrix
    # ---------------------------------------------------------

    solvers = [
        solver.solver_name
        for solver in stats
    ]

    # Anzahl Instanzen pro Familie
    family_counts = defaultdict(int)

    for family in instance_families:
        family_counts[family] += 1

    # Familien nach Anzahl der Instanzen absteigend sortieren
    families = sorted(
        family_counts,
        key=lambda family: family_counts[family],
        reverse=True
    )

    matrix = np.full(
        (len(solvers), len(families)),
        np.nan
    )

    for i, solver in enumerate(solvers):

        for j, family in enumerate(families):

            values = solver_family_times[solver].get(
                family,
                []
            )

            if len(values) == 1:
                values = []

            if values:
                matrix[i, j] = np.mean(values)

    # ---------------------------------------------------------
    # Print matrix
    # ---------------------------------------------------------

    print("\nMean solve time per family:\n")

    print(
        f"{'Solver':<20}",
        *[f"{f:<15}" for f in families]
    )

    for i, solver in enumerate(solvers):

        values = []

        for j in range(len(families)):

            value = matrix[i, j]

            if np.isnan(value):
                values.append(f"{'N/A':<15}")
            else:
                values.append(f"{value:<15.2f}")

        print(
            f"{solver:<20}",
            *values
        )

    # ---------------------------------------------------------
    # Plot heatmap
    # ---------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(
            max(10, len(families) * 0.8),
            max(4, len(solvers) * 0.6)
        )
    )

    image = ax.imshow(
        matrix,
        aspect="auto"
    )

    ax.set_xticks(range(len(families)))

    # Family + Anzahl Instanzen
    family_labels = [
        f"{family} (n={family_counts[family]})"
        for family in families
    ]

    ax.set_xticklabels(
        family_labels,
        rotation=90
    )

    ax.set_yticks(range(len(solvers)))
    ax.set_yticklabels(solvers)

    ax.set_xlabel("Problem family")
    ax.set_ylabel("Solver")

    ax.set_title(
        "Mean solve time by solver and problem family"
    )

    fig.colorbar(
        image,
        ax=ax,
        label="mean solve time [s]"
    )

    plt.tight_layout()
    plt.subplots_adjust(left=0.25)

    plt.savefig(
        "solve_time_by_family.png",
        dpi=300
    )

    plt.show()


if __name__ == "__main__":
    main()
