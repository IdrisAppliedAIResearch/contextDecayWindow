"""RS003 Stage-0 / R-TEMP: temporal admission oracle.

Frozen date parser + gold-anchor and relative-resolution window oracles per
RS003_STAGE0_PRE_REGISTRATION.md section 4. Zero model calls: arms are set
windows over cached pool metadata fed through the registered packer.
"""
from __future__ import annotations

import datetime
import re

from rs003_common import (ARTIFACTS, CAPS, block_dia_ids, coverage,
                          double_run, get_vector, instrument_checks,
                          load_vectors, load_world, pack_ids, pack_order,
                          rank_all, save, summarize)

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
for _a, _b in [("jan", 1), ("feb", 2), ("mar", 3), ("apr", 4), ("jun", 6),
               ("jul", 7), ("aug", 8), ("sep", 9), ("oct", 10), ("nov", 11),
               ("dec", 12)]:
    MONTHS[_a] = _b
WEEKDAYS = {d: i for i, d in enumerate(
    ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
     "sunday"])}
DURATION_Q = re.compile(r"\b(how long|how many \w+ (?:ago|since)|duration)\b", re.I)


def parse_session_date(s):
    m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)\s+on\s+(\d{1,2})\s+(\w+),?\s*(\d{4})",
                  s or "")
    if not m:
        return None
    hh, mm, ap, dd, mon, yy = m.groups()
    mo = MONTHS.get(mon.lower())
    if not mo:
        return None
    try:
        return datetime.date(int(yy), mo, int(dd))
    except ValueError:
        return None


def parse_gold_date(text):
    """Gold parser per pre-registration section 4 -> (kind, value).

    Rules (most specific first):
      'The <weekday> before <date>' -> month window containing the
        mechanically resolved anchor day;
      'first weekend of Month YYYY' -> that month;
      full dates (D Month, YYYY | DMonth,YYYY | Month D, YYYY) -> day;
      'Month YYYY' -> month; bare YYYY -> year; else None.
    """
    text = "" if text is None else str(text)
    wb = re.search(r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
                   r"\s+before\s+(\d{1,2})\s*([A-Za-z]+),?\s*(\d{4})", text, re.I)
    if wb:
        wd = WEEKDAYS[wb.group(1).lower()]
        mo = MONTHS.get(wb.group(3).lower())
        if mo:
            try:
                anchor = datetime.date(int(wb.group(4)), mo, int(wb.group(2)))
                delta = (anchor.weekday() - wd) % 7 or 7
                resolved = anchor - datetime.timedelta(days=delta)
                return ("month", (resolved.year, resolved.month))
            except ValueError:
                pass
    fw = re.search(r"weekend of ([A-Za-z]+)\s+(\d{4})", text, re.I)
    if fw and fw.group(1).lower() in MONTHS:
        return ("month", (int(fw.group(2)), MONTHS[fw.group(1).lower()]))
    for pat in [r"(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})",     # D Month, YYYY
                r"(\d{1,2})([A-Z][a-z]+),?\s*(\d{4})",       # DMonth,YYYY
                r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})"]:    # Month D, YYYY
        m = re.search(pat, text)
        if not m:
            continue
        a, b, c = m.groups()
        cand = []
        if a.isdigit() and b.lower() in MONTHS:
            cand.append((int(a), MONTHS[b.lower()], c))
        if b.isdigit() and a.lower() in MONTHS:
            cand.append((int(b), MONTHS[a.lower()], c))
        for d, mo, y in cand:
            try:
                return ("day", datetime.date(int(y), mo, d))
            except ValueError:
                pass
    my = re.search(r"([A-Za-z]+)\s+(\d{4})", text)
    if my and my.group(1).lower() in MONTHS:
        return ("month", (int(my.group(2)), MONTHS[my.group(1).lower()]))
    yy = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if yy:
        return ("year", int(yy.group(1)))
    return (None, None)


def window_dates(kind, val):
    if kind == "day":
        return {val}
    if kind == "month":
        y, mo = val
        d, out = datetime.date(y, mo, 1), set()
        while d.month == mo:
            out.add(d)
            d += datetime.timedelta(days=1)
        return out
    if kind == "year":
        d, out = datetime.date(val, 1, 1), set()
        while d.year == val:
            out.add(d)
            d += datetime.timedelta(days=1)
        return out
    return set()


def window_bounds(base_dates, delta):
    if not base_dates:
        return None
    return (min(base_dates) - datetime.timedelta(days=delta),
            max(base_dates) + datetime.timedelta(days=delta))


REL = re.compile(
    r"\b(yesterday|today|the day before yesterday|"
    r"last (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"last (?:week|month|year)|the week before|the previous (?:week|month|year)|"
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten) "
    r"(?:days?|weeks?|months?|years?) (?:ago|before|after|later|earlier)|"
    r"this (?:past|last) (?:week|month))\b", re.I)
NUMWORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
           "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def resolve_relative(expr, anchor):
    """Deterministic resolve of one relative expression against anchor date."""
    e = expr.lower().strip()
    if e == "yesterday":
        return anchor - datetime.timedelta(days=1)
    if e == "today":
        return anchor
    if "day before yesterday" in e:
        return anchor - datetime.timedelta(days=2)
    m = re.match(r"last (monday|tuesday|wednesday|thursday|friday|saturday|sunday)", e)
    if m:
        wd = WEEKDAYS[m.group(1)]
        return anchor - datetime.timedelta(days=(anchor.weekday() - wd) % 7 or 7)
    m = (re.match(r"(?:last|the week before|the previous) (week|month|year)", e)
         or re.match(r"this (?:past|last) (week|month)", e))
    if m:
        unit = m.group(1)
        if unit == "week":
            return anchor - datetime.timedelta(days=7)
        if unit == "month":
            y, mo = (anchor.year - 1, 12) if anchor.month == 1 else (
                anchor.year, anchor.month - 1)
            return anchor.replace(year=y, month=mo)
        return anchor.replace(year=anchor.year - 1)
    m = re.match(r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten) "
                 r"(days?|weeks?|months?|years?) (ago|before|after|later|earlier)", e)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else NUMWORD[m.group(1)]
        unit, direc = m.group(2), m.group(3)
        mult = 1 if direc in ("after", "later") else -1
        if unit.startswith("day"):
            return anchor + datetime.timedelta(days=mult * n)
        if unit.startswith("week"):
            return anchor + datetime.timedelta(weeks=mult * n)
        if unit.startswith("month"):
            mo = anchor.month + mult * n
            return anchor.replace(year=anchor.year + (mo - 1) // 12,
                                  month=(mo - 1) % 12 + 1)
        if unit.startswith("year"):
            return anchor.replace(year=anchor.year + mult * n)
    return None


def window_order(base_provider, delta, reverse):
    def order_fn(qid, elems):
        bounds = window_bounds(base_provider(qid), delta)
        if bounds is None:
            return []
        lo, hi = bounds
        kept = [e["idx"] for e in elems
                if (sd := parse_session_date(e["date"])) is not None and lo <= sd <= hi]
        return list(reversed(kept)) if reverse else kept
    return order_fn


def compute():
    srcs, convs, items, audit, disc, golds = load_world()
    vecs = load_vectors()
    log = {}
    instrument_checks((srcs, convs, items, audit, disc, golds), vecs, log)
    cat2 = sorted(q for q in items if golds[q]["cat"] == "2")

    parsed = {q: parse_gold_date(golds[q]["gold_answer"]) for q in cat2}
    base_dates = {q: window_dates(*parsed[q]) for q in cat2}

    rel_dates, ev_texts, bucket = {}, {}, {}
    for q in cat2:
        cid, sidx = q.split(":")[0], int(q.split(":")[1])
        conv = srcs[cid]["conversation"]
        tmap = {}
        for k, v in conv.items():
            if k.startswith("session_") and isinstance(v, list):
                for t in v:
                    tmap[t["dia_id"]] = t["text"]
        rr, texts = set(), []
        for dia in convs[cid]["qa"][sidx].get("evidence", []):
            txt = tmap.get(dia, "")
            texts.append(txt)
            sd = parse_session_date(convs[cid]["turn_date"].get(dia, ""))
            if sd is None:
                continue
            for m in REL.finditer(txt):
                d = resolve_relative(m.group(0), sd)
                if d:
                    rr.add(d)
        rel_dates[q], ev_texts[q] = rr, texts
        if DURATION_Q.search(golds[q]["question"]):
            bucket[q] = "duration-difference"
        elif any(REL.search(t) for t in texts):
            bucket[q] = "relative-in-evidence"
        elif parsed[q][0]:
            bucket[q] = f"absolute-in-gold({parsed[q][0]})"
        else:
            bucket[q] = "unparseable"

    def metrics(order_fn, cap):
        out = {}
        for q in cat2:
            elems = convs[q.split(":")[0]]["elements"]
            chosen, chars = pack_order(order_fn(q, elems), elems, cap)
            cov = coverage(golds[q]["gold_ids"], pack_ids(chosen, elems))
            out[q] = dict(coverage=cov, n_packed=len(chosen), chars=chars,
                          full=1 if cov == 1.0 else 0,
                          zero=1 if cov == 0.0 else 0)
        return out

    def control_metrics(block_key):
        out = {}
        for q in cat2:
            ids = block_dia_ids(items[q][block_key])
            cov = coverage(golds[q]["gold_ids"], ids)
            out[q] = dict(coverage=cov, n_packed=None,
                          chars=len(items[q][block_key]),
                          full=1 if cov == 1.0 else 0,
                          zero=1 if cov == 0.0 else 0)
        return out

    arms = {"B_as_is": control_metrics("block_b"),
            "C_as_is": control_metrics("block_c")}
    for cap in CAPS:
        def cc80_order(q, elems, _vecs=vecs):
            r = rank_all(elems, golds[q]["question"],
                         get_vector(_vecs, golds[q]["question"]), _vecs)
            return list(r.order)
        arms[f"CC80_{cap}"] = metrics(cc80_order, cap)
        for delta in (1, 3, 7, 14):
            for rev in (False, True):
                arms[f"T1_gold_d{delta}_{'rev' if rev else 'chron'}_{cap}"] = metrics(
                    window_order(lambda q: base_dates[q], delta, rev), cap)
        arms[f"T2_relative_d7_chron_{cap}"] = metrics(
            window_order(lambda q: rel_dates[q], 7, False), cap)

    # gold-window resolution agreement on items where both sides parse
    agree = {}
    for q in cat2:
        if parsed[q][0] == "day" and rel_dates[q]:
            agree[q] = parsed[q][1] in rel_dates[q]
        elif parsed[q][0] in ("month", "year") and rel_dates[q]:
            w = window_dates(*parsed[q])
            agree[q] = bool(w & rel_dates[q])

    arms_m = {k: (v if k in ("B_as_is", "C_as_is") else v) for k, v in arms.items()}
    summary = {k: summarize(v, cat2, audit) for k, v in arms_m.items()}

    t1 = summary["T1_gold_d7_chron_16000"]
    cc = summary["CC80_16000"]
    t2 = summary["T2_relative_d7_chron_16000"]
    margin_t1 = t1["full_rate"] - cc["full_rate"]
    margin_t2 = t2["full_rate"] - cc["full_rate"]
    parseable = [q for q in cat2 if parsed[q][0]]
    n_p = max(1, len(parseable))
    t1p = sum(arms["T1_gold_d7_chron_16000"][q]["full"] for q in parseable) / n_p
    ccp = sum(arms["CC80_16000"][q]["full"] for q in parseable) / n_p
    recovery = (margin_t2 / margin_t1) if margin_t1 > 0 else None
    if margin_t1 >= 0.10:
        if t1["zero"] <= cc["zero"] and recovery is not None and recovery >= 0.5:
            disp = "BUILD"
        else:
            disp = "SIGNAL"  # between-tier: registered 'between' report
    else:
        disp = "KILL"
    disposition = dict(
        verdict=disp, t1_full=t1["full_rate"], cc80_full=cc["full_rate"],
        t1_margin=round(margin_t1, 4), t2_margin=round(margin_t2, 4),
        recovery_pct=(round(recovery, 4) if recovery is not None else None),
        margin_parseable_subset=round(t1p - ccp, 4),
        n_parseable=len(parseable), t1_zero=t1["zero"], cc80_zero=cc["zero"])

    return {"cat": "2", "instrument": log, "arms": arms, "summary": summary,
            "buckets": bucket,
            "gold_parse_kind": {q: parsed[q][0] for q in cat2},
            "resolution_agreement": agree,
            "disposition": disposition}


def main():
    results = double_run(compute)
    save(ARTIFACTS / "rs003_temp_results.json", results)
    d = results["disposition"]
    print("R-TEMP:", d["verdict"],
          "| T1 margin", d["t1_margin"], "T2 recovery", d["recovery_pct"],
          "| parseable", d["n_parseable"])
    for k in sorted(results["summary"]):
        s = results["summary"][k]
        print(f"  {k:36s} full={s['full']:2d}/{s['n']} "
              f"zero@Bmiss={s['zero_among_B_misses']:2d} cov={s['mean_coverage']}")


if __name__ == "__main__":
    main()
