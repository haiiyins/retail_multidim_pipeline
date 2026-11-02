"""Run registry: one JSON line per training / evaluation run in data/ml/registry/runs.jsonl (append-only, no lakehouse lock).

Each record: run_id, model, started / finished (UTC), wall_sec, git commit (+dirty), host, config hash, params, metrics, artifacts."""
import datetime as dt, hashlib, json, os, socket, subprocess, time, uuid
import pandas as pd
from ml.common.data import ROOT, ml_path

REGISTRY = "registry/runs.jsonl"


def _git():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True).strip())
        return sha, dirty
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None


def config_hash(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:12]


class Run:
    """with Run("p1_tuned", config) as run: ...; run.metrics.update(...); run.artifacts[...] = path"""

    def __init__(self, model, config=None, params=None, notes=""):
        self.record = {"run_id": uuid.uuid4().hex[:12], "model": model, "config": config or {}, "config_hash": config_hash(config or {}),
                       "params": params or {}, "notes": notes}
        self.metrics, self.artifacts = {}, {}

    def __enter__(self):
        self._t0 = time.time()
        self.record["started"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        return self

    def __exit__(self, exc_type, exc, tb):
        sha, dirty = _git()
        self.record.update(finished=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), wall_sec=round(time.time() - self._t0, 1),
                           git_commit=sha, git_dirty=dirty, host=socket.gethostname().split(".")[0], status="failed" if exc_type else "ok",
                           metrics=self.metrics, artifacts=self.artifacts)
        with open(ml_path(REGISTRY), "a") as f:
            f.write(json.dumps(self.record, default=str) + "\n")
        return False


def runs(model=None):
    path = ml_path(REGISTRY)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_json(path, lines=True)
    return df[df["model"] == model] if model else df
