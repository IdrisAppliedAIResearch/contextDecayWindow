"""Generate HH-002's evidence spine.

The spine is the file every sentence of the writeup is checked against. Each
row names a value, the artifact it came from, and that artifact's SHA-256, so
a claim can be traced to bytes on disk rather than to a memory of a run.

HH-001's spine caught nothing when its token figure was four times too low,
because the gate checked that a number appeared in the spine, not that the
spine was right. So this generator computes every value from the artifacts
itself. Nothing here is typed by hand, and a number that cannot be computed
does not get a row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analysis.hh002_analysis import (  # noqa: E402
    HH002AnalysisError,
    cost_summary,
    gctrl,
    judge_variance,
    load_judged,
    load_predictions,
    paired,
)
from analysis.hh002_harness import UPSTREAM, VENDOR_DIGESTS  # noqa: E402
from analysis.hh002_run import ARTIFACTS, INHERITED, PUBLISHED, score  # noqa: E402

#: Registered arms first, then the post-hoc RAG sweep.  The sweep is
#: DESCRIPTIVE: it was added after A_RAG missed its target, to establish that
#: the published "RAG (best variant)" row names a family rather than a
#: configuration.  It carries no claim about this component.
REGISTERED_ARMS = ["A_FULL", "A_CDW", "A_CDW_NOTS", "A_RAG", "A_NONE"]
SWEEP_ARMS = ["A_RAG_1000_K1", "A_RAG_1000_K2", "A_RAG_500_K4"]
ARMS = REGISTERED_ARMS + SWEEP_ARMS


def digest(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate HH-002 spine")
    parser.add_argument("--base", type=Path, default=ARTIFACTS)
    parser.add_argument("--out", type=Path,
                        default=Path("paper/notes/HH002_EVIDENCE_SPINE.md"))
    parser.add_argument("--tolerance", type=float, default=3.0)
    args = parser.parse_args(argv)
    base = args.base

    available = [a for a in ARMS if (base / a / "judged_r1.json").exists()]
    if not available:
        print("no judged arms", file=sys.stderr)
        return 1

    out: list[str] = []
    w = out.append

    w("# HH-002 evidence spine\n")
    w("Every value below is computed from the artifact named beside it by")
    w("`scripts/hh002_spine.py`. Nothing is typed by hand.\n")

    # -- provenance -------------------------------------------------------
    w("## 1. Provenance\n")
    w(f"- Upstream harness: `{UPSTREAM['repository']}` at `{UPSTREAM['commit']}`, "
      f"tree `{UPSTREAM['tree']}`, paper `{UPSTREAM['paper']}`")
    w("- Vendored prompt digests (SHA-256 of the upstream git blob):\n")
    w("| File | SHA-256 |")
    w("|---|---|")
    for name, sha in sorted(VENDOR_DIGESTS.items()):
        w(f"| `vendor/{name}` | `{sha}` |")
    w("")

    commitments = base / "commitments.json"
    if commitments.exists():
        payload = json.loads(commitments.read_text(encoding="utf-8"))
        w(f"- Commitments digest: `{payload['digest']}`")
        w(f"- Model: `{payload['commitments']['model']}`, "
          f"embedder `{payload['commitments']['embedding_model']}`")
        w(f"- Artifact `commitments.json` SHA-256: `{digest(commitments)}`\n")

    # -- artifact digests -------------------------------------------------
    w("## 2. Artifacts\n")
    w("| Artifact | Records | SHA-256 |")
    w("|---|---:|---|")
    for arm in available:
        for name in ("predictions.json", "judged_r1.json", "judged_r2.json"):
            path = base / arm / name
            if not path.exists():
                continue
            n = len(json.loads(path.read_text(encoding="utf-8"))["records"])
            w(f"| `{arm}/{name}` | {n} | `{digest(path)}` |")
    w("")

    # -- the numbers ------------------------------------------------------
    w("## 3. Scores\n")
    w("Standing follows commitment order, not determinism. The five registered")
    w("arms were named in `HH_002_PRE_REGISTRATION.md` §5 before the first")
    w("generation call; the sweep was added after `A_RAG` missed its target and")
    w("is DESCRIPTIVE.\n")
    w("| Arm | llm_score | f1 | exact_match | n | malformed | Standing |")
    w("|---|---:|---:|---:|---:|---:|---|")
    for arm in available:
        result = score(list(load_judged(arm, base=base).values()))
        standing = (
            "REGISTERED-LIVE" if arm in REGISTERED_ARMS else "DESCRIPTIVE"
        )
        w(f"| `{arm}` | {result['llm_score']*100:.2f}% | {result['f1']:.4f} | "
          f"{result['exact_match']:.4f} | {result['n']} | "
          f"{result['malformed_judgements']} | {standing} |")
    w("")

    # -- per category -----------------------------------------------------
    w("## 3a. Scores by question category\n")
    w("LoCoMo category 1 is single-hop, 2 temporal, 3 multi-hop, 4")
    w("open-domain. Category 5 is adversarial and is skipped by")
    w("`evals.py:22`, so it reaches no number in any row.\n")
    per_cat: dict[str, dict[str, float]] = {}
    cats: list[str] = []
    for arm in available:
        result = score(list(load_judged(arm, base=base).values()))
        per_cat[arm] = {
            c: v["llm_score"] * 100 for c, v in result["per_category"].items()
        }
        for c in result["per_category"]:
            if c not in cats:
                cats.append(c)
    cats.sort(key=int)
    counts = score(
        list(load_judged(available[0], base=base).values())
    )["per_category"]
    w("| Arm | " + " | ".join(f"cat {c} (n={counts[c]['n']})" for c in cats) + " |")
    w("|---" * (len(cats) + 1) + "|")
    for arm in available:
        w(f"| `{arm}` | "
          + " | ".join(f"{per_cat[arm].get(c, float('nan')):.2f}%" for c in cats)
          + " |")
    w("")
    if "A_CDW" in per_cat and "A_CDW_NOTS" in per_cat:
        w("**Timestamp effect** (`A_CDW` − `A_CDW_NOTS`), by category: "
          + ", ".join(
              f"cat {c} {per_cat['A_CDW'][c] - per_cat['A_CDW_NOTS'][c]:+.2f}"
              for c in cats
          )
          + ".\n")

    # -- floor-adjusted ---------------------------------------------------
    if "A_NONE" in per_cat:
        floor = score(list(load_judged("A_NONE", base=base).values()))
        floor_pts = floor["llm_score"] * 100
        w("## 3b. Points above the no-memory floor\n")
        w(f"The floor is **{floor_pts:.2f}%** overall and is **not uniform**: "
          + ", ".join(f"cat {c} {per_cat['A_NONE'][c]:.2f}%" for c in cats)
          + ".\n")
        w("**Rows measured on this rig only.** Subtracting this floor from a")
        w("row quoted from Table 2 is forbidden — see `DO_NOT_WRITE.md` item")
        w("35. The floor was measured here, and the strata of the quoted rows")
        w("were never published.\n")
        w("| Arm | Raw | Above floor |")
        w("|---|---:|---:|")
        for arm in available:
            if arm == "A_NONE":
                continue
            raw = score(list(load_judged(arm, base=base).values()))
            raw_pts = raw["llm_score"] * 100
            w(f"| `{arm}` | {raw_pts:.2f}% | {raw_pts - floor_pts:.2f} |")
        w("")

    # -- gate -------------------------------------------------------------
    tolerance = args.tolerance
    variance = None
    for arm in available:
        if (base / arm / "judged_r2.json").exists():
            try:
                variance = judge_variance(arm, base)
                tolerance = max(tolerance, variance["spread_points"])
            except HH002AnalysisError:
                pass
            break

    w("## 4. G-CTRL\n")
    if variance:
        w(f"Judge variance, `{variance['arm']}` scored twice over the same "
          f"{variance['n']} sealed answers: rates "
          f"{variance['rate_points']}, spread "
          f"**{variance['spread_points']:.2f} points**, "
          f"{variance['item_flips']} items flipped "
          f"({variance['item_flip_rate']*100:.2f}%).\n")
    w(f"Tolerance in force: **±{tolerance:.2f} points** "
      f"(registered rule: ±3.0 or the measured spread, whichever is wider).\n")
    gate = gctrl(tolerance, base)
    w("| Arm | Published | Measured | Delta | Within |")
    w("|---|---:|---:|---:|:--:|")
    for check in gate["checks"]:
        if check.get("status") == "NOT RUN":
            w(f"| `{check['arm']}` | {check['target']:.2f}% | — | — | not run |")
            continue
        w(f"| `{check['arm']}` | {check['target_points']:.2f}% | "
          f"{check['measured_points']:.2f}% | {check['delta_points']:+.2f} | "
          f"{'yes' if check['within_tolerance'] else 'NO'} |")
    w("")
    w(f"**G-CTRL: {'PASSED' if gate['passed'] else 'FAILED'}**\n")

    # -- contrasts --------------------------------------------------------
    w("## 5. Paired contrasts\n")
    w("`p` is one-sided for the named treatment beating the named control, so a")
    w("row whose treatment lost reads `p = 1`. Both directions of the")
    w("`A_CDW`/`A_FULL` contrast are printed because the paper quotes the")
    w("component-favouring one, and a spine that held only the losing direction")
    w("would leave that quotation untraceable.\n")
    w("**Registered vs post-hoc.** `HH_002_PRE_REGISTRATION.md` §7 registers one")
    w("directional claim: `A_CDW` > `A_RAG`. Every other row here is post-hoc.")
    w("`A_CDW` > `A_FULL` is emphatically post-hoc - §10 prediction 4 predicted")
    w("the opposite sign, that the component would land *below* full context.\n")
    w("| Treatment | Control | Endpoint | Delta (pts) | Gains | Losses | Ties | p | Standing |")
    w("|---|---|---|---:|---:|---:|---:|---:|---|")
    registered = {("A_CDW", "A_RAG")}
    for treatment, control in [
        ("A_CDW", "A_RAG"), ("A_CDW", "A_NONE"),
        ("A_CDW", "A_FULL"), ("A_FULL", "A_CDW"),
        ("A_CDW", "A_CDW_NOTS"), ("A_FULL", "A_RAG"),
        ("A_CDW", "A_RAG_500_K4"), ("A_RAG_500_K4", "A_RAG_1000_K2"),
    ]:
        if treatment not in available or control not in available:
            continue
        for endpoint in ("llm_score", "f1"):
            try:
                contrast = paired(treatment, control, endpoint, base)
            except HH002AnalysisError:
                continue
            standing = ("REGISTERED-LIVE"
                        if (treatment, control) in registered
                        else "post-hoc")
            w(f"| `{treatment}` | `{control}` | {endpoint} | "
              f"{contrast.delta*100:+.2f} | {contrast.gains} | "
              f"{contrast.losses} | {contrast.ties} | "
              f"{contrast.p_one_sided:.4g} | {standing} |")
    w("")

    # -- cost -------------------------------------------------------------
    w("## 6. Cost per answer\n")
    w("| Arm | Mean prompt tokens | Total prompt tokens | Mean context chars | "
      "Units delivered |")
    w("|---|---:|---:|---:|---:|")
    for arm, row in cost_summary(available, base).items():
        w(f"| `{arm}` | {row['mean_prompt_tokens']:,} | "
          f"{row['total_prompt_tokens']:,} | "
          f"{row['mean_context_chars']:,} | "
          f"{row['mean_units_delivered']:,.2f} |")
    w("")

    # -- inherited --------------------------------------------------------
    w("## 7. Rows quoted, not measured\n")
    w("These come from arXiv:2504.19413 Table 2 and were **not** re-run here.")
    w("Five of them are the Mem0 authors' reproductions of other people's")
    w("systems, not those systems' own reports.\n")
    w("| System | Published | Attribution |")
    w("|---|---:|---|")
    for system, value in INHERITED.items():
        note = "Mem0 authors, own system" if system.startswith("Mem0") \
            else "Mem0 authors' reproduction"
        w(f"| {system} | {value:.2f}% | {note} |")
    w("")

    # -- prohibitions -----------------------------------------------------
    w("## 8. Prohibitions\n")
    w("Grep these before publishing. Each is a sentence this study's design")
    w("makes false.\n")
    w("- Do **not** write that this component beat Mem0 *on the published")
    w("  table*. Mem0's row was not re-run here; it needs a vendor account")
    w("  this study does not have. It is quoted with attribution.")
    w("- Do **not** report a paired test against Mem0, Zep or A-MEM. Their")
    w("  per-item answers were never published.")
    w("- Do **not** call any of this `CONFIRMATORY`. LoCoMo is spent on both")
    w("  splits and generation ran against a vendor API, so `AGENTS.md` §4's")
    w("  byte-identical rerun rule cannot be met. `REGISTERED-LIVE` at best.")
    w("- Do **not** describe the result as a capability claim. LoCoMo fits a")
    w("  modern context window; full context wins the published table.")
    w("- Do **not** compare any number here to Mem0's current 92.5%. That is")
    w("  a different harness, a different answerer model and top_k=200.")
    w("- Do **not** claim breadth. The arm carries no coverage objective.\n")

    text = "\n".join(out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    print(f"\nwritten to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
