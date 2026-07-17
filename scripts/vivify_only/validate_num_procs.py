#!/usr/bin/env python3

from pathlib import Path
import re
import sys


def read_setup(setup_file):
    setup = {}

    with open(setup_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            key, value = line.split(maxsplit=1)
            setup[key] = value

    return setup


def check_portfolio(portfolio_dir):
    setup_file = portfolio_dir / "setup.txt"

    if not setup_file.exists():
        print(f"ERROR {portfolio_dir}: missing setup.txt")
        return 1

    setup = read_setup(setup_file)

    threads_per_proc = int(setup["THREADS_PER_PROC"])
    num_procs = int(setup["MPI_PROCS"])
    num_threads = int(setup["TOTAL_THREADS"])

    errors = 0

    print(
        f"\nChecking portfolio {portfolio_dir.name} "
        f"{num_procs} procs x {threads_per_proc} threads = {num_threads} total"
    )

    # Each problem instance
    for problem_dir in portfolio_dir.iterdir():

        if not problem_dir.is_dir():
            continue

        # Each MPI process directory
        num_found_procs = 0;
        for proc_dir in problem_dir.iterdir():

            if not proc_dir.is_dir():
                continue;

            if not proc_dir.name.isdigit():
                print(
                    f"ERROR {portfolio_dir.name}/"
                    f"{problem_dir.name}/"
                    f"{proc_dir.name}: "
                    f"not a valid dir"
                )
                errors += 1
                continue

            proc = int(proc_dir.name)
            num_found_procs += 1

            # Read all files in process directory
            for logfile in proc_dir.iterdir():

                if not logfile.is_file():
                    continue

                try:
                    text = logfile.read_text(errors="ignore")
                except Exception:
                    continue

                for match in re.finditer(r"S(\d+)\.0", text):

                    sid = int(match.group(1))

                    first_sid = proc * threads_per_proc
                    last_sid = first_sid + threads_per_proc - 1

                    if sid < first_sid or sid > last_sid:
                        print(
                            f"ERROR {portfolio_dir.name}/"
                            f"{problem_dir.name}/"
                            f"{proc_dir.name}: "
                            f"found S{sid}, expected "
                            f"S{first_sid}-S{last_sid}"
                        )
                        errors += 1
        if num_found_procs != num_procs:
            print(
                f"ERROR {portfolio_dir.name}/"
                f"{problem_dir.name}/"
                f"{proc_dir.name}: "
                f"found {num_found_procs} proc dirs, expected {num_procs}"
            )
            errors += 1
    return errors


def check_results(results_dir):
    results_dir = Path(results_dir)

    errors = 0

    # Each portfolio directory
    for portfolio_dir in sorted(results_dir.iterdir()):

        if not portfolio_dir.is_dir():
            continue

        errors += check_portfolio(portfolio_dir)

    if errors:
        print(f"\nFAILED: {errors} errors found")
        return False

    print("\nOK: all portfolios passed")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} RESULTS_DIR")
        sys.exit(1)

    sys.exit(0 if check_results(sys.argv[1]) else 1)
