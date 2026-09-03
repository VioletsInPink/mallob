import matplotlib.pyplot as plt
import matplotlib
import sys
import re

import statistics_extractor

matplotlib.use("Agg")

RESULT_DIR = sys.argv[1]
OUT_TEX = sys.argv[2] + "/table.tex"
OUT_SVG = sys.argv[2] + "/table.svg"
OUT_MD = sys.argv[2] + "/table.md"

data = []

# -------------------------
# LOAD DATA
# -------------------------
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
    m = re.fullmatch(r"_v(\d+\.?\d*)%", suffix)
    if m:
        return (2, float(m.group(1)))

    if suffix.startswith("+"):
        m = re.search(r"_v(\d+)%", suffix)
        if m:
            return (3, int(m.group(1)))
        return (3, 0)

    return (4, suffix)

stats = statistics_extractor.getStats(RESULT_DIR)
stats = sorted(
    statistics_extractor.getStats(RESULT_DIR),
    key=cadical_sort_key,
)

data.append([    "solver",      "solved",               "par2",          "busy_time",                 "",                                                "scheduled",                                       "vivified",                                           "scheduled per sec",                                                             "subsumed"])
data.append([    "",            "sat + unsat",          "",              "vivify_time",               "vivify time%",                                    "vivified%",                                       "str + subs",                                         "vivified per sec",                                                              "subsumed without vivification"])
for s in stats:
    data.append([s.solver_name, s.solved,               f"{s.par2:.2f}", f"{s.avg.busy_time:.2f}s",    "",                                                f"{s.avg.vivify_sched:.2f}",                       f"{s.avg.vivified:.2f}",                              f"{s.avg.vivify_sched / s.avg.vivify_time if s.avg.vivify_time > 0 else 0:.2f}", f"{s.avg.subsumed:.2f}"])
    data.append(["",            f"{s.sat} + {s.unsat}", "",              f"{s.avg.vivify_time / s.avg.num_active_threads:.2f}s", f"{s.percent.avg.vivify_time.avg.solve_time:.2f}%", f"{s.percent.avg.vivified.avg.vivify_sched:.2f}%", f"{s.avg.vivify_strs:.2f} + {s.avg.vivify_subs:.2f}", f"{s.avg.vivified / s.avg.vivify_time if s.avg.vivify_time > 0 else 0:.2f}",     f"{(s.avg.subsumed / (1 - (s.percent.avg.vivify_time.avg.solve_time/ 100))):.2f}"])
# -------------------------
# MARKDOWN TABLE
# -------------------------
md = []
md.append("| " + " | ".join(map(str, data[0])) + " |")
md.append("| " + " | ".join(map(str, data[1])) + " |")
md.append("| " + " | ".join(["---"] * len(data[0])) + " |")

for row in data[2:]:
    md.append("| " + " | ".join(map(str, row)) + " |")


with open(OUT_MD, "w") as f:
    f.write("\n".join(md))

print(f"Wrote Markdown table to {OUT_MD}")


# -------------------------
# LATEX TABLE
# -------------------------
latex = []
latex.append("\\begin{tabular}{" + "l"*len(data[0]) + "}")
latex.append("\\toprule")
latex.append(" & ".join(map(str, data[0])).replace("_", r"\_").replace("%", r"\%") + "\\\\")
latex.append(" & ".join(map(str, data[1])).replace("_", r"\_").replace("%", r"\%") + "\\\\")
latex.append("\\midrule")

for i, row in enumerate(data[2:]):
    latex.append(" & ".join(map(str, row)).replace("_", r"\_").replace("%", r"\%") + "\\\\")
    if i % 2 == 1:
        latex.append("\\addlinespace")

latex.pop()
latex.append("\\bottomrule")
latex.append("\\end{tabular}")

with open(OUT_TEX, "w") as f:
    f.write("\n".join(latex))

print(f"Wrote LaTeX table to {OUT_TEX}")

# -------------------------
# SVG PLOT (PAR2 + solved)
# -------------------------
# plt.figure()
#
# plt.axis("off")
#
# table_data = [data[0]]
# table_data = data[1:]
#
# plt.table(cellText=table_data, loc="center", cellLoc="left")
#
# plt.title("Mallob / CaDiCaL Config Comparison")
# plt.tight_layout()
# plt.savefig(OUT_SVG, format="svg")
#
# print(f"Wrote SVG plot to {OUT_SVG}")
