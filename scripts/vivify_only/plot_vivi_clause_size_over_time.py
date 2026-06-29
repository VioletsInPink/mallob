import glob
import re
import sys
from collections import defaultdict
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")

pattern_time = re.compile(r'\[(\d+\.\d+)\]')
pattern_data = re.compile(r'\((\d+)\)')
pattern_type = re.compile(r'vivify (clause)')
pattern_vivi = re.compile(r'\((c|v)\)')

def parse_file(fname, data):

    with open(fname, "r") as f:
        for line in f:
            if ") vivify" not in line:
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


            k = pattern_vivi.search(line)
            if not k:
                print("No key:", line)
                continue
            k = k.group(1)
        
            # print(t, k, d)

            data[k][t].append(d)

    return data


def merge_all(files):
    series = defaultdict(lambda: defaultdict(list))

    for f in files:
        parse_file(f, series)

    return series


def main():
    files = glob.glob(f"{sys.argv[1]}/**/cadical.out.#*.*", recursive=True)
    
    if not files:
        print("No cadical.out.#*.* files found")
        return

    series = merge_all(files)

    # print(series)

    for kind, marker, name in [("v", "x", "vivify only"), ("c", "o", "CaDiCal")]:
        xs = []
        ys = []

        for t, values in series[kind].items():
            for d in set(values):
                xs.append(t)
                ys.append(d)

        plt.scatter(xs, ys, marker=marker, label=name, s=8)

    plt.xlabel("Time")
    plt.ylabel("Clause length")
    plt.legend()
    plt.title("Length of vivified clauses over time")
    plt.savefig(sys.argv[2] + "clause_length_over_time.svg")
    plt.clf()



    all_values = [
        d
        for type_dict in series.values()
        for time_dict in type_dict.values()
        for d in time_dict
    ]
    counts = Counter(all_values)
    plt.bar(counts.keys(), counts.values())

    plt.xlabel("clause length")
    plt.ylabel("occurence count")
    plt.title("Occurences of Clause length")
    plt.savefig(sys.argv[2] + "clause_length_distribution.svg")

main()

