"""BERT-SWAP Stage 0b analysis: option 2 (retrain) vs frozen controls."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"


def load(rid):
    m = [json.loads(l) for l in (RUNS / f"{rid}.metrics.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    q3 = [json.loads(l) for l in (RUNS / f"{rid}.q3.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    meta = json.loads((RUNS / f"{rid}.meta.json").read_text(encoding="utf-8"))
    return m, q3, meta


def sign_test(w, l):
    n = w + l
    if n == 0:
        return 1.0
    k = min(w, l)
    return min(sum(math.comb(n, i) for i in range(k + 1)) / (2 ** (n - 1)), 1.0)


def main():
    pdata = json.loads((HERE / "probes.json").read_text(encoding="utf-8"))
    planted = [p for p in pdata["probes"] if p["kind"] == "planted"]
    controls = [p for p in pdata["probes"] if p["kind"] == "control"]

    for model, rid, rid_f in [
            ("bert-small (opt2)", "opt2_small", "small_notrain"),
            ("bert-base (opt2)", "opt2_base", "base_notrain")]:
        print(f"\n=== {model} ===")
        mt, qt, meta = load(rid)
        mf, qf, _ = load(rid_f)
        idx_t = {m["turn"]: m for m in mt}
        idx_f = {m["turn"]: m for m in mf}
        swaps = meta["swap_turns"]

        def get(idx, pid, turn):
            m = idx.get(turn)
            return (None, None) if m is None else (
                m["probes"][pid]["correct"], m["probes"][pid]["margin"])

        rows = []
        for p in planted:
            s, pid = p["source_turn"], p["fact_id"]
            imm = next((u for u in swaps if u >= s), None)
            if imm is None:
                continue
            pre = [get(idx_t, pid, t)[0] for t in range(max(1, s - 5), s)]
            c_t, m_t = get(idx_t, pid, imm)
            c_f, m_f = get(idx_f, pid, imm)
            rows.append({
                "probe": pid, "src": s, "imm_turn": imm,
                "pre": round(sum(pre) / len(pre), 3),
                "imm_t": c_t, "imm_f": c_f,
                "t10_t": get(idx_t, pid, imm + 10)[0],
                "t50_t": get(idx_t, pid, imm + 50)[0],
                "mar_t": m_t, "mar_f": m_f,
            })
        for r in rows:
            print(" ", r)

        def mean(v):
            v = [x for x in v if x is not None]
            return sum(v) / len(v) if v else float("nan")

        imm_t = mean([1 if r["imm_t"] else 0 for r in rows])
        imm_f = mean([1 if r["imm_f"] else 0 for r in rows])
        pre = mean([r["pre"] for r in rows])
        net = sum(1 for r in rows if r["imm_t"] and not r["imm_f"]) - \
            sum(1 for r in rows if r["imm_f"] and not r["imm_t"])
        mar_d = mean([r["mar_t"] for r in rows]) - mean([r["mar_f"] for r in rows])
        ctrl = mean([1 if get(idx_t, p["fact_id"], 60)[0] else 0 for p in controls])
        print(f"  G1b inputs: imm_t={imm_t:.3f} imm_f={imm_f:.3f} pre={pre:.3f} "
              f"net={net} margin_delta={mar_d:.3f} ctrl={ctrl:.3f}")
        g1b = ("WORKS" if imm_t >= 0.50 and pre <= 0.30 and net >= 2 else
               "SIGNAL" if imm_t > 0.25 and mar_d >= 0.10 else "DEAD")
        print(f"  G1b disposition: {g1b}")

        # Q2b + retrain cost + plant-margin gate
        sm = [m for m in mt if m.get("swap")]
        print("  Q2b align@swap:", [m["align_cos_mean"] for m in sm])
        ts = {}
        for l in (RUNS / f"{rid}.timing.jsonl").read_text().splitlines():
            t = json.loads(l)
            if t.get("retrain_s"):
                ts[t["turn"]] = t["retrain_s"]
        print("  retrain_s per swap:", [ts.get(u) for u in swaps])
        gates = [(m["turn"], m.get("swap_plant_margins")) for m in sm]
        fires = []
        prev = None
        for u, g in gates:
            if g and prev and prev[1]:
                common = set(g) & set(prev[1])
                if common:
                    a = sum(prev[1][k] for k in common) / len(common)
                    b = sum(g[k] for k in common) / len(common)
                    if b < a - 0.05:
                        fires.append(u)
            prev = (u, g)
        print(f"  plant-margin gate (-0.05 common-set rule) fires at: {fires}")

        # Q3b
        qk_t = {(q["checkpoint"], q["query_turn"]): q for q in qt}
        qk_f = {(q["checkpoint"], q["query_turn"]): q for q in qf}
        keys = sorted(set(qk_t) & set(qk_f))
        w = l = 0
        cp_net = {}
        for k in keys:
            a, b = qk_t[k]["hit3_all"], qk_f[k]["hit3_all"]
            d = 1 if (a and not b) else -1 if (b and not a) else 0
            w += d > 0
            l += d < 0
            cp_net[k[0]] = cp_net.get(k[0], 0) + d
        print(f"  Q3b: items={len(keys)} hit3 net = {w}/{l} "
              f"(p={sign_test(w, l):.3f}) per-cp={cp_net}")
        g3b = ("WORKS" if w - l >= 3 and all(v > -2 for v in cp_net.values())
               else "SIGNAL" if w - l >= 1 else "NO_SIGNAL")
        print(f"  G3b disposition: {g3b}")


if __name__ == "__main__":
    main()
