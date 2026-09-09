import matplotlib.pyplot as plt
import matplotlib
import sys
import re

import statistics_extractor

matplotlib.use("Agg")

RESULT_DIR = sys.argv[1]
def OUT_TEX(s): return sys.argv[2] + "/" + s + "table.tex"
def OUT_SVG(s): return sys.argv[2] +"/" + s + "table.svg"
def OUT_MD(s): return sys.argv[2] + "/" + s + "table.md"

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

def create_tables(data, suffix=""):
    # -------------------------
    # MARKDOWN TABLE
    # -------------------------
    md = []
    md.append("| " + " | ".join(map(str, data[0])) + " |")
    md.append("| " + " | ".join(map(str, data[1])) + " |")
    md.append("| " + " | ".join(["---"] * len(data[0])) + " |")

    for row in data[2:]:
        md.append("| " + " | ".join(map(str, row)) + " |")


    with open(OUT_MD(suffix), "w") as f:
        f.write("\n".join(md))

    print(f"Wrote Markdown table to {OUT_MD(suffix)}")


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

    with open(OUT_TEX(suffix), "w") as f:
        f.write("\n".join(latex))

    print(f"Wrote LaTeX table to {OUT_TEX(suffix)}")

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

data.append(["solver", "solved",               "par2", "par1", "mean solve_time"          "avg busy_time",                       "",                                                      "checked",                                                "vivified",                                                       "checked per sec",                                                                  "prod", "vivi prod", "subsumed"])
data.append([    "",            "sat + unsat",          "",               "",                     "avg vivify time%",                                          "sched",                                              "str + rat",                                                     "vivified per sec",                                                                 "flt + adm + drp", "flt + adm + drp", "subsume time"])
for s in stats:
    data.append([s.solver_name, s.solved,               round(s.par2, 2), f"{round(s.avg.busy_time, 2)}s",   "",                                                      round(s.avg.vivify_checked, 2),                           f"{round(s.avg.vivified, 2)}",                                    round(s.avg.vivify_checked / s.avg.vivify_time if s.avg.vivify_time > 0 else 0, 2), round(s.avg.prod, 2), round(s.avg.vivi_prod, 2), round(s.avg.subsumed, 2)])
    data.append(["",            f"{s.sat} + {s.unsat}", "",               f"{round(s.avg.vivify_time, 2)}s", f"{round(s.percent.avg.vivify_time.avg.busy_time, 2)}%", f"{round(s.avg.vivify_sched)}", f"{round(s.avg.vivify_strs, 2)} + {round(s.avg.vivify_rat, 2)}", round(s.avg.vivified / s.avg.vivify_time if s.avg.vivify_time > 0 else 0, 2),       f"{round(s.avg.prod_flt, 2)} + {round(s.avg.prod_adm, 2)} + {round(s.avg.prod_drp, 2)}", f"{round(s.avg.vivi_prod_flt, 2)} + {round(s.avg.vivi_prod_adm, 2)} + {round(s.avg.vivi_prod_drp, 2)}", f"{round(s.avg.subsume_time, 2)}"])

create_tables(data)

data = []

data.append(["solver", "solved", "sat + unsat", "par2", "par1", "mean solve time", "avg solve time", "avg vivify time %"])
for s in stats:
    data.append([s.solver_name, s.solved, f"{s.sat} + {s.unsat}", round(s.par2, 2), round(s.par1), f"{round(s.mean.busy_time)}s", f"{round(s.avg.busy_time, 2)}s", f"{round(s.percent.avg.vivify_time.avg.solve_time, 2)}%"])

create_tables(data, "small_")
