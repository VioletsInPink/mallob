import matplotlib.pyplot as plt
import matplotlib
import sys

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
stats = statistics_extractor.getStats(RESULT_DIR)

data.append(["solver", "solved", "sat", "unsat", "par2", "busy_time", "vivify_time", "vivified", "vivify_throughput", "percent_time_in_vivify"])
for s in stats:
    data.append([s.solver_name, s.solved, s.sat, s.unsat, round(s.par2, 3), round(s.busy_time_per_instance, 3), round(s.vivify_time_per_instance, 3), round(s.vivified_per_instance, 3), round(s.vivified_throughput), round(100 * s.vivify_time_per_instance / s.busy_time_per_instance, 3)])

# -------------------------
# MARKDOWN TABLE
# -------------------------
md = []
md.append("| " + " | ".join(map(str, data[0])) + " |")
md.append("| " + " | ".join(["---"] * len(data[0])) + " |")

for row in data[1:]:
    md.append(f"| " + " | ".join(map(str, row)) + " |")


with open(OUT_MD, "w") as f:
    f.write("\n".join(md))

print(f"Wrote Markdown table to {OUT_MD}")


# -------------------------
# LATEX TABLE
# -------------------------
latex = []
latex.append("\\begin{tabular}{lrrrrr}")
latex.append("\\hline")
latex.append(" & ".join(map(str, data[0])) + "\\\\")
latex.append("\\hline")

for row in data[1:]:
    latex.append(" & ".join(map(str, row)) + "\\\\")

latex.append("\\hline")
latex.append("\\end{tabular}")

with open(OUT_TEX, "w") as f:
    f.write("\n".join(latex))

print(f"Wrote LaTeX table to {OUT_TEX}")

# -------------------------
# SVG PLOT (PAR2 + solved)
# -------------------------
plt.figure()

plt.axis("off")

table_data = [data[0]]
table_data = data[1:]

plt.table(cellText=table_data, loc="center", cellLoc="left")

plt.title("Mallob / CaDiCaL Config Comparison")
plt.tight_layout()
plt.savefig(OUT_SVG, format="svg")

print(f"Wrote SVG plot to {OUT_SVG}")
