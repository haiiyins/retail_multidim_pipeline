"""P3 training, tuning and scoring (plan §8, D5 / D6 / D9). Train on every train anchor with a positive in its list (listwise loss);
early stopping on the unconditional valid NDCG@20 after every epoch; tuning = the fair harness (tuning.yml p3, n_trials trials).
Variants (t32 ablation, with the tuned parameters of full): full · onehead (no gating) · fixedgate (g = repeat share) · noseq (context
only, no sequence encoder nor attention) · nodin (no target attention).
Usage: python ml/umtr/train.py --source v2 --tune
       python ml/umtr/train.py --source v2 --final --variants full,onehead,fixedgate,noseq   →  data/ml/scores/p3_<variant>_<split>_d30.parquet"""
import argparse, copy, json, os, sys, time
import numpy as np, pandas as pd, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect, load_config, ml_path
from ml.common.registry import Run
from ml.common.tuning import N_TRIALS, tune
from ml.eval.protocol import build_positives, evaluate
from ml.retrieval.neural import seed_everything
from ml.umtr.data import get
from ml.umtr.model import UMTR, loss_fn

C = load_config("umtr")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
VARIANTS = {"full": {}, "onehead": {"two_head": False}, "fixedgate": {"gate": "fixed"}, "noseq": {"sequence": False, "din": False},
            "nodin": {"din": False}}
LONG = ("model", "dept", "seq", "gap")


def batch(d, i):
    return {k: (d[k][i].to(DEVICE, non_blocking=True).long() if k in LONG else d[k][i].to(DEVICE, non_blocking=True))
            for k in ("x", "model", "dept", "rep", "y30", "y90", "mask", "seq", "gap", "rho", "gate_y")}


def build(meta, params, variant):
    n_feat = meta["stats"]["mean"].shape[0] + len(meta["stats"]["flag_cols"])
    return UMTR(n_feat, meta["n_models"], meta["n_dept"], params["d"], params["dropout"], C["heads"], C["blocks"], C["max_len"],
                **VARIANTS[variant]).to(DEVICE)


@torch.no_grad()
def score(model, d, codes, bs=1024):
    model.eval()
    parts = []
    for s in range(0, len(d["x"]), bs):
        i = torch.arange(s, min(s + bs, len(d["x"])))
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=DEVICE == "cuda"):
            lp = model(batch(d, i))["logp"].float().cpu()
        parts.append(lp)
    lp = torch.cat(parts).numpy()
    mask = d["mask"].numpy()
    a, k = np.nonzero(mask)
    head = d["anchors"]
    return pd.DataFrame({"member_id": head["member_id"].to_numpy()[a], "anchor_date": head["anchor_date"].to_numpy()[a],
                         "model_code": codes[d["model"].numpy()[a, k] - 1], "country_code": head["country_code"].to_numpy()[a],
                         "score": lp[a, k]})


def ndcg(con, scores, split, metric="NDCG@20"):
    con.register("_s", scores)
    res = evaluate(con, "_s", f"read_parquet('{build_positives(con, split, 30)}')")
    con.unregister("_s")
    return float(res.groupby("member_id")[metric].mean().mean())


def fit(tr, va, params, variant, con, codes, seed=0, log=""):
    seed_everything(seed)
    model = build(tr["meta"], params, variant)
    opt = torch.optim.AdamW(model.parameters(), lr=params["lr"], weight_decay=0.01)
    train_idx = torch.nonzero((tr["y30"] & tr["mask"]).any(1)).squeeze(1)
    gen = torch.Generator().manual_seed(seed)
    best, best_state, best_ep = -1.0, None, -1
    for ep in range(C["epochs"]):
        model.train()
        t0, tot, n = time.time(), 0.0, 0
        perm = train_idx[torch.randperm(len(train_idx), generator=gen)]
        for s in range(0, len(perm), C["batch"]):
            b = batch(tr, perm[s:s + C["batch"]])
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=DEVICE == "cuda"):
                loss = loss_fn(model, b, params["lambda_d90"], params["lambda_gate"])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tot, n = tot + loss.detach(), n + 1
        v = ndcg(con, score(model, va, codes), "valid")
        print(f"    {log} epoch {ep}: loss {float(tot) / max(n, 1):.4f}  valid NDCG@20 {v:.4f}  {time.time() - t0:.0f}s", flush=True)
        if v > best:
            best, best_ep, best_state = v, ep, copy.deepcopy(model.state_dict())
    model.load_state_dict(best_state)
    return model, best, best_ep


def study(source):
    return "p3" if source == "v2" else f"p3_{source}"


def tuned_params(source):
    p = dict(C["params"])
    path = ml_path("tuning", f"{study(source)}.parquet")
    if os.path.exists(path):
        t = pd.read_parquet(path)
        t = t[(t["state"] == "COMPLETE") & (t["trial"] < N_TRIALS)]
        if len(t):
            p.update(json.loads(t.loc[t["value"].idxmax(), "params"]))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="v2")
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--trials", type=int, default=None)
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--variants", default="full")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    con = connect()
    tr, va = get(a.source, "train"), get(a.source, "valid")
    codes = tr["meta"]["codes"]
    print(f"train {len(tr['x']):,} anchors · valid {len(va['x']):,} · {tr['x'].shape[2]} features", flush=True)
    if a.tune:
        def objective(params, trial):
            full = {**C["params"], **params}
            _, v, ep = fit(tr, va, full, "full", con, codes, log=f"trial {trial.number}")
            trial.set_user_attr("best_epoch", ep)
            print(f"  trial {trial.number}: NDCG@20 (valid, unconditional) {v:.4f}  epoch {ep}  {params}", flush=True)
            return v
        st, _ = tune(study(a.source), objective, n_trials=a.trials, space=load_config("tuning")["p3"]["space"],
                     tag="" if a.trials is None else f"_smoke{a.trials}")
        print(f"best {st.best_value:.4f}  {st.best_params}", flush=True)
    if a.final:
        te = get(a.source, "test")
        params = tuned_params(a.source)
        for variant in a.variants.split(","):
            with Run(f"p3:{a.source}:{variant}", config={"umtr": C, "variant": variant, "source": a.source, "seed": a.seed}, params=params) as run:
                t0 = time.time()
                model, v, ep = fit(tr, va, params, variant, con, codes, seed=a.seed, log=variant)
                run.metrics.update({"valid_ndcg20": v, "best_epoch": ep, "train_sec": time.time() - t0,
                                    "params": int(sum(p.numel() for p in model.parameters()))})
                tag = (variant if a.source == "v2" else f"{a.source}_{variant}") + ("" if a.seed == 0 else f"_seed{a.seed}")
                os.makedirs(ml_path("models"), exist_ok=True)
                torch.save({"state": model.state_dict(), "params": params, "variant": variant}, ml_path("models", f"p3_{tag}.pt"))
                for split, d in (("valid", va), ("test", te)):
                    t1 = time.time()
                    sc = score(model, d, codes)
                    run.metrics[f"{split}_score_sec_per_1000"] = (time.time() - t1) / len(d["x"]) * 1000
                    sc.to_parquet(os.path.join(ML_DIR, "scores", f"p3_{tag}_{split}_d30.parquet"), index=False)
                print(f"  {variant}: valid NDCG@20 {v:.4f} (epoch {ep})", flush=True)


if __name__ == "__main__":
    sys.exit(main())
