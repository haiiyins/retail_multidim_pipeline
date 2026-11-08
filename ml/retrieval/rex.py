"""REX — single-stage Repeat–Explore network: one model scores the whole universe of a country × cutoff, with no candidate stage and
no ranker, from the purchase sequence, the member's own history of each model, the dynamics of each model's popularity and the
member's web attention. A t31 row next to the two-stage pipeline (ml/baselines/nbr.py --source rex).

  logit_i(t) = u(t) · v_i                                   explore: basket transformer + RFM + month  ·  model + department + price
             + pop(f_i(t))                                  popularity: buyers of i in the 7 / 30 / 90 days before t, trend, same
                                                            30 days a year earlier; an MLP shared by every model
             + 1[bought i before t] · rep(φ_i(t), u, v_i)   repeat: purchase days, recency, age, decayed counts of the member on i,
                                                            the repurchase rate and cycle of i before the cutoff
             + 1[web attention to i] · web(ψ_i(t), u, v_i)  web: product views / cart events of the member on i in the
                                                            web_window_days before t, by the day the attribution is known

Training examples: reference days t drawn uniformly in the Δ days before one of the member's purchase days (not her first), so the
day of the next purchase within (t, t + Δ] is spread as at a weekly anchor; t + Δ < cutoff (pit.last_fit_anchor); refs_per_epoch
per member, resampled every epoch. Target: every universe model bought in (t, t + Δ], repeats included; loss: softmax over the
universe averaged over the targets. Every input is dated strictly before t: purchases (Events.history), web events whose
attribution is known before t (max(event_ts, identity_verified_ts) as a local date, read with an 8-hour shift so a late-evening
UTC event never lands before its local day), popularity counts of days < t; the repeat statistics of a model come from purchases
before the cutoff. d, blocks, dropout, lr are tuned on valid NDCG@20 (tuning.yml rex).

REX v2 (source rex2) adds the price dimension and a richer repeat channel:
  pop(f_i(t), price_i(t − 1))      price of i in force on t − 1 (median over its SKUs of the national interval, a temporary promotion
                                   first): has a price, log price standardised per country, promotion depth, share of SKUs on a
                                   temporary promotion, log price against its 90-day maximum
  + rel(u)[bucket(log p_i − log p̄_member)]   the member's price affinity: buckets of the item's log price against the mean log unit
                                   price she paid before t, scored by a projection of u
  rep(φ_i, φ2_i, price_i, u, v_i)  φ2: her own repeat share (shrunk), recency against her own cycle on i
Stock is left out: the only exported stock table covers spare parts (gld_fs_model_country, issue #21).
Usage: python ml/baselines/nbr.py --source rex|rex2 --tune --build"""
import copy, datetime as dt, os, queue, sys, threading
import numpy as np, pandas as pd, torch, torch.nn as nn, torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, ml_path
from ml.common.levels import group_map
from ml.common.registry import config_hash
from ml.retrieval.base import CFG, DAY_BITS, DEVICE, EPOCH, Source, Universe, day_num, item_attributes
from ml.retrieval.neural import (GAP_BUCKETS, OFFSET, OOV, PAD, Encoder, basket_windows, gap_buckets, months, seed_everything,
                                 train)
from ml.retrieval.two_tower import pick_refs, rfm

C = CFG["rex"]
DELTA = CFG["delta"]
WEB_VIEW = ("product_page_viewed", "product_size_selected")
WEB_CART = ("product_added_to_cart", "cart_viewed", "checkout_commenced")
N_POP, N_REP, N_WEB = 7, 10, 5
N_PRICE, N_REP2, REL_BUCKETS, REL_WIDTH = 5, 2, 12, 0.25
PRICE_FROM = "2022-01-01"
SUB = 2048   # anchors per scoring block


class WebEvents:
    """Web attention of one country, one row per member × model × known day, as integer arrays sorted by (member, day); member and
    model indices are those of the country's Events (models never bought in the country are dropped)."""

    def __init__(self, con, ev):
        names = ", ".join(f"'{e}'" for e in WEB_VIEW + WEB_CART)
        view = ", ".join(f"'{e}'" for e in WEB_VIEW)
        r = con.execute(f"""
            SELECT member_id, model_code,
                   date_diff('day', DATE '1970-01-01', CAST(GREATEST(event_ts_utc, identity_verified_ts) + INTERVAL 8 HOUR AS DATE))::INT AS day,
                   COUNT(DISTINCT event_id) FILTER (WHERE event_name IN ({view}))::INT AS views,
                   COUNT(DISTINCT event_id) FILTER (WHERE event_name NOT IN ({view}))::INT AS carts
            FROM lh.gold.gld_web_stitched
            WHERE country_code = ? AND model_code IS NOT NULL AND event_name IN ({names})
            GROUP BY ALL""", [ev.country]).df()
        m = ev.member_index(r["member_id"])
        i = ev.item_index(r["model_code"])
        keep = (m >= 0) & (i >= 0)
        m, i = m[keep], i[keep]
        day, views, carts = (r[c].to_numpy()[keep] for c in ("day", "views", "carts"))
        order = np.lexsort((day, m))
        self.m, self.i, self.day = m[order], i[order].astype(np.int64), day[order].astype(np.int64)
        self.views, self.carts = views[order].astype(np.float32), carts[order].astype(np.float32)
        self.key = self.m * DAY_BITS + self.day

    def window(self, m, t, days):
        """(row, index) of the rows of member m[row] known in [t − days, t)."""
        lo = np.searchsorted(self.key, m * DAY_BITS + t - days)
        hi = np.searchsorted(self.key, m * DAY_BITS + t)
        n = np.where(m >= 0, hi - lo, 0)
        row = np.repeat(np.arange(len(m)), n)
        idx = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n) + np.repeat(lo, n)
        return row, idx


class Prices:
    """Daily national price of every model of a country's Events from PRICE_FROM to the last sales day: the SKU interval valid on
    the day (temporary promotion first, then the lowest price), median over the model's SKUs. Arrays (days, models): log price
    (NaN without a valid interval), promotion depth, temporary-promotion share. Cached under data/ml/rex/."""

    def __init__(self, con, ev):
        path = ml_path("rex", f"price_{ev.country}.parquet")
        last = (EPOCH + dt.timedelta(days=int(ev.day.max()))).isoformat()
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            con.execute("SET memory_limit='100GB'")
            con.execute(f"""COPY (
                WITH m AS (SELECT DISTINCT model_code FROM lh.silver.slv_fact_sales_line WHERE country_code = '{ev.country}' AND model_code IS NOT NULL),
                p AS (SELECT dm.model_code, p.item_code, p.eff_start, p.eff_end, p.price, p.ref_price, p.is_temp_promo
                      FROM lh.silver.slv_price_sku_interval p
                      JOIN (SELECT DISTINCT item_code, model_code FROM lh.silver.slv_dim_model) dm USING (item_code) JOIN m USING (model_code)
                      WHERE p.country_code = '{ev.country}' AND p.price_scope = 'NATIONAL'
                        AND p.eff_end >= DATE '{PRICE_FROM}' AND p.eff_start <= DATE '{last}'),
                d AS (SELECT CAST(range AS DATE) AS d FROM range(DATE '{PRICE_FROM}', DATE '{last}' + 1, INTERVAL 1 DAY)),
                sku AS (SELECT p.model_code, d.d, p.price, p.ref_price, p.is_temp_promo FROM p JOIN d ON d.d BETWEEN p.eff_start AND p.eff_end
                        QUALIFY ROW_NUMBER() OVER (PARTITION BY p.item_code, d.d ORDER BY p.is_temp_promo DESC, p.price ASC, p.eff_start DESC) = 1)
                SELECT model_code, date_diff('day', DATE '1970-01-01', d)::INT AS day, MEDIAN(price) AS price,
                       MEDIAN(ref_price) AS ref_price, AVG(is_temp_promo::INT) AS temp
                FROM sku GROUP BY ALL) TO '{path}' (FORMAT parquet)""")
        r = pd.read_parquet(path)
        self.day0 = day_num(PRICE_FROM)
        n_days = int(ev.day.max()) - self.day0 + 1
        assert ev.level == "model", "national prices are per model"
        i = ev.item_index(r["model_code"])
        k = (i >= 0) & (r["day"].to_numpy() >= self.day0) & (r["day"].to_numpy() < self.day0 + n_days)
        i, d = i[k], r["day"].to_numpy()[k] - self.day0
        self.log_price = np.full((n_days, len(ev.items)), np.nan, np.float32)
        self.depth = np.zeros((n_days, len(ev.items)), np.float32)
        self.temp = np.zeros((n_days, len(ev.items)), np.float32)
        price, ref = r["price"].to_numpy()[k], r["ref_price"].to_numpy()[k]
        self.log_price[d, i] = np.log(price)
        self.depth[d, i] = np.nan_to_num(np.clip(1 - price / ref, 0, 0.9))
        self.temp[d, i] = r["temp"].to_numpy()[k]

    def features(self, items):
        """(days, len(items), N_PRICE) float32 and (days, len(items)) log price for the given model indices."""
        lp = self.log_price[:, items]
        has = ~np.isnan(lp)
        mu, sd = np.nanmean(lp), np.nanstd(lp) + 1e-6
        peak = pd.DataFrame(lp).rolling(91, min_periods=1).max().to_numpy(np.float32)
        f = np.stack([has, np.where(has, (lp - mu) / sd, 0), self.depth[:, items], self.temp[:, items],
                      np.where(has, lp - peak, 0)], 2).astype(np.float32)
        return f, lp


def item_repeat_stats(ev, uni, cutoff):
    """Per universe model, from purchases before the cutoff: share of its buyers with two or more purchase days (shrunk to the
    universe mean with 20 pseudo-buyers) and log1p of the mean days between two purchase days of the same buyer (universe median
    when no buyer came back)."""
    sel = ev.before(cutoff)
    u = uni.pos[ev.i[sel]]
    k = u >= 0
    key = ev.m[sel][k].astype(np.int64) * uni.size + u[k]
    day = ev.day[sel][k]
    pk, inv = np.unique(key, return_inverse=True)
    n = np.bincount(inv)
    first = np.full(len(pk), np.iinfo(np.int64).max)
    last = np.full(len(pk), np.iinfo(np.int64).min)
    np.minimum.at(first, inv, day)
    np.maximum.at(last, inv, day)
    item = pk % uni.size
    buyers = np.bincount(item, minlength=uni.size)
    again = np.bincount(item, weights=n >= 2, minlength=uni.size)
    prior = again.sum() / max(buyers.sum(), 1)
    rate = (again + 20 * prior) / (buyers + 20)
    rep = n >= 2
    gap = np.bincount(item[rep], weights=np.log1p((last - first)[rep] / (n[rep] - 1)), minlength=uni.size)
    cnt = np.bincount(item[rep], minlength=uni.size)
    log_gap = np.where(cnt > 0, gap / np.maximum(cnt, 1), np.median(gap[cnt > 0] / cnt[cnt > 0]) if (cnt > 0).any() else 4.0)
    return np.stack([rate, log_gap], 1).astype(np.float32)


def daily_buyers(ev, uni, rows=None):
    """(days + 1, universe) cumulative buyers per model: row k = buyers on days < day0 + k, and day0. rows: the purchase rows
    counted (default all)."""
    u = uni.pos[ev.i]
    k = u >= 0
    if rows is not None:
        k &= rows
    day0 = int(ev.day.min())
    n_days = int(ev.day.max()) - day0 + 2
    d = np.zeros((n_days, uni.size), np.float32)
    np.add.at(d, (ev.day[k] - day0 + 1, u[k]), 1)
    return torch.from_numpy(np.cumsum(d, 0)), day0


def pop_features(cum, day0, t):
    """(len(t), universe, N_POP) popularity of every model at days t from counts of days < t."""
    def buyers(lo, hi):   # days in [t - lo, t - hi)
        a = torch.as_tensor(np.clip(t - lo - day0, 0, cum.shape[0] - 1), device=cum.device)
        b = torch.as_tensor(np.clip(t - hi - day0, 0, cum.shape[0] - 1), device=cum.device)
        return cum[b] - cum[a]

    b7, b30, b90 = buyers(7, 0), buyers(30, 0), buyers(90, 0)
    ly, ly_next = buyers(365 + 30, 365), buyers(365, 365 - 30)
    tot = b30.sum(1, keepdim=True).expand_as(b30)
    f = torch.stack([b7, b30, b90, ly, ly_next], 2).log1p() / 5
    trend = (torch.log1p(b7 * 30 / 7) - torch.log1p(b30)).unsqueeze(2)
    share = (torch.log1p(b30) - torch.log1p(tot)).unsqueeze(2) / 5
    return torch.cat([f, trend, share], 2)


def price_features(f, lp, day0, t):
    """Price inputs of every model at days t, read on t − 1: {"f": (len(t), universe, N_PRICE), "lp": (len(t), universe)}; days
    before the price table get no price."""
    k = t - 1 - day0
    idx = torch.as_tensor(np.clip(k, 0, f.shape[0] - 1), device=f.device)
    known = torch.as_tensor(k >= 0, device=f.device)
    return {"f": f[idx] * known[:, None, None], "lp": torch.where(known[:, None], lp[idx], torch.nan)}


class Batch:
    """Inputs of a set of members m at days t: basket windows, RFM, month, the repeat pairs (member's universe models bought before
    t) with φ, the web pairs (models with web attention in the window) with ψ, and the unique days for the popularity features."""

    def __init__(self, ev, web, uni, stats, m, t, row=None, idx=None, country=None):
        """country: country index of each row (pooled REX): the popularity days become (country, day) keys."""
        n = len(m)
        self.country = np.zeros(n, np.int64) if country is None else np.asarray(country, np.int64)
        if row is None:
            row, idx = ev.history(m, t)
        self.n = n
        self.x, self.days, self.lens = basket_windows(ev, uni, row, idx, n, C["max_len"], C["width"])
        self.x[self.lens == 0, 0, 0] = OOV
        self.lens = np.maximum(self.lens, 1)
        self.t = t
        self.rfm = rfm(ev, row, idx, t, n)
        self.month = months(t)
        u = uni.pos[ev.i[idx]]
        k = u >= 0
        key = row[k].astype(np.int64) * uni.size + u[k]
        age = (t[row] - ev.day[idx])[k].astype(np.float64)
        pk, inv = np.unique(key, return_inverse=True)
        cnt = np.bincount(inv)
        last = np.full(len(pk), np.inf)
        first = np.zeros(len(pk))
        np.minimum.at(last, inv, age)
        np.maximum.at(first, inv, age)
        d30 = np.bincount(inv, weights=np.exp(-age / 30))
        d180 = np.bincount(inv, weights=np.exp(-age / 180))
        self.rep_row, self.rep_item = (pk // uni.size).astype(np.int64), (pk % uni.size).astype(np.int64)
        st = stats[self.rep_item]
        log_last = np.log1p(last)
        self.phi = np.stack([np.log1p(cnt), log_last / 5, np.log1p(first) / 5, np.log1p(d30), np.log1p(d180),
                             st[:, 0], st[:, 1] / 5, (log_last - st[:, 1]) / 5, cnt >= 2,
                             np.log1p(np.bincount(self.rep_row, minlength=n))[self.rep_row] / 5], 1).astype(np.float32)
        rows, again = np.bincount(self.rep_row, weights=cnt, minlength=n), np.bincount(self.rep_row, weights=cnt - 1, minlength=n)
        rho = (again + 20 * 0.2) / (rows + 20)
        own = np.where(cnt >= 2, (first - last) / np.maximum(cnt - 1, 1), np.nan)
        self.phi2 = np.stack([rho[self.rep_row] * 5, np.where(cnt >= 2, (log_last - np.log1p(own)), 0) / 2], 1).astype(np.float32)
        paid = ev.price[idx] if ev.price is not None else np.zeros(len(idx), np.float32)
        ok = paid > 0
        s = np.bincount(row[ok], weights=np.log(paid[ok]), minlength=n)
        c = np.bincount(row[ok], minlength=n)
        self.member_lp = np.where(c > 0, s / np.maximum(c, 1), np.nan).astype(np.float32)
        wr, wi = web.window(m, t, C["web_window_days"])
        wu = uni.pos[web.i[wi]]
        k = wu >= 0
        wr, wi, wu = wr[k], wi[k], wu[k]
        wk, winv = np.unique(wr.astype(np.int64) * uni.size + wu, return_inverse=True)
        wage = (t[wr] - web.day[wi]).astype(np.float64)
        views = np.bincount(winv, weights=web.views[wi], minlength=len(wk))
        carts = np.bincount(winv, weights=web.carts[wi], minlength=len(wk))
        v7 = np.bincount(winv, weights=web.views[wi] * (wage <= 7), minlength=len(wk))
        wlast = np.full(len(wk), np.inf)
        np.minimum.at(wlast, winv, wage)
        self.web_row, self.web_item = (wk // uni.size).astype(np.int64), (wk % uni.size).astype(np.int64)
        bought = np.isin(wk, pk)
        self.psi = np.stack([np.log1p(views), np.log1p(v7), np.log1p(carts), np.log1p(wlast) / 3, bought], 1).astype(np.float32)
        self.t_uni, self.t_inv = np.unique(t if country is None else self.country * DAY_BITS + t, return_inverse=True)

    def tensors(self):
        dev = DEVICE
        f = lambda a, dt=None: torch.as_tensor(a, dtype=dt, device=dev)
        return {"x": f(self.x.astype(np.int64)), "days": f(self.days), "lens": f(self.lens), "t": f(self.t),
                "rfm": self.rfm.to(dev), "month": f(self.month), "rep_row": f(self.rep_row), "rep_item": f(self.rep_item),
                "phi": f(self.phi), "phi2": f(self.phi2), "member_lp": f(self.member_lp), "web_row": f(self.web_row),
                "web_item": f(self.web_item), "psi": f(self.psi), "t_inv": f(self.t_inv), "country": f(self.country)}


def mlp(i, h, o, dropout):
    return nn.Sequential(nn.Linear(i, h), nn.GELU(), nn.Dropout(dropout), nn.Linear(h, o))


class REXNet(nn.Module):
    def __init__(self, size, item_dept, item_price, d, blocks, dropout, drop=(), item_lp=None, item_hier=(), n_countries=1):
        """drop: channels left out: web, pop, rep, seq (member = RFM + month, no basket transformer), and the v2 inputs price
        (price features, price affinity) and rep2 (φ2); REX v1 drops both. item_lp: mean log unit price paid for each universe model
        before the cutoff, the fallback of the affinity when the model has no price interval. item_hier: per universe model, its
        group index at each extra product level (variant hier), embedded into the item tower. n_countries > 1 (pooled REX): a
        country embedding added to the month embedding of the member."""
        super().__init__()
        self.country = nn.Embedding(n_countries, d) if n_countries > 1 else None
        self.hier = nn.ModuleList(nn.Embedding(int(h.max()) + 1, d) for h in item_hier)
        for j, h in enumerate(item_hier):
            self.register_buffer(f"item_hier{j}", torch.as_tensor(h))
        self.drop = set(drop)
        self.use_price, self.use_rep2 = "price" not in self.drop, "rep2" not in self.drop
        self.enc = Encoder(size + OFFSET, d, blocks, C["heads"], dropout, C["max_len"], causal=True)
        self.gap, self.age = nn.Embedding(GAP_BUCKETS, d), nn.Embedding(GAP_BUCKETS, d)
        self.rfm, self.month = nn.Linear(3, d), nn.Embedding(12, d)
        self.user = mlp(3 * d, d, d, dropout)
        self.dept = nn.Embedding(int(item_dept.max()) + 1, d)
        self.price = nn.Embedding(C["price_buckets"], d)
        self.item = mlp((3 + len(item_hier)) * d, d, d, dropout)
        n_price = N_PRICE if self.use_price else 0
        self.pop = mlp(N_POP + n_price, d, 1, 0.0)
        self.rep = mlp(N_REP + (N_REP2 if self.use_rep2 else 0) + n_price + 2 * d, d, 1, dropout)
        self.web = mlp(N_WEB + 2 * d, d, 1, dropout)
        if self.use_price:
            self.rel = nn.Linear(d, REL_BUCKETS)
            nn.init.zeros_(self.rel.weight)
            nn.init.zeros_(self.rel.bias)
            self.register_buffer("item_lp", torch.as_tensor(np.full(size, np.nan) if item_lp is None else item_lp, dtype=torch.float32))
        for e in (self.gap, self.age):
            nn.init.normal_(e.weight, std=0.02)
        self.register_buffer("item_dept", torch.as_tensor(item_dept))
        self.register_buffer("item_price", torch.as_tensor(item_price))
        self.scale = d ** -0.5

    def items(self):
        e = self.enc.emb.weight[OFFSET:]
        hier = [emb(getattr(self, f"item_hier{j}")) for j, emb in enumerate(self.hier)]
        return self.item(torch.cat([e, self.dept(self.item_dept), self.price(self.item_price)] + hier, 1))

    def users(self, b):
        x, days, lens = b["x"], b["days"], b["lens"]
        when = self.month(b["month"]) + (self.country(b["country"]) if self.country is not None else 0)
        if "seq" in self.drop:
            ctx = [self.rfm(b["rfm"]), when]
            return self.user(torch.cat([torch.zeros_like(ctx[0])] + ctx, 1))
        e = self.enc.emb(x)
        inp = e.sum(2) / (x != PAD).sum(2, keepdim=True).clamp(min=1)
        steps = torch.arange(x.shape[1], device=x.device)[None]
        age = torch.ceil(torch.log2((b["t"][:, None] - days).clamp(min=0).float() + 1)).long().clamp(1, GAP_BUCKETS - 1)
        age = torch.where(steps < lens[:, None], age, 0)
        h = self.enc(None, lens, inp + self.gap(gap_buckets(days, lens)) + self.age(age))
        last = h[torch.arange(len(lens), device=x.device), lens - 1]
        return self.user(torch.cat([last, self.rfm(b["rfm"]), when], 1))

    def forward(self, b, pop, price=None):
        """b: Batch.tensors(); pop: (unique days, universe, N_POP); price: price_features() at the same unique days (v2).
        Returns (n, universe) logits."""
        u, v = self.users(b), self.items()
        rep_f = [b["phi"]]
        if self.use_rep2:
            rep_f.append(b["phi2"])
        if self.use_price:
            rep_f.append(price["f"][b["t_inv"][b["rep_row"]], b["rep_item"]])
            pop = torch.cat([pop, price["f"]], 2)
        extra = [net(torch.cat([f, u[row], v[item]], 1)).squeeze(-1) if len(row) and ch not in self.drop else None
                 for ch, row, item, f, net in (("rep", b["rep_row"], b["rep_item"], torch.cat(rep_f, 1), self.rep),
                                               ("web", b["web_row"], b["web_item"], b["psi"], self.web))]
        p = self.pop(pop).squeeze(-1)
        rel = self.rel(u) if self.use_price else None
        with torch.autocast("cuda", enabled=False):   # bf16 logits tie too often over 5 000 models
            logits = (u.float() @ v.float().T) * self.scale
            if "pop" not in self.drop:
                logits = logits + p.float()[b["t_inv"]]
            if rel is not None:
                lp = price["lp"][b["t_inv"]]
                lp = torch.where(torch.isnan(lp), self.item_lp[None, :].expand_as(lp), lp)
                diff = torch.nan_to_num(lp - b["member_lp"][:, None], nan=0.0)
                bucket = (torch.floor(diff / REL_WIDTH) + REL_BUCKETS // 2).long().clamp(0, REL_BUCKETS - 1)
                s = rel.float().gather(1, bucket)
                logits = logits + torch.where(torch.isnan(b["member_lp"])[:, None], 0.0, s)
            for (row, item), s in zip(((b["rep_row"], b["rep_item"]), (b["web_row"], b["web_item"])), extra):
                if s is not None:
                    logits = logits.index_put((row, item), s.float(), accumulate=True)
        return logits


def prefetch(gen, depth=4):
    """Run a batch generator in a background thread, depth batches ahead (numpy batch building overlaps the GPU step)."""
    q, done = queue.Queue(depth), object()

    def work():
        try:
            for item in gen:
                q.put(item)
        finally:
            q.put(done)

    threading.Thread(target=work, daemon=True).start()
    while (item := q.get()) is not done:
        yield item


def full_target_loss(logits, target):
    logp = F.log_softmax(logits.float(), dim=1)
    t = target.float()
    return -(torch.where(target, logp, 0.0).sum(1) / t.sum(1)).mean()   # masked logits are −inf off the targets


def basket_days(ev, cutoff):
    """Purchase days of each member before the cutoff, except her first: (member, day, first purchase day)."""
    bk = np.unique(ev.key[ev.before(cutoff)])
    bm, bd = bk // DAY_BITS, (bk % DAY_BITS).astype(np.int64)
    first = np.r_[True, bm[1:] != bm[:-1]]
    fd = bd[first][np.cumsum(first) - 1]
    return bm[~first], bd[~first], fd[~first]


def targets(ev, uni, m, t):
    """(row, universe item) of every universe model bought in (t, t + Δ] by members m."""
    lo = np.searchsorted(ev.key, m * DAY_BITS + t + 1)
    hi = np.searchsorted(ev.key, m * DAY_BITS + t + DELTA + 1)
    n = hi - lo
    row = np.repeat(np.arange(len(m)), n)
    idx = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n) + np.repeat(lo, n)
    u = uni.pos[ev.i[idx]]
    return row[u >= 0], u[u >= 0]


class REX(Source):
    """base rex (v1: no price, no φ2) or rex2 (v2); variant = full or an ablation (VARIANTS), named <base>_<variant>."""
    VARIANTS = {"full": (), "noweb": ("web",), "nopop": ("pop",), "norep": ("rep",), "noseq": ("seq",), "noprice": ("price",),
                "hier": ()}
    V1 = ("price", "rep2")
    HIER = ("nature", "family")   # product levels embedded by the hier variant

    def __init__(self, variant="full", base="rex", level="model"):
        self._web, self._prices, self.variant, self.base, self.level = {}, {}, variant, base, level
        self.drop = self.VARIANTS[variant] + (self.V1 if base == "rex" else ())
        self.name = base if variant == "full" else f"{base}_{variant}"
        if level != "model":
            self.name = f"{base}_{level}" + ("" if variant == "full" else f"_{variant}")
        self.version = 1 if base == "rex" else 2
        self.epochs = CFG[base].get("epochs", C["epochs"])

    def web(self, ev):
        key = (ev.country, ev.level)
        if key not in self._web:
            con = connect(threads=16)
            self._web[key] = WebEvents(con, ev)
            con.close()
        return self._web[key]

    def prices(self, ev):
        if ev.country not in self._prices:
            con = connect(threads=16)
            self._prices[ev.country] = Prices(con, ev)
            con.close()
        return self._prices[ev.country]

    def prepare(self, ev, uni, cutoff):
        bm, bd, fd = basket_days(ev, cutoff)
        c = day_num(cutoff)
        lo, hi = np.maximum(bd - DELTA, fd + 1), np.minimum(bd - 1, c - DELTA - 1)
        ok = lo <= hi
        dept, price, _ = item_attributes(ev, uni, cutoff, C["price_buckets"])
        cum, day0 = daily_buyers(ev, uni)
        prep = {"m": bm[ok], "lo": lo[ok], "hi": hi[ok], "dept": dept, "price": price, "stats": item_repeat_stats(ev, uni, cutoff),
                "cum": cum, "day0": day0, "hier": ()}
        if self.variant == "hier":
            con = connect(threads=16)
            g = pd.read_parquet(group_map(con), columns=["model_code", *self.HIER]).set_index("model_code")
            con.close()
            codes = g.reindex(ev.items[uni.items])
            prep["hier"] = tuple(np.unique(codes[lv].fillna("?").to_numpy(), return_inverse=True)[1].astype(np.int64)
                                 for lv in self.HIER)
        if "price" not in self.drop:
            pt = self.prices(ev)
            f, lp = pt.features(uni.items)
            sel = ev.before(cutoff) & (ev.price > 0)
            u = uni.pos[ev.i[sel]]
            k = u >= 0
            s = np.bincount(u[k], weights=np.log(ev.price[sel][k]), minlength=uni.size)
            n = np.bincount(u[k], minlength=uni.size)
            prep.update(price_f=torch.from_numpy(f), price_lp=torch.from_numpy(lp), price_day0=pt.day0,
                        item_lp=np.where(n > 0, s / np.maximum(n, 1), np.nan).astype(np.float32))
        return prep

    def price_inputs(self, model, t_uni):
        return price_features(model.price_f, model.price_lp, model.price_day0, t_uni) if model.price_f is not None else None

    # one country per model; REXPool overrides these four
    n_countries = 1

    def countries_of(self, ev, m):
        return None

    def pop(self, cum, day0, b):
        return pop_features(cum, day0, b.t_uni)

    def allowed(self, model, country):
        """(n, universe) bool of the items a row may score, None = every universe item."""
        return None

    def fit(self, prep, params, ev, uni, cutoff):
        rng = seed_everything(self.seed)
        web = self.web(ev)
        cum = prep["cum"].to(DEVICE)
        model = REXNet(uni.size, prep["dept"], prep["price"], params["d"], params["blocks"], params["dropout"], self.drop,
                       prep.get("item_lp"), prep.get("hier", ()), self.n_countries).to(DEVICE)
        model.country_items = prep["country_items"].to(DEVICE) if "country_items" in prep else None
        model.price_f = prep["price_f"].to(DEVICE) if "price_f" in prep else None
        model.price_lp = prep["price_lp"].to(DEVICE) if "price_lp" in prep else None
        model.price_day0 = prep.get("price_day0")
        bs = C["batch"]

        def batches(ep):
            return prefetch(build(pick_refs(rng, prep["m"], C["refs_per_epoch"])))

        def build(pick):
            for s in range(0, len(pick), bs):
                i = pick[s:s + bs]
                m = prep["m"][i]
                t = rng.integers(prep["lo"][i], prep["hi"][i] + 1)
                country = self.countries_of(ev, m)
                b = Batch(ev, web, uni, prep["stats"], m, t, country=country)
                trow, titem = targets(ev, uni, m, t)
                tgt = torch.zeros(len(i), uni.size, dtype=torch.bool, device=DEVICE)
                tgt[torch.from_numpy(trow).to(DEVICE), torch.from_numpy(titem).to(DEVICE)] = True
                ok = self.allowed(model, country)
                if ok is not None:
                    tgt &= ok
                has = tgt.any(1)
                yield b.tensors(), self.pop(cum, prep["day0"], b), self.price_inputs(model, b.t_uni), tgt, has, ok

        def loss_fn(model, batch):
            b, pop, price, tgt, has, ok = batch
            logits = model(b, pop, price)
            if ok is not None:
                logits = logits.masked_fill(~ok, -torch.inf)
            return full_target_loss(logits[has], tgt[has])

        model = train(model, batches, loss_fn, self.epochs, params["lr"], log=f"{self.name} {ev.country} {str(cutoff)[:10]}")
        model.cum, model.day0, model.stats, model.web_events = cum, prep["day0"], prep["stats"], web
        return model

    def scores(self, model, q):
        m = np.full(q.n, -1, np.int64)
        has = np.bincount(q.all_row, minlength=q.n) > 0
        m[has] = q.ev.m[q.all_idx][np.searchsorted(q.all_row, np.flatnonzero(has))]
        out = []
        for s in range(0, q.n, SUB):
            e = min(s + SUB, q.n)
            lo, hi = np.searchsorted(q.all_row, [s, e])
            country = self.countries_of(q.ev, m[s:e])
            b = Batch(q.ev, model.web_events, q.uni, model.stats, m[s:e], q.day[s:e].astype(np.int64),
                      q.all_row[lo:hi] - s, q.all_idx[lo:hi], country=country)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=DEVICE == "cuda"):
                sc = model(b.tensors(), self.pop(model.cum, model.day0, b), self.price_inputs(model, b.t_uni)).float()
            ok = self.allowed(model, country)
            out.append(sc if ok is None else sc.masked_fill(~ok, -torch.inf))
        return torch.cat(out)


class REXPool(REX):
    """REX fitted once per cutoff on the purchases of every country (Events.pool): one network, the models shared by name, a
    country embedding in the member tower; each country keeps its own universe (top universe.size models by its buyers, the
    softmax and the scores masked to it) and its own popularity counts. Scores the anchors of each country through
    Events.view(country). Prices are not used (v1)."""

    def __init__(self):
        super().__init__("full", "rex")
        self.name = "rex_pool"
        self._memo = {}

    @property
    def n_countries(self):
        return len(self._countries)

    def universe(self, ev, cutoff):
        key = ("uni", cutoff)
        if key not in self._memo:
            self._countries = ev.countries
            own = [Universe(_restrict(ev, c), cutoff).items for c in range(len(ev.countries))]
            uni = Universe.__new__(Universe)
            uni.items = np.unique(np.concatenate(own))
            uni.size = len(uni.items)
            uni.pos = np.full(len(ev.items), -1, np.int64)
            uni.pos[uni.items] = np.arange(uni.size)
            mask = np.zeros((len(own), uni.size), bool)
            for c, it in enumerate(own):
                mask[c, uni.pos[it]] = True
            uni.country_items = torch.from_numpy(mask)
            self._memo[key] = uni
        return self._memo[key]

    def prepare(self, ev, uni, cutoff):
        key = ("prep", cutoff)
        if key not in self._memo:
            prep = super().prepare(ev, uni, cutoff)
            rows = ev.member_country[ev.m]
            cums = [daily_buyers(ev, uni, rows == c)[0] for c in range(len(ev.countries))]
            prep["cum"], prep["country_items"] = torch.stack(cums), uni.country_items
            self._memo[key] = prep
        return self._memo[key]

    def fit(self, prep, params, ev, uni, cutoff):
        key = ("fit", cutoff, config_hash(params), self.seed)
        if key not in self._memo:
            for old in [k for k in self._memo if k[0] == "fit" and k[2:] != key[2:]]:   # another tuning trial: free the GPU
                del self._memo[old]
            torch.cuda.empty_cache()
            self._memo[key] = super().fit(prep, params, ev, uni, cutoff)
        return self._memo[key]

    def web(self, ev):
        if "web" not in self._memo:
            con = connect(threads=16)
            parts = [WebEvents(con, ev.view(c)) for c in ev.countries]
            con.close()
            w = WebEvents.__new__(WebEvents)
            m, i, day = (np.concatenate([getattr(p, a) for p in parts]) for a in ("m", "i", "day"))
            views, carts = (np.concatenate([getattr(p, a) for p in parts]) for a in ("views", "carts"))
            order = np.lexsort((day, m))
            w.m, w.i, w.day, w.views, w.carts = m[order], i[order], day[order], views[order], carts[order]
            w.key = w.m * DAY_BITS + w.day
            self._memo["web"] = w
        return self._memo["web"]

    def countries_of(self, ev, m):
        own = ev.countries.index(ev.country) if ev.country in ev.countries else 0
        return np.where(m >= 0, ev.member_country[np.maximum(m, 0)], own)

    def pop(self, cum, day0, b):
        c, t = b.t_uni // DAY_BITS, b.t_uni % DAY_BITS
        return torch.cat([pop_features(cum[k], day0, t[c == k]) for k in np.unique(c)])

    def allowed(self, model, country):
        return model.country_items[torch.as_tensor(country, device=DEVICE)]


def _restrict(ev, c):
    """The pooled events reduced to the purchases of country c (for its universe)."""
    keep = ev.member_country[ev.m] == c
    r = copy.copy(ev)
    r.m, r.i, r.day, r.ts = ev.m[keep], ev.i[keep], ev.day[keep], ev.ts[keep]
    r.key = r.m.astype(np.int64) * DAY_BITS + r.day
    return r


if __name__ == "__main__":
    from ml.retrieval.base import main
    sys.exit(main(REX()))
