"""Product levels coarser than the model: every model belongs to exactly one group per level in bronze.dim_item. Used by the
granularity ladder (ml/eval/granularity.py) and by sources trained directly at a level (Events.load(level=...))."""
import os

from ml.common.data import ML_DIR

LEVELS = {"model": "model_code", "supermodel": "supermodel_code", "nature": "product_nature_id", "family": "retail_family_code",
          "subdept": "retail_sub_department_code", "department": "retail_department_code"}


def group_map(con):
    """Parquet path of model_code → one VARCHAR column per level (cached; the lakehouse stays read-only)."""
    path = os.path.join(ML_DIR, "eval", "model_groups.parquet")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cols = ", ".join(f"CAST(ANY_VALUE({c}) AS VARCHAR) AS {lv}" for lv, c in LEVELS.items() if lv != "model")
        con.execute(f"""COPY (SELECT model_code, model_code AS model, {cols} FROM lh.bronze.dim_item
                    WHERE model_code IS NOT NULL GROUP BY model_code) TO '{path}' (FORMAT parquet)""")
    return path


def grid_relation(con, level="model"):
    """gold.anchor_model_grid at a level: a group is recommendable at an anchor when one of its models is."""
    if level == "model":
        return "lh.gold.anchor_model_grid"
    return (f"(SELECT DISTINCT g.country_code, g.anchor_date, m.{level} AS model_code FROM lh.gold.anchor_model_grid g "
            f"JOIN read_parquet('{group_map(con)}') m USING (model_code))")


def native_level(name):
    """Level of a score set trained at a level (rex_<level>_nbr…), None for model-level score sets."""
    parts = name.split("_")
    return parts[1] if len(parts) > 2 and parts[0] in ("rex", "rex2") and parts[1] in LEVELS and parts[1] != "model" else None
