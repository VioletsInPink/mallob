import matplotlib.pyplot as plt
import matplotlib
import sys

matplotlib.use("Agg")

INPUT_FILE = sys.argv[1] + "/summary_table.txt"
OUT_TEX = sys.argv[2] + "/table.tex"
OUT_SVG = sys.argv[2] + "/plot.svg"

data = []

# -------------------------
# LOAD DATA
# -------------------------
with open(INPUT_FILE, "r") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) < 4:
            continue

        solver = parts[0]
        solved = int(parts[1])
        sat = int(parts[2])
        unsat = int(parts[3])
        par2 = float(parts[4])

        data.append((solver, solved, sat, unsat, par2))

# sort by PAR2 (lower is better)
data.sort(key=lambda x: x[4])

# -------------------------
# LATEX TABLE
# -------------------------
latex = []
latex.append("\\begin{tabular}{lrrrrr}")
latex.append("\\hline")
latex.append("Solver & SAT & UNSAT & Solved & PAR2 \\\\")
latex.append("\\hline")

for solver, solved, sat, unsat, par2 in data:
    latex.append(f"{solver} & {solved} & {sat} & {unsat} & {par2:.2f} \\\\")

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

table_data = [["Solver", "solved", "sat", "unsat", "PAR2"]]
table_data += [[s, str(sol), str(sat), str(usat), f"{p:.2f}"]
               for s, sol, sat, usat, p in sorted(data)]

plt.table(cellText=table_data, loc="center", cellLoc="left")

plt.title("Mallob / CaDiCaL Config Comparison")
plt.tight_layout()
plt.savefig(OUT_SVG, format="svg")

print(f"Wrote SVG plot to {OUT_SVG}")
