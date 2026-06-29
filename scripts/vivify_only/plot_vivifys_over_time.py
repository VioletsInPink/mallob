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

def parse_file(fname, data):

    with open(fname, "r") as f:
        for line in f:
            if "] vivify" not in line:
                continue

            t = pattern_time.search(line)
            if not t:
                print("No time:", line)
                continue
            t = round(float(t.group(1)), 3)
            

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
        
            # print(t, k, d)

            if t in data[k]:
                data[k][t] += d
            else:
                data[k][t] = d

    return data


def merge_all(files):
    series = defaultdict(dict)

    for f in files:
        parse_file(f, series)

    return series


def main():
    files = glob.glob(f"{sys.argv[1]}/**/cadical.out.#*.*", recursive=True)
    
    if not files:
        print("No cadical.out.#*.* files found")
        return

    series = merge_all(files)

    # these keys correlate to vivified values
    vivify_keys = ["subsumed", "strengthened", "unit"]
    vivified = defaultdict(dict)
    for k in vivify_keys:
        if k in series:
            vivified[k] = series[k]

    if not vivified:
        print("did not vivify: skip")
        return

    # create a total counr
    total = Counter()
    for data in vivified.values():
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

        # plot individual series
        for name, data in vivified.items():
            items = sorted(data.items())
            times = [t for t, v in items]
            values = [v for t, v in items]

            # plt.plot(times, values, label=name, linestyle="None", marker='x')
            ax.plot(times, values, label=name, linestyle="None", marker='x')
            axins.plot(times, values, label=name, linestyle="None", marker='x')
            
        # plot a total line
        ax.plot(total_times, total_values, label="TOTAL", linestyle="--")
        axins.plot(total_times, total_values, label="TOTAL", linestyle="--")

        axins.set_xlabel("time")
        ax.set_ylabel("value")
        ax.legend()
        ax.set_title("vivifications over time")
        plt.savefig(sys.argv[2] + "vivifications.svg")

    else: 
        # plot individual series
        for name, data in vivified.items():
            items = sorted(data.items())
            times = [t for t, v in items]
            values = [v for t, v in items]

            plt.plot(times, values, label=name, linestyle="None", marker='x')
        
        # plot a total line
        plt.plot(total_times, total_values, label="TOTAL", linestyle="--")

        plt.xlabel("time")
        plt.ylabel("value")
        plt.legend()
        plt.title("vivifications over time")
        plt.savefig(sys.argv[2] + "vivifications.svg")

main()
