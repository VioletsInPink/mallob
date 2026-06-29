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

def parse_file(fname, data):

    with open(fname, "r") as f:
        for line in f:
            if "] vivify" not in line:
                continue

            t = pattern_time.search(line)
            if not t:
                print("No time:", line)
                continue
            t = round(float(t.group(1)), 1)
            

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

            if k == "checked":
                continue

            v = pattern_vivi.search(line)
            if not v:
                print("No type:", line)
                continue
            v = v.group(1)

            # print(t, k, d)

            if t in data[k]:
                data[v][k][t] += d
            else:
                data[v][k][t] = d

    return data


def merge_all(files):
    series = defaultdict(lambda: defaultdict(dict))

    for f in files:
        parse_file(f, series)

    return series


def main():
    files = glob.glob(f"{sys.argv[1]}/**/cadical.out.#*.*", recursive=True)
    
    if not files:
        print("No cadical.out.#*.* files found")
        return

    series = merge_all(files)

    if not series:
        print("did not vivify: skip")
        return

    # create a total count
    total_vivi = Counter()
    for data in series["v"].values():
        total_vivi.update(data)

    total_vivi_sorted = sorted(total_vivi.items())
    total_vivi_times = [t for t, v in total_vivi_sorted]
    total_vivi_values = [v for t, v in total_vivi_sorted]

    # create a total count
    total_c = Counter()
    for data in series["c"].values():
        total_c.update(data)

    total_c_sorted = sorted(total_c.items())
    total_c_times = [t for t, v in total_c_sorted]
    total_c_values = [v for t, v in total_c_sorted]


    total = Counter()
    for data in series["c"].values():
        total.update(data)
    for data in series["v"].values():
        total.update(data)

    total_sorted = sorted(total.items())
    total_times = [t for t, v in total_sorted]
    total_values = [v for t, v in total_sorted]

    # calculate a ratio
    vals = list(total.values())

    avg = sum(vals) / len(vals)
    mx = max(vals)

    spike_ratio = mx / avg if avg > 0 else 0

    if (spike_ratio > 10):
        fig, (ax, axins) = plt.subplots(2, 1)
        vals = np.array(list(total.values()))
        threshold = np.percentile(vals, 95)
        axins.set_ylim(0, threshold + 2)

        # # plot individual series
        # for name, data in vivified.items():
        #     items = sorted(data.items())
        #     times = [t for t, v in items]
        #     values = [v for t, v in items]
        #
        #     # plt.plot(times, values, label=name, linestyle="None", marker='x')
        #     ax.plot(times, values, label=name, linestyle="None", marker='x')
        #     axins.plot(times, values, label=name, linestyle="None", marker='x')

        # plot a total line

        if total_vivi_times:
            ax.plot(total_vivi_times, total_vivi_values, label="vivify only", linestyle="--", marker="x", ms=8)
        if total_c_times:
            ax.plot(total_c_times, total_c_values, label="cadical", linestyle="None", marker="x", ms=8)
        if total_times:
            ax.plot(total_times, total_values, label="total", linestyle="--")

        if total_vivi_times:
            axins.plot(total_vivi_times, total_vivi_values, label="vivify only", linestyle="--", marker="x", ms=8)
        if total_c_times:
            axins.plot(total_c_times, total_c_values, label="cadical", linestyle="None", marker="x", ms=8)
        if total_times:
            axins.plot(total_times, total_values, label="total", linestyle="--")



        axins.set_xlabel("solver time")
        ax.set_ylabel("value")
        ax.legend()
        ax.set_title("vivifications over time")
        plt.savefig(sys.argv[2] + "vivifications.svg")

    else: 

        # # plot individual series
        # for name, data in vivified.items():
        #     items = sorted(data.items())
        #     times = [t for t, v in items]
        #     values = [v for t, v in items]
        #
        #     plt.plot(times, values, label=name, linestyle="None", marker='x')
        
        # plot a total line
        if total_vivi_times: 
            plt.plot(total_vivi_times, total_vivi_values, label="vivify only", linestyle="None", marker="x", ms=8)
        if total_c_times:
            plt.plot(total_c_times, total_c_values, label="cadical", linestyle="None", marker=".", ms=8)
        if total_times:
            plt.plot(total_times, total_values, label="total", linestyle="--")

        plt.xlabel("solver time")
        plt.ylabel("number of vivifications")
        plt.legend()
        plt.title("vivifications over time")
        plt.savefig(sys.argv[2] + "vivifications.svg")



main()
