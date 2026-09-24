"""ENTITY-LINKING PREFLIGHT v2 (decisive instrument; EXPLORATORY, zero model calls).
WIN test: for LoCoMo gold evidence PAIRS, is there a pair that entity-linking bridges but NEITHER
dense cosine NOR lexical(BM25-style discriminative token) reaches? Enriched on gold vs random pairs
or it is not signal. Speaker-subtracted + DF(discriminative)-filtered tokens/entities. LoCoMo SPENT ->
descriptive only.
"""
import json, sqlite3, os, re, html, random
from collections import defaultdict, Counter
import numpy as np

REPO = r"C:\Users\muzaf\PycharmProjects\contextDecayWindow"
LOCO = r"C:\Users\muzaf\Downloads\locomo10.json"
STORE_DIR = os.path.join(REPO, r"experiments\comparisons\hh_003\artifacts\run\A_EPISODIC")
DF_T = 0.25
OUT = os.path.join(os.environ.get("TEMP", r"C:\Users\muzaf\AppData\Local\Temp\opencode"), "pf_entitylink2.json")

STOP = set("""a an the and or but if then else when while for to of in on at by with from as is are was were be been
being i you he she it we they me him her them my your his its our their this that these those there here what which
who whom whose do does did doing have has had having not no yes so too very can will just also about above after again
all any because before below between both each few more most other some such than own same s t don now oh hey hi wow well
ugh okay ok please thanks thank say said says tell told think thought want wanted go going get got like liked loves love
am really cool awesome great nice yeah yeahh""".split())

def norm(t):
    t = html.unescape(t or "")
    return re.sub(r"\s+", " ", t.strip().lower())

tok_re = re.compile(r"[a-z0-9']+")
ent_re = re.compile(r"\b([A-Z][a-z][A-Za-z'\-]*(?:\s+[A-Z][a-z][A-Za-z'\-]*)?)\b")
CAPSTOP = set(w.capitalize() for w in STOP)
EXTRA_CAP = set("Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September October November December The This That I We You Hey Wow Oh Gonna Yeah And But So Then What When Where How Why Who There Here They Their".split())

def tokens(t):
    return set(w for w in tok_re.findall(norm(t)) if w not in STOP and len(w) > 1)
def ents_raw(t):
    raw = re.sub(r"\s+", " ", html.unescape(t or ""))
    out = set()
    for m in ent_re.findall(raw):
        for part in [m] + m.split():
            p = part.strip()
            if p in CAPSTOP or p in EXTRA_CAP or len(p) < 2:
                continue
            out.add(p.lower())
    return out

data = json.load(open(LOCO, encoding="utf-8"))

def session_turns(s):
    turns = []
    keys = [k for k in s["conversation"] if re.match(r"session_\d+$", k)]
    keys.sort(key=lambda k: int(k.split("_")[1]))
    for k in keys:
        for t in s["conversation"][k]:
            turns.append((t.get("dia_id"), t.get("text", "")))
    return turns

conv_state = {}
for s in data:
    conv = s["sample_id"]
    dbp = os.path.join(STORE_DIR, conv + ".db")
    if not os.path.exists(dbp):
        continue
    c = sqlite3.connect(dbp); cur = c.cursor()
    eps = cur.execute("SELECT turn_number,user_message,assistant_message,embedding FROM episodes ORDER BY turn_number").fetchall()
    c.close()
    turns = session_turns(s)
    speakers = set()
    for kk in ("speaker_a", "speaker_b"):
        nm = s["conversation"].get(kk, "")
        for w in re.findall(r"[A-Za-z]+", nm or ""):
            speakers.add(w.lower())
    E = {}
    tdf, edf = Counter(), Counter()
    for tn, um, am, emb in eps:
        raw = um + " " + am
        tk = tokens(raw)
        en = set(x for x in ents_raw(raw) if x not in speakers)
        E[tn] = dict(tk=tk, en=en, e=np.frombuffer(emb, dtype=np.float32))
        for w in tk:
            tdf[w] += 1
        for w in en:
            edf[w] += 1
    N = max(1, len(eps))
    d2t = {}
    for gi, (dida, txt) in enumerate(turns):
        nt = norm(txt)
        if len(nt) < 4:
            continue
        cands = [tn for tn, v in E.items() if nt in (norm(v and "") or "")] if False else None
        # content join using normalized full episode text
        cands = [tn for tn, v in E.items() if nt in norm(v["tkraw"])] if "tkraw" in next(iter(E.values())) else None
        if cands is None:
            # rebuild: store normalized raw once
            pass
    conv_state[conv] = dict(E=E, turns=turns, tdf=tdf, edf=edf, N=N, speakers=speakers)

# store normalized raw for join + maps
for conv, st in conv_state.items():
    for tn, v in st["E"].items():
        v["nt"] = norm(v["e"].tobytes().hex()) if False else None  # placeholder
# We need raw text for join; reload raw text map.
for conv, st in conv_state.items():
    dbp = os.path.join(STORE_DIR, conv + ".db"); c = sqlite3.connect(dbp); cur = c.cursor()
    for tn, um, am in cur.execute("SELECT turn_number,user_message,assistant_message FROM episodes"):
        st["E"][tn]["ntraw"] = norm(um + " " + am)
    c.close()
    E = st["E"]
    m = {}
    for gi, (dida, txt) in enumerate(st["turns"]):
        nt = norm(txt)
        if len(nt) < 4:
            continue
        cands = [tn for tn, v in E.items() if nt in v["ntraw"]]
        if not cands:
            nt2 = nt[:40]
            cands = [tn for tn, v in E.items() if nt2 and nt2 in v["ntraw"]]
        if len(cands) == 1:
            m[dida] = cands[0]
        elif len(cands) > 1:
            m[dida] = min(cands, key=lambda tn: abs(tn - (gi // 2 + 1)))
    st["d2t"] = m
    mapped = sum(1 for dida, txt in st["turns"] if dida in m)
    st["map_rate"] = mapped / max(1, len(st["turns"]))

usable = [c for c, st in conv_state.items() if st["map_rate"] >= 0.90]
print("map_rate:", {c: round(st["map_rate"], 3) for c, st in sorted(conv_state.items())}, "usable:", len(usable))

# discriminative token/entity membership
def disc_tokens(cv, tn):
    st = conv_state[cv]; N = st["N"]
    return set(w for w in st["E"][tn]["tk"] if st["tdf"][w] <= DF_T * N)
def disc_ents(cv, tn):
    st = conv_state[cv]; N = st["N"]
    return set(w for w in st["E"][tn]["en"] if st["edf"][w] <= DF_T * N)

NRM = {cv: {tn: conv_state[cv]["E"][tn]["e"] / (np.linalg.norm(conv_state[cv]["E"][tn]["e"]) + 1e-9)
           for tn in conv_state[cv]["E"]} for cv in usable}
_rc = {}
def rank_of(cv, i, j):
    key = (cv, i)
    if key not in _rc:
        vi = NRM[cv][i]
        order = sorted((t for t in NRM[cv] if t != i), key=lambda t: -float(np.dot(vi, NRM[cv][t])))
        _rc[key] = {t: r + 1 for r, t in enumerate(order)}
    return _rc[key].get(j)
def cos(cv, i, j):
    a = conv_state[cv]["E"][i]["e"]; b = conv_state[cv]["E"][j]["e"]
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0

def classify(cv, i, j, K=5):
    c = cos(cv, i, j)
    r = rank_of(cv, i, j)
    lex = bool(disc_tokens(cv, i) & disc_tokens(cv, j))
    ent = bool(disc_ents(cv, i) & disc_ents(cv, j))
    dense = (r is not None and r <= K)
    return dict(cos=c, rank=r, lex=lex, ent=ent, dense=dense,
                win=(ent and not lex and not dense),
                win_nodense=(ent and not dense))

def summarize(items, tag, K=5):
    rows = []
    for it in items:
        d2t = conv_state[it["conv"]]["d2t"]
        eps = sorted({d2t[e] for e in it["ev"] if e in d2t})
        for a in range(len(eps)):
            for b in range(a + 1, len(eps)):
                m = classify(it["conv"], eps[a], eps[b], K)
                m.update(conv=it["conv"], q=it["q"], i=eps[a], j=eps[b])
                rows.append(m)
    n = len(rows)
    if n == 0:
        print(tag, "no pairs"); return {"summary": {"n": 0}, "rows": []}
    def f(key):
        return round(sum(1 for m in rows if m[key]) / n, 3)
    ranks = sorted(m["rank"] for m in rows if m["rank"])
    summ = dict(tag=tag, n=n,
                cos_med=round(sorted(m["cos"] for m in rows)[n // 2], 3),
                rank_med=(ranks[len(ranks) // 2] if ranks else None),
                dense_rate_K5=f("dense"), lex_rate=f("lex"), ent_rate=f("ent"),
                WIN_entity_only=round(sum(1 for m in rows if m["win"]) / n, 3),
                ent_and_not_dense=round(sum(1 for m in rows if m["win_nodense"]) / n, 3))
    print(tag, json.dumps(summ))
    return {"summary": summ, "rows": rows}

def gold_items(cat):
    out = []
    for s in data:
        conv = s["sample_id"]
        if conv not in usable:
            continue
        for q in s.get("qa", []):
            if q.get("category") == cat and isinstance(q.get("evidence"), list) and len(q["evidence"]) >= 2:
                out.append(dict(conv=conv, q=q["question"], ev=q["evidence"]))
    return out

r3 = summarize(gold_items(3), "CAT3_MULTIHOP")
summarize(gold_items(1), "CAT1_CONTROL")

random.seed(20260923)
nrows = []
for cv in usable:
    tns = list(NRM[cv])
    for _ in range(2000):
        i, j = random.sample(tns, 2)
        nrows.append(classify(cv, i, j, K=5))
nn = len(nrows)
def fn(key):
    return round(sum(1 for m in nrows if m[key]) / nn, 3)
print("NULL_RANDOM", json.dumps(dict(n=nn, cos_med=round(sorted(m["cos"] for m in nrows)[nn // 2], 3),
      dense_rate_K5=fn("dense"), lex_rate=fn("lex"), ent_rate=fn("ent"),
      WIN_entity_only=round(sum(1 for m in nrows if m["win"]) / nn, 3),
      ent_and_not_dense=round(sum(1 for m in nrows if m["win_nodense"]) / nn, 3))))

wins = [m for m in r3["rows"] if m["win"]]
print("CAT3 WIN examples n=", len(wins))
for m in wins[:12]:
    cv = m["conv"]; e1 = m["ent"] if "ent" in m else ""
    entsh = disc_ents(cv, m["i"]) & disc_ents(cv, m["j"])
    print("   ", cv, "t%d-t%d" % (m["i"], m["j"]), "cos=%.2f rank=%s lex=%s entsh=%s | Q:%s" %
          (m["cos"], m["rank"], m["lex"], list(entsh)[:4], m["q"][:56]))

json.dump({"cat3": r3}, open(OUT, "w", encoding="utf-8"), indent=1, default=str)
print("wrote", OUT)
