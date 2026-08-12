"""Agreement between the two raters, and the adjudicated gold standard.

The adjudication rules are the ones fixed in `DMR_004_ANNOTATION_PROTOCOL.md`
§5 before any label existed:

* a `finite` disagreement resolves to `false`, because a fail-closed stage must
  not have a gold standard that over-claims completeness;
* a `plan_class` disagreement is recorded as `DISPUTED` rather than resolved,
  and disputed queries leave the per-class statistics while staying in the
  finite/open statistic that rule 1 has already settled;
* `requested_count` survives only where both raters chose `ENUMERATE_N` and
  agreed on the integer.

Cohen's kappa is reported alongside raw agreement because raw agreement on a
skewed label is uninformative - the same reason the pre-registration cannot
gate on accuracy.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

DISPUTED = "DISPUTED"


def _artifact(repository_root: Path, name: str) -> dict[str, Any]:
    path = repository_root / "experiments/components/biological_memory/dmr_004/artifacts" / name
    if not path.is_file():
        raise FileNotFoundError(f"annotation artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def cohen_kappa(pairs: list[tuple[Any, Any]]) -> float | None:
    """Chance-corrected agreement. None when it is undefined."""
    if not pairs:
        return None
    total = len(pairs)
    observed = sum(1 for left, right in pairs if left == right) / total
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    expected = sum(
        (left_counts[label] / total) * (right_counts[label] / total)
        for label in set(left_counts) | set(right_counts)
    )
    if expected >= 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def adjudicate(repository_root: Path, split: str) -> dict[str, Any]:
    short = {"development": "dev", "holdout": "holdout"}[split]
    a = _artifact(repository_root, f"annotations_{short}_rater_a.json")
    b = _artifact(repository_root, f"annotations_{short}_rater_b.json")
    if a["split_manifest_sha256"] != b["split_manifest_sha256"]:
        raise ValueError("raters annotated different split manifests")

    a_by_id = {row["query_id"]: row for row in a["labels"]}
    b_by_id = {row["query_id"]: row for row in b["labels"]}
    if set(a_by_id) != set(b_by_id):
        raise ValueError("raters annotated different queries")

    gold: list[dict[str, Any]] = []
    finite_pairs: list[tuple[Any, Any]] = []
    class_pairs: list[tuple[Any, Any]] = []
    unparsed = 0

    for query_id in a_by_id:
        left = a_by_id[query_id]
        right = b_by_id[query_id]

        # An unparsed rater-B response is a missing judgement, not a vote for
        # anything. It is counted, excluded from agreement, and adjudicated the
        # conservative way for `finite`.
        if not right.get("parsed", True):
            unparsed += 1
            gold.append(
                {
                    "query_id": query_id,
                    "finite": False if left["finite"] else left["finite"],
                    "plan_class": DISPUTED,
                    "requested_count": None,
                    "basis": "rater_b_unparsed",
                }
            )
            continue

        finite_pairs.append((left["finite"], right["finite"]))
        class_pairs.append((left["plan_class"], right["plan_class"]))

        agreed_finite = left["finite"] and right["finite"]
        agreed_class = left["plan_class"] == right["plan_class"]
        count = None
        if agreed_class and left["plan_class"] == "ENUMERATE_N":
            if left["requested_count"] == right["requested_count"]:
                count = left["requested_count"]
        gold.append(
            {
                "query_id": query_id,
                "finite": agreed_finite,
                "plan_class": left["plan_class"] if agreed_class else DISPUTED,
                "requested_count": count,
                "basis": "agreed" if agreed_class else "class_disputed",
            }
        )

    rated = len(finite_pairs)
    finite_agree = sum(1 for left, right in finite_pairs if left == right)
    class_agree = sum(1 for left, right in class_pairs if left == right)
    confusion: Counter[tuple[str, str]] = Counter(class_pairs)

    return {
        "split": split,
        "annotated": len(gold),
        "rater_b_unparsed": unparsed,
        "finite": {
            "rated": rated,
            "agreed": finite_agree,
            "raw_agreement": finite_agree / rated if rated else None,
            "cohen_kappa": cohen_kappa(finite_pairs),
            "rater_a_true": sum(1 for left, _ in finite_pairs if left),
            "rater_b_true": sum(1 for _, right in finite_pairs if right),
        },
        "plan_class": {
            "rated": rated,
            "agreed": class_agree,
            "raw_agreement": class_agree / rated if rated else None,
            "dispute_rate": (rated - class_agree) / rated if rated else None,
            "cohen_kappa": cohen_kappa(class_pairs),
            "confusion": [
                {"rater_a": key[0], "rater_b": key[1], "count": value}
                for key, value in sorted(confusion.items(), key=lambda item: -item[1])
            ],
        },
        "gold": {
            "finite_true": sum(1 for row in gold if row["finite"]),
            "finite_false": sum(1 for row in gold if not row["finite"]),
            "classes": dict(Counter(row["plan_class"] for row in gold)),
            "labels": sorted(gold, key=lambda row: row["query_id"]),
        },
    }


def write_gold(repository_root: Path, split: str) -> Path:
    record = adjudicate(repository_root, split)
    path = (
        repository_root
        / "experiments/components/biological_memory/dmr_004/artifacts"
        / f"gold_{split}.json"
    )
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
