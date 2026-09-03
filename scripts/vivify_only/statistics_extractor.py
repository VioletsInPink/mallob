#!/usr/bin/env python3

# This script extracts relevant stats from a given results directory
# All extracted stats are an average over the amount of solver threads used by that instance

from enum import Enum
import numpy as np
import argparse
import re
from pathlib import Path
from dataclasses import dataclass, field, fields, is_dataclass
from tqdm import tqdm
import pickle

def plotable(prop):
    prop.fget.plotable = True
    return prop

@classmethod
def get_plotable(cls):
    result = []

    # Dataclass fields
    if is_dataclass(cls):
        for f in fields(cls):
            if f.metadata.get("plotable", False):
                result.append(f.name)

    # Plotable properties/functions
    for name, attr in vars(cls).items():
        if isinstance(attr, property) and getattr(attr.fget, "plotable", False):
            result.append(name)

    return result

class RESULT(Enum):
    UNKOWN = 1
    SAT = 2
    UNSAT = 3

@dataclass
class InstanceStats:
    busy_time: float = field(default=0, metadata={"plotable": True})
    result: RESULT = field(default=RESULT.UNKOWN, metadata={"plotable": False})
    num_active_threads: int = field(default=0, metadata={"plotable": True})
    num_active_threads_per_proc: int = field(default=0, metadata={"plotable": True})

    subsumed: float = field(default=0, metadata={"plotable": True})
    subsume_time: float = field(default=0, metadata={"plotable": True})

    vivified: float = field(default=0, metadata={"plotable": True})
    vivify_strs: float = field(default=0, metadata={"plotable": True})
    vivify_subs: float = field(default=0, metadata={"plotable": True})
    vivify_checked: float = field(default=0, metadata={"plotable": True})
    vivify_sched: float = field(default=0, metadata={"plotable": True})
    vivify_time_per_thread: float = field(default=0, metadata={"plotable": True})
    vivify_time: float = field(default=0, metadata={"plotable": True})
    solve_time_per_thread: float = field(default=0, metadata={"plotable": True})
    solve_time: float = field(default=0, metadata={"plotable": True})

    prod: float = field(default=0, metadata={"plotable": True})
    prod_adm: float = field(default=0, metadata={"plotable": True})
    prod_drp: float = field(default=0, metadata={"plotable": True})
    prod_flt: float = field(default=0, metadata={"plotable": True})

    vivi_prod: float = field(default=0, metadata={"plotable": True})
    vivi_prod_adm: float = field(default=0, metadata={"plotable": True})
    vivi_prod_drp: float = field(default=0, metadata={"plotable": True})
    vivi_prod_flt: float = field(default=0, metadata={"plotable": True})

    @plotable
    @property
    def vivified_percent(self):
        return self.vivified / self.vivify_checked if self.vivify_checked > 0 else 0

    @plotable
    @property
    def vivify_strs_percent(self):
        return self.vivify_strs / self.vivify_checked if self.vivify_checked > 0 else 0

    @plotable
    @property
    def vivify_subs_percent(self):
        info("uses sched not checked as base")
        return 100* self.vivify_subs / self.vivify_sched if self.vivify_checked > 0 else 0

    @plotable
    @property
    def percent(self):
        class PercentRoot:
            def __init__(self, obj):
                self.obj = obj

            def __getattr__(self, numerator):
                return NumeratorProxy(self.obj, numerator)

        class NumeratorProxy:
            def __init__(self, obj,  numerator):
                self.obj = obj
                self.numerator = numerator
            def __getattr__(self, denominator_s):
                numerator = getattr(self.obj, self.numerator)
                denominator = getattr(self.obj, denominator_s)
                return numerator / denominator * 100 if denominator else 0
        return PercentRoot(self)

    plotable = get_plotable

@dataclass
class Stats:
    solver_name: str = field(metadata={"plotable": False})
    num_instances: int = field(default=0, metadata={"plotable": True})
    solved: int = field(default=0, metadata={"plotable": True})
    sat: int = field(default=0, metadata={"plotable": True})
    unsat: int = field(default=0, metadata={"plotable": True})
    par2: float = field(default=0, metadata={"plotable": True})
 
    @plotable
    @property
    def avg(self):
        class InstanceAverage:
            def __init__(self, instances):
                self.instances = instances

            def __getattr__(self, name):
                if not self.instances:
                    raise AttributeError("No instance stats available")

                if not hasattr(self.instances[0], name):
                    raise AttributeError(
                        f"{type(self.instances[0]).__name__} has no field '{name}'"
                    )

                values = [
                    getattr(x, name)
                    for x in self.instances
                    if hasattr(x, name)
                ]
                return sum(values) / len(values) if values else 0

        return InstanceAverage(self.instance_stats)

    @plotable
    @property
    def percent(self):
        class PercentRoot:
            def __init__(self, obj):
                self.obj = obj

            def __getattr__(self, numerator_source):
                return SourceProxy(self.obj, numerator_source)

        class SourceProxy:
            def __init__(self, obj, numerator_source):
                self.obj = obj
                self.numerator_source = numerator_source

            def __getattr__(self, numerator_field):
                return NumeratorProxy(
                    self.obj,
                    self.numerator_source,
                    numerator_field,
                )

        class NumeratorProxy:
            def __init__(self, obj, numerator_source, numerator_field):
                self.obj = obj
                self.numerator_source = numerator_source
                self.numerator_field = numerator_field

            def __getattr__(self, denominator_source):
                return DenominatorProxy(
                    self.obj,
                    self.numerator_source,
                    self.numerator_field,
                    denominator_source,
                )

        class DenominatorProxy:
            def __init__(
                self,
                obj,
                numerator_source,
                numerator_field,
                denominator_source,
            ):
                self.obj = obj
                self.numerator_source = numerator_source
                self.numerator_field = numerator_field
                self.denominator_source = denominator_source

            def __getattr__(self, denominator_field):
                numerator = getattr(
                    getattr(self.obj, self.numerator_source),
                    self.numerator_field,
                )
                denominator = getattr(
                    getattr(self.obj, self.denominator_source),
                    denominator_field,
                )

                return numerator / denominator * 100 if denominator else 0

        return PercentRoot(self)

    instance_stats: list[InstanceStats] = field(default_factory=list)
    plotable = get_plotable

@dataclass
class Setup:
    num_threads: int
    nprocs: int
    threads_per_proc: int
    timeout: int
    vivify: bool

def warn(*msg):
    tqdm.write(f"\033[93mWARNING: {' '.join(map(str, msg))}\033[0m")

def info(*msg):
    tqdm.write(f"\033[94mInfo: {''.join(map(str, msg))}\033[0m")

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

def get_busy_time_and_result(instance_dir, setup: type[Setup], stats: InstanceStats):
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

def get_clause_sharing_statistics(instance_dir: Path, stats: InstanceStats):
    found_threads = 0

    pattern = re.compile(r"S(\d+)\.\d+\s+vivification only")
    vivify_threads = []
    # each process directory
    for proc_dir in instance_dir.iterdir():
        if not proc_dir.is_dir() or not proc_dir.name.isdigit():
            continue

        # get vivification threads
        job_file = list(proc_dir.glob("jobs.*"))
        if not job_file:
            return False

        for logfile in job_file:
            with open(logfile, "r", encoding="utf8") as f:
                for line in f:
                    m = pattern.search(line)
                    if m:
                        vivify_threads.append(int(m.group(1)))

        # subproc output files
        subproc_files = list(proc_dir.glob("subproc.*"))
        if not subproc_files:
            return False

        pattern_subproc = re.compile(r"END\s+S(\d+).*?prod:(\d+).*?flt:(\d+)\s+adm:(\d+)\s+drp:(\d+)")
        for logfile in subproc_files:
            with open(logfile) as f:
                for line in f:
                    m = pattern_subproc.search(line)
                    if m:
                        found_threads += 1
                        solver_id = int(m.group(1))
                        stats.prod += int(m.group(2))
                        stats.prod_flt += int(m.group(3))
                        stats.prod_adm += int(m.group(4))
                        stats.prod_drp += int(m.group(5))


                        if solver_id in vivify_threads:
                            stats.vivi_prod += int(m.group(2))
                            stats.vivi_prod_flt += int(m.group(3))
                            stats.vivi_prod_adm += int(m.group(4))
                            stats.vivi_prod_drp += int(m.group(5))

    if found_threads > 0:
        stats.prod /= found_threads
        stats.prod_adm /= found_threads
        stats.prod_drp /= found_threads
        stats.prod_flt /= found_threads

        stats.vivi_prod /= found_threads
        stats.vivi_prod_adm /= found_threads
        stats.vivi_prod_drp /= found_threads
        stats.vivi_prod_flt /= found_threads


    if found_threads != stats.num_active_threads:
        warn(f"found results for {found_threads}, expected {stats.num_active_threads} in {instance_dir.name}")

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
                        continue

                    m = re.search(
                        r"c \s+vivifystrs:\s+(\d+)",
                        line
                    )
                    if m:
                        stats.vivify_strs += int(m.group(1))
                        continue

                    m = re.search(
                        r"c \s+vivifysubs:\s+(\d+)",
                        line
                    )
                    if m:
                        stats.vivify_subs += int(m.group(1))
                        continue

                    m = re.search(
                        r"c \s+vivifychecks:\s+(\d+)",
                        line
                    )
                    if m:
                        stats.vivify_checked += int(m.group(1))
                        continue

                    m = re.search(
                        r"c \s+vivifysched:\s+(\d+)",
                        line
                    )
                    if m:
                        stats.vivify_sched += int(m.group(1))
                        continue

                    m = re.search(
                        r"c subsumed:\s+(\d+)",
                        line
                    )
                    if m:
                        stats.subsumed += int(m.group(1))
                        continue

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

                    # Example:
                    # 0.32    0.77% vivify
                    m = re.match(
                        r"\s*([0-9.]+)\s+[0-9.]+%\s+subsume",
                        line
                    )
                    if m:
                        stats.subsume_time += float(m.group(1))

    if found_threads > 0:
        # stats.subsumed /= found_threads
        # stats.vivified /= found_threads
        # stats.vivify_strs /= found_threads
        # stats.vivify_subs /= found_threads
        # stats.vivify_checked /= found_threads
        # stats.vivify_sched /= found_threads
        stats.vivify_time_per_thread /= found_threads
        stats.solve_time_per_thread /= found_threads

    if found_threads != stats.num_active_threads:
        warn(f"found results for {found_threads}, expected {stats.num_active_threads} in {instance_dir.name}")

    return True

def createStats(solver_name: str, instance_stats: list[InstanceStats], setup: type[Setup]):
    sat = 0
    unsat = 0
    par2 = 0

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

    par2 /= len(instance_stats)

    return Stats(solver_name, len(instance_stats), sat + unsat, sat, unsat, par2, instance_stats)

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

        # if not get_clause_sharing_statistics(instance_dir, stats):
        #     no_stats_found.append(instance_dir.name)

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

def getStats(results_dir):
    results_dir = Path(results_dir)
    cache_path = results_dir / "stats.pickle"

    if not results_dir.is_dir():
        print(f"ERROR: {results_dir} is not a directory")
        exit(1)

    # Load existing cache
    if cache_path.is_file():
        with open(cache_path, "rb") as cache:
            warn("using cached results")
            stats = pickle.load(cache)
    else:
        stats = []

    # Keep track of which portfolio directories are already cached
    cached_portfolios = [stat.solver_name for stat in stats]
    changed = False

    for portfolio_dir in sorted(results_dir.iterdir()):
        if not portfolio_dir.is_dir():
            continue

        # Skip non-portfolio directories
        if not (portfolio_dir / "setup.txt").exists():
            print(f"Skipping {portfolio_dir}: no setup.txt")
            continue

        if portfolio_dir.name in cached_portfolios:
            continue

        print(f"\n=== Processing {portfolio_dir.name} ===")

        stats.append(extract(portfolio_dir))
        changed = True

    # Rewrite cache only if new portfolios were found
    if changed:
        with open(cache_path, "wb") as cache:
            pickle.dump(stats, cache)

    return stats
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "results_dir",
        help="Directory containing the experiment results."
    )

    args = parser.parse_args()
    getStats(args.results_dir)

if __name__ == "__main__":
    main()
