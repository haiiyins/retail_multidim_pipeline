"""Render the dbt lineage as figures for the report (WBS 5.1, issue #44): reads dbt_multidim/target/manifest.json (run `dbt docs generate`
first), draws the model DAG with Graphviz — full pipeline and one figure per layer boundary — into docs/figures/lineage_*.{svg,png}.
Nodes are coloured by layer (sources, staging, silver, quarantine, audit, gold); tests are omitted."""
import json, pathlib, subprocess, sys
MAN = pathlib.Path("dbt_multidim/target/manifest.json"); OUT = pathlib.Path("docs/figures"); OUT.mkdir(parents=True, exist_ok=True)
man = json.loads(MAN.read_text())
COL = {"source": "#e0e0e0", "staging": "#d9ead3", "silver": "#cfe2f3", "quarantine": "#f4cccc", "audit": "#fff2cc", "gold": "#ffe599"}
def layer(uid):
    if uid.startswith("source."): return "source"
    node = man["nodes"][uid]; path = node.get("original_file_path", "")
    for l in ("staging", "silver", "quarantine", "audit", "gold"):
        if f"/{l}/" in path or path.startswith(f"models/{l}/"): return l
    return "gold"
def label(uid):
    if uid.startswith("source."): return man["sources"][uid]["name"]
    return man["nodes"][uid]["name"]
models = {uid: n for uid, n in man["nodes"].items() if n["resource_type"] == "model"}
edges = set()
for uid, n in models.items():
    for dep in n["depends_on"].get("nodes", []):
        if dep in models or dep.startswith("source."): edges.add((dep, uid))
# the Python-built Gold tables are referenced as plain gold.* relations: add them from the raw SQL
for uid, n in models.items():
    sql = n.get("raw_code", "")
    for t in ("anchor_grid", "anchor_model_grid", "split_windows"):
        if f"gold.{t}" in sql: edges.add((f"python.{t}", uid))
def write(name, keep):
    lines = ["digraph lineage {", 'rankdir=LR; node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10]; edge [color="#666666"];']
    nodes = {a for a, b in edges if keep(a) and keep(b)} | {b for a, b in edges if keep(a) and keep(b)}
    for u in sorted(nodes):
        if u.startswith("python."): lines.append(f'"{u}" [label="{u.split(".")[1]}\\n(python)", fillcolor="{COL["gold"]}", shape=component];')
        else: lines.append(f'"{u}" [label="{label(u)}", fillcolor="{COL[layer(u)]}"];')
    for a, b in sorted(edges):
        if keep(a) and keep(b): lines.append(f'"{a}" -> "{b}";')
    lines.append("}")
    dot = OUT / f"{name}.dot"; dot.write_text("\n".join(lines))
    for fmt in ("svg", "png"):
        subprocess.run(["dot", f"-T{fmt}", str(dot), "-o", str(OUT / f"{name}.{fmt}")], check=True)
    dot.unlink(); print(f"→ docs/figures/{name}.svg / .png  ({len(nodes)} nodes)")
L = lambda u: "python" if u.startswith("python.") else layer(u)
write("lineage_full", lambda u: True)
write("lineage_bronze_to_silver", lambda u: L(u) in ("source", "staging", "silver", "quarantine", "audit"))
write("lineage_silver_to_gold", lambda u: L(u) in ("silver", "gold", "python") or (L(u) == "quarantine" and label(u) == "leakage_violations"))
