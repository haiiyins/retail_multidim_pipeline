"""Render the dbt lineage as figures for the report (WBS 5.1, issue #44): reads dbt_multidim/target/manifest.json (run `dbt docs generate`
first), draws the model DAG with Graphviz — full pipeline and one figure per layer boundary — into docs/figures/lineage_*.{svg,png}.

Layout: left-to-right columns by dependency depth (Bronze sources in column 0, every model one column right of its deepest input), all
nodes of a column on the same rank, boxes of one width, orthogonal edges. Nodes are coloured by layer (sources, staging, silver,
quarantine, audit, gold, python-built Gold tables); tests are omitted. The three Gold tables built by evaluation/build_anchor_grid.py are
drawn as components with their real inputs (the Silver tables the script reads) so the grid sits between Silver and Gold."""
import json, pathlib, subprocess
MAN = pathlib.Path("dbt_multidim/target/manifest.json"); OUT = pathlib.Path("docs/figures"); OUT.mkdir(parents=True, exist_ok=True)
man = json.loads(MAN.read_text())
COL = {"source": "#e0e0e0", "staging": "#d9ead3", "silver": "#cfe2f3", "quarantine": "#f4cccc", "audit": "#fff2cc", "gold": "#ffe599", "python": "#ffd966"}
LEGEND = [("source", "Bronze source (Parquet view)"), ("staging", "staging view"), ("silver", "Silver model"), ("quarantine", "quarantine table"),
          ("audit", "audit table"), ("gold", "Gold model"), ("python", "Gold table built by Python")]
# the anchor grid is built by evaluation/build_anchor_grid.py from these Silver tables; split_windows comes from evaluation/split.yml
PY_INPUTS = {"python.anchor_grid": ["silver.slv_fact_sales_line", "silver.slv_fact_returns", "silver.slv_member_profile"],
             "python.anchor_model_grid": ["python.anchor_grid", "silver.slv_fact_sales_line"], "python.split_windows": []}


def layer(uid):
    if uid.startswith("source."): return "source"
    if uid.startswith("python."): return "python"
    path = man["nodes"][uid].get("original_file_path", "")
    for l in ("staging", "silver", "quarantine", "audit", "gold"):
        if f"/{l}/" in path or path.startswith(f"models/{l}/"): return l
    return "gold"


def label(uid):
    if uid.startswith("source."): return man["sources"][uid]["name"]
    if uid.startswith("python."): return uid.split(".", 1)[1]
    return man["nodes"][uid]["name"]


models = {uid: n for uid, n in man["nodes"].items() if n["resource_type"] == "model"}
by_name = {n["name"]: uid for uid, n in models.items()}
edges = set()
for uid, n in models.items():
    for dep in n["depends_on"].get("nodes", []):
        if dep in models or dep.startswith("source."): edges.add((dep, uid))
    for t in ("anchor_grid", "anchor_model_grid", "split_windows"):          # Python-built Gold tables referenced as plain gold.* relations
        if f"gold.{t}" in n.get("raw_code", ""): edges.add((f"python.{t}", uid))
for py, inputs in PY_INPUTS.items():
    for i in inputs:
        src = i if i.startswith("python.") else by_name.get(i.split(".", 1)[1])
        if src: edges.add((src, py))


def depth_of(nodes, kept_edges):
    """Longest path from a node without inputs (the Bronze sources); split_windows has none, so it is pinned next to anchor_grid."""
    preds = {n: [a for a, b in kept_edges if b == n] for n in nodes}; memo = {}
    def d(n):
        if n not in memo: memo[n] = 0 if not preds[n] else 1 + max(d(p) for p in preds[n])
        return memo[n]
    depth = {n: d(n) for n in nodes}
    if "python.split_windows" in depth and "python.anchor_grid" in depth: depth["python.split_windows"] = depth["python.anchor_grid"]
    return depth


def write(name, keep):
    kept = sorted((a, b) for a, b in edges if keep(a) and keep(b))
    nodes = sorted({a for a, b in kept} | {b for a, b in kept}, key=lambda u: (list(COL).index(layer(u)), label(u)))
    depth = depth_of(nodes, kept)
    lines = ["digraph lineage {",
             'graph [rankdir=LR, splines=ortho, newrank=true, nodesep=0.18, ranksep=0.7, dpi=144, fontname="Helvetica", pad=0.3];',
             'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, width=2.3, height=0.34, fixedsize=true, color="#808080"];',
             'edge [color="#7a7a7a", arrowsize=0.6, penwidth=0.9];']
    for u in nodes:
        shape = ', shape=component, style="filled"' if layer(u) == "python" else ""
        lines.append(f'"{u}" [label="{label(u)}", fillcolor="{COL[layer(u)]}"{shape}];')
    legend = '<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">' + "".join(
        f'<tr><td bgcolor="{COL[k]}" width="18"></td><td align="left"> {t}</td></tr>' for k, t in LEGEND if any(layer(u) == k for u in nodes)) + "</table>>"
    lines.append(f'legend [shape=plaintext, style="", fixedsize=false, fontsize=11, label={legend}];')
    for c in sorted(set(depth.values())):
        members = " ".join(f'"{u}";' for u in nodes if depth[u] == c) + (" legend;" if c == 0 else "")
        lines.append("{ rank=same; " + members + " }")
    for a, b in kept: lines.append(f'"{a}" -> "{b}";')
    lines.append("}")
    dot = OUT / f"{name}.dot"; dot.write_text("\n".join(lines))
    for fmt in ("svg", "png"):
        subprocess.run(["dot", f"-T{fmt}", str(dot), "-o", str(OUT / f"{name}.{fmt}")], check=True)
    dot.unlink(); print(f"→ docs/figures/{name}.svg / .png  ({len(nodes)} nodes, {len(kept)} edges, {max(depth.values()) + 1} columns)")


write("lineage_full", lambda u: True)
write("lineage_bronze_to_silver", lambda u: layer(u) in ("source", "staging", "silver", "quarantine", "audit") and label(u) not in ("leakage_violations", "candidate_recall"))
write("lineage_silver_to_gold", lambda u: layer(u) in ("silver", "gold", "python") or label(u) in ("leakage_violations", "candidate_recall"))
