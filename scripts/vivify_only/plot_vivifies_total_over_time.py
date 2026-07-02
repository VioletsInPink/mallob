import glob
import re
import sys
from collections import defaultdict
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

matplotlib.use("Agg")

pattern_time = re.compile(r'\[(\d+\.\d+)\]')
pattern_data = re.compile(r'\((\d+)\)')
pattern_type = re.compile(r'vivify (checked|subsumed|strengthened|found)')
pattern_vivi = re.compile(r'\((c|v)\)')

def parse_file(fname, data, checked):

    with open(fname, "r") as f:
        for line in f:
            if "] vivify" not in line:
                continue

            t = pattern_time.search(line)
            if not t:
                print("No time:", line)
                continue
            t = float(t.group(1))
            

            d = pattern_data.search(line)
            if not d:
                print("No data:", line)
                continue
            d = int(d.group(1))
            if d == 0:
                continue


            k = pattern_type.search(line)
            if not k:
                print("No key:", line)
                continue
            k = k.group(1)

            if k == "found":
                k = "unit"


            v = pattern_vivi.search(line)
            if not v:
                print("No type:", line)
                continue
            v = v.group(1)

            # print(t, k, d)


            if k == "checked":
                if t in checked:
                    checked[t] += d
                else:
                    checked[t] = d
                continue

            if t in data[k]:
                data[v][k][t] += d
            else:
                data[v][k][t] = d

    return data


def merge_all(files):
    series = defaultdict(lambda: defaultdict(dict))
    checked = defaultdict(int)

    for f in files:
        parse_file(f, series, checked)

    return series, checked


def main():
    files = glob.glob(f"{sys.argv[1]}/**/cadical.out.#*.*", recursive=True)
    
    if not files:
        print("No cadical.out.#*.* files found")
        return

    series, checked = merge_all(files)

    if not series:
        print("did not vivify: skip")
        return

    # create a total count
    total_checked_sorted = sorted(checked.items())
    total_checked_times = [t for t, v in total_checked_sorted]
    total_checked_values = [v for t, v in total_checked_sorted]

    running_total = 0
    total_checked_values_accu = []
    for t, v in total_checked_sorted:
        running_total += v
        total_checked_values_accu.append(running_total)

    # create a total count
    total_vivi = Counter()
    for data in series["v"].values():
        total_vivi.update(data)

    total_vivi_sorted = sorted(total_vivi.items())
    total_vivi_times = [t for t, v in total_vivi_sorted]
    total_vivi_values = [v for t, v in total_vivi_sorted]

    running_total = 0
    total_vivi_values_accu = []
    for t, v in total_vivi_sorted:
        running_total += v
        total_vivi_values_accu.append(running_total)


    # create a total count
    total_c = Counter()
    for data in series["c"].values():
        total_c.update(data)

    total_c_sorted = sorted(total_c.items())
    total_c_times = [t for t, v in total_c_sorted]
    total_c_values = [v for t, v in total_c_sorted]

    running_total = 0
    total_c_values_accu = []
    for t, v in total_c_sorted:
        running_total += v
        total_c_values_accu.append(running_total)


    total = Counter()
    for data in series["c"].values():
        total.update(data)
    for data in series["v"].values():
        total.update(data)

    total_sorted = sorted(total.items())
    total_times = [t for t, v in total_sorted]
    total_values = [v for t, v in total_sorted]

    running_total = 0
    total_values_accu = []
    for t, v in total_sorted:
        running_total += v
        total_values_accu.append(running_total)

    fig, (ax, axins) = plt.subplots(2, 1)

    vals = np.array(list(total_values_accu))
    threshold = np.percentile(vals, 95)
    axins.set_ylim(0, threshold * 1.3)

    if total_vivi_times:
        ax.plot(total_vivi_times, total_vivi_values_accu, label="vivify only", linestyle="-")
    if total_c_times:
        ax.plot(total_c_times, total_c_values_accu, label="cadical", linestyle="-")
    if total_c_times and total_vivi_times and total_times:
        ax.plot(total_times, total_values_accu, label="total vivified", linestyle="-")
    if total_checked_sorted:
        ax.plot(total_checked_times, total_checked_values_accu, label="total checked", linestyle="-")

    if total_vivi_times:
        axins.plot(total_vivi_times, total_vivi_values_accu, label="vivify only", linestyle="-")
    if total_c_times:
        axins.plot(total_c_times, total_c_values_accu, label="cadical", linestyle="-")
    if total_c_times and total_vivi_times and total_times:
        axins.plot(total_times, total_values_accu, label="total vivified", linestyle="-")
    if total_checked_sorted:
        axins.plot(total_checked_times, total_checked_values_accu, label="total checked", linestyle="-")


    axins.set_xlabel("solver time")
    plt.ylabel("number of clauses")
    ax.legend()
    ax.set_title("vivifications over time")
    plt.savefig(sys.argv[2] + "/vivifications_" + sys.argv[3] + ".svg")

main()
