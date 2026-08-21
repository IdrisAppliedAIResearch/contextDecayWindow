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

ARMS = ["A_FULL", "A_CDW", "A_CDW_NOTS", "A_RAG", "A_NONE"]


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
    w("| Arm | llm_score | f1 | exact_match | n | malformed judgements |")
    w("|---|---:|---:|---:|---:|---:|")
    for arm in available:
        result = score(list(load_judged(arm, base=base).values()))
        w(f"| `{arm}` | {result['llm_score']*100:.2f}% | {result['f1']:.4f} | "
          f"{result['exact_match']:.4f} | {result['n']} | "
          f"{result['malformed_judgements']} |")
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
    w("| Treatment | Control | Endpoint | Delta (pts) | Gains | Losses | Ties | p |")
    w("|---|---|---|---:|---:|---:|---:|---:|")
    for treatment, control in [
        ("A_CDW", "A_RAG"), ("A_CDW", "A_NONE"), ("A_FULL", "A_CDW"),
        ("A_CDW", "A_CDW_NOTS"), ("A_FULL", "A_RAG"),
    ]:
        if treatment not in available or control not in available:
            continue
        for endpoint in ("llm_score", "f1"):
            try:
                contrast = paired(treatment, control, endpoint, base)
            except HH002AnalysisError:
                continue
            w(f"| `{treatment}` | `{control}` | {endpoint} | "
              f"{contrast.delta*100:+.2f} | {contrast.gains} | "
              f"{contrast.losses} | {contrast.ties} | "
              f"{contrast.p_one_sided:.4g} |")
    w("")

    # -- cost -------------------------------------------------------------
    w("## 6. Cost per answer\n")
    w("| Arm | Mean prompt tokens | Total prompt tokens | Mean context chars | "
      "Units delivered |")
    w("|---|---:|---:|---:|---:|")
    for arm, row in cost_summary(available, base).items():
        w(f"| `{arm}` | {row['mean_prompt_tokens']:,.1f} | "
          f"{row['total_prompt_tokens']:,} | "
          f"{row['mean_context_chars']:,.1f} | "
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
