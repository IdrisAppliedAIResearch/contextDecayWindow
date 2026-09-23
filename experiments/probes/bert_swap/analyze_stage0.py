"""BERT-SWAP Stage 0 analysis. Reads run artifacts only; prints dispositions."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
PLANTED = None  # loaded from probes.json


def load(rid):
    m = [json.loads(l) for l in (RUNS / f"{rid}.metrics.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    q3 = [json.loads(l) for l in (RUNS / f"{rid}.q3.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    return m, q3


def sign_test(w, l):
    n = w + l
    if n == 0:
        return 1.0
    k = min(w, l)
    p = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** (n - 1))
    return min(p, 1.0)


def main():
    pdata = json.loads((HERE / "probes.json").read_text(encoding="utf-8"))
    planted = [p for p in pdata["probes"] if p["kind"] == "planted"]
    controls = [p for p in pdata["probes"] if p["kind"] == "control"]

    for model, rid_t, rid_f in [("bert-small", "small_train", "small_notrain"),
                                ("bert-base-uncased", "base_train", "base_notrain")]:
        print(f"\n=== {model} ===")
        mt, qt = load(rid_t)
        mf, qf = load(rid_f)
        idx_t = {m["turn"]: m for m in mt}
        idx_f = {m["turn"]: m for m in mf}

        def acc(idx, pid, turn):
            m = idx.get(turn)
            return None if m is None else m["probes"][pid]["correct"]

        def mar(idx, pid, turn):
            m = idx.get(turn)
            return None if m is None else m["probes"][pid]["margin"]

        # Q1 table
        rows = []
        for p in planted:
            s = p["source_turn"]
            pid = p["fact_id"]
            pre_turns = [t for t in range(max(1, s - 5), s)]
            pre_f = [acc(idx_f, pid, t) for t in pre_turns]
            pre_t = [acc(idx_t, pid, t) for t in pre_turns]
            r = {
                "probe": pid, "src": s,
                "pre_frozen": round(sum(pre_f) / len(pre_f), 3),
                "pre_train": round(sum(pre_t) / len(pre_t), 3),
                "imm_t": acc(idx_t, pid, s), "imm_f": acc(idx_f, pid, s),
                "t10_t": acc(idx_t, pid, s + 10), "t10_f": acc(idx_f, pid, s + 10),
                "t50_t": acc(idx_t, pid, s + 50), "t50_f": acc(idx_f, pid, s + 50),
                "mar_imm_t": round(mar(idx_t, pid, s), 3),
                "mar_imm_f": round(mar(idx_f, pid, s), 3),
            }
            rows.append(r)
        for r in rows:
            print(" ", r)

        def mean(vals):
            v = [x for x in vals if x is not None]
            return sum(v) / len(v) if v else float("nan")

        imm_t = mean([1 if r["imm_t"] else 0 for r in rows])
        imm_f = mean([1 if r["imm_f"] else 0 for r in rows])
        pre_all = mean([r["pre_train"] for r in rows])
        t10 = mean([1 if r["t10_t"] else 0 for r in rows if r["t10_t"] is not None])
        t50 = mean([1 if r["t50_t"] else 0 for r in rows if r["t50_t"] is not None])
        net_imm = sum(1 for r in rows if r["imm_t"] and not r["imm_f"]) - \
            sum(1 for r in rows if r["imm_f"] and not r["imm_t"])
        mar_d = mean([r["mar_imm_t"] for r in rows]) - mean([r["mar_imm_f"] for r in rows])

        ctrl_f = mean([1 if acc(idx_f, p["fact_id"], 60) else 0 for p in controls])
        ctrl_t = mean([1 if acc(idx_t, p["fact_id"], 60) else 0 for p in controls])
        print(f"  Q1: imm_t={imm_t:.3f} imm_f={imm_f:.3f} pre={pre_all:.3f} "
              f"t+10={t10:.3f} t+50={t50:.3f} net_imm={net_imm} "
              f"margin_delta={mar_d:.3f} ctrl_f={ctrl_f:.3f} ctrl_t={ctrl_t:.3f}")

        g1 = ("WORKS" if imm_t >= 0.50 and pre_all <= 0.30 and net_imm >= 2 else
              "SIGNAL" if imm_t > 0.25 and mar_d >= 0.10 else "DEAD")
        print(f"  G1 disposition: {g1}")

        # Q2
        cs = [m["align_cos_mean"] for m in mt]
        buckets = [round(sum(cs[i:i + 20]) / len(cs[i:i + 20]), 6)
                   for i in range(0, len(cs), 20)]
        slice_drift = [m.get("slice_delta_ratio") for m in mt]
        fires = sum(1 for x in slice_drift if x and x > 1.2)
        print(f"  Q2: align_cos_mean buckets={buckets}")
        print(f"      gate fires (slice>1.2x): {fires}/"
              f"{sum(1 for x in slice_drift if x is not None)} turns")

        # Q3
        qk_t = {(q["checkpoint"], q["query_turn"]): q for q in qt}
        qk_f = {(q["checkpoint"], q["query_turn"]): q for q in qf}
        keys = sorted(set(qk_t) & set(qk_f))
        w = l = 0
        for k in keys:
            a, b = qk_t[k]["hit3_all"], qk_f[k]["hit3_all"]
            if a and not b:
                w += 1
            elif b and not a:
                l += 1
        p3 = sign_test(w, l)
        cp_net = {}
        for k in keys:
            a, b = qk_t[k]["hit3_all"], qk_f[k]["hit3_all"]
            cp = k[0]
            cp_net[cp] = cp_net.get(cp, 0) + (1 if a and not b else -1 if b and not a else 0)
        print(f"  Q3: items={len(keys)} hit3 net train-vs-frozen = {w}/{l} "
              f"(sign p={p3:.3f}) per-cp net={cp_net}")
        g3 = ("WORKS" if w - l >= 3 and all(v > -2 for v in cp_net.values()) else
              "SIGNAL" if w - l >= 1 else "NO_SIGNAL")
        print(f"  G3 disposition: {g3}")


if __name__ == "__main__":
    main()
