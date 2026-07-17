import matplotlib.pyplot as plt
import matplotlib
import sys

matplotlib.use("Agg")

INPUT_FILE = sys.argv[1] + "/summary_table.txt"
OUT_TEX = sys.argv[2] + "/table.tex"
OUT_SVG = sys.argv[2] + "/table.svg"
OUT_MD = sys.argv[2] + "/table.md"

data = []

# -------------------------
# LOAD DATA
# -------------------------
with open(INPUT_FILE, "r") as f:
    for line in f:
        parts = line.strip().split()
        data.append(parts)

# sort by PAR2 (lower is better)
# data.sort(key=lambda x: x[4])

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
