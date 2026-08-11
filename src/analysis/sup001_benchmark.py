from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.biological_memory.supersession import content_sha256


REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "components" / "biological_memory" / "sup_001"
ARTIFACT_ROOT = STUDY_ROOT / "artifacts"
DOMAINS = ("preference", "location", "schedule", "quantity")
TOP_K = 8
BUDGET_CHARS = 32_000

UPDATED_SUBJECTS = {
    "preference": (
        "afternoon tea", "breakfast coffee", "desk snack", "focus music",
        "weekend dessert", "reading chair", "notebook style", "running route",
        "movie genre", "lunch soup", "garden flower", "travel seat",
        "meeting format", "exercise class", "podcast topic", "lamp color",
    ),
    "location": (
        "team workshop", "parcel pickup", "book club", "photo archive",
        "volunteer shift", "family dinner", "language lesson", "bike repair",
        "painting class", "project review", "farmers market", "music rehearsal",
        "tax appointment", "dog training", "study group", "holiday storage",
    ),
    "schedule": (
        "dentist visit", "piano lesson", "weekly swim", "project standup",
        "grocery delivery", "therapy session", "garden watering", "library visit",
        "strength workout", "meal prep", "language practice", "budget review",
        "team planning", "dog walk", "meditation", "family call",
    ),
    "quantity": (
        "weekly running goal", "coin collection", "book target", "water bottles",
        "course modules", "garden pots", "volunteer hours", "photo prints",
        "recipe cards", "museum visits", "practice sessions", "storage boxes",
        "client interviews", "charity miles", "journal pages", "seed packets",
    ),
}

VALUE_STEMS = {
    "preference": (
        ("Earl Grey", "Sencha", "Jasmine green"),
        ("dark roast", "oat latte", "flat white"),
        ("almonds", "apple slices", "rice crackers"),
        ("ambient piano", "brown noise", "instrumental jazz"),
        ("lemon tart", "berry crumble", "pear sorbet"),
        ("window rocker", "oak armchair", "blue chaise"),
        ("dot grid", "plain cream", "narrow ruled"),
        ("river loop", "park circuit", "canal path"),
        ("historical drama", "documentary", "quiet comedy"),
        ("tomato basil", "lentil", "miso"),
        ("lavender", "marigold", "zinnia"),
        ("aisle", "window", "bulkhead aisle"),
        ("video call", "walking meeting", "written update"),
        ("spin", "pilates", "strength circuit"),
        ("science history", "urban design", "field ecology"),
        ("warm amber", "soft white", "daylight blue"),
    ),
    "location": tuple(
        (f"North Hall {i+1}", f"Cedar Room {i+1}", f"Riverside Suite {i+1}")
        for i in range(16)
    ),
    "schedule": tuple(
        (
            f"Monday {8+i%4}:00 cycle {i+1:02d}",
            f"Wednesday {9+i%4}:30 cycle {i+1:02d}",
            f"Friday {10+i%4}:15 cycle {i+1:02d}",
        )
        for i in range(16)
    ),
    "quantity": tuple(
        (str(100 + i), str(200 + i), str(300 + i)) for i in range(16)
    ),
}

UNCHANGED_SUBJECTS = {
    domain: tuple(f"{domain} stable item {index+1}" for index in range(8))
    for domain in DOMAINS
}


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _statement(domain: str, subject: str, value: str, version: int) -> str:
    if version == 1:
        return f"For my {subject}, the recorded {domain} value is {value}."
    return (
        f"Update for my {subject}: the {domain} value is now {value}. "
        "This replaces the value I gave earlier."
    )


def _query(domain: str, subject: str) -> str:
    return f"What is the current {domain} value for my {subject}?"


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    registrations: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    updated: dict[str, list[dict[str, Any]]] = {}

    def add_episode(
        *, domain: str, key: str | None, subject: str, value: str,
        version: int | None, kind: str, supersedes: str | None = None,
    ) -> dict[str, Any]:
        user = _statement(domain, subject, value, version or 1)
        assistant = "I recorded that update verbatim."
        identity = content_sha256(user, assistant)
        row = {
            "episode_sha256": identity,
            "turn_number": len(episodes) + 1,
            "user": user,
            "assistant": assistant,
        }
        episodes.append(row)
        if key is not None:
            registrations.append(
                {
                    "memory_key": key,
                    "episode_sha256": identity,
                    "operation": "initial" if version == 1 else "update",
                    "supersedes": supersedes,
                }
            )
        return {**row, "domain": domain, "subject": subject, "value": value, "kind": kind}

    # Initial versions, then stable facts and distractors, then two update waves.
    for domain in DOMAINS:
        for index, subject in enumerate(UPDATED_SUBJECTS[domain]):
            key = f"{domain}:{index:02d}"
            row = add_episode(
                domain=domain, key=key, subject=subject,
                value=VALUE_STEMS[domain][index][0], version=1, kind="updated",
            )
            updated[key] = [row]
    for domain in DOMAINS:
        for index, subject in enumerate(UNCHANGED_SUBJECTS[domain]):
            value = f"fixed-{domain}-{index+1:02d}"
            row = add_episode(
                domain=domain, key=None, subject=subject, value=value,
                version=None, kind="unchanged",
            )
            query_id = f"natural:unchanged:{domain}:{index:02d}"
            queries.append({"query_id": query_id, "text": _query(domain, subject)})
            key_rows.append(
                {
                    "query_id": query_id, "kind": "unchanged", "domain": domain,
                    "current_sha256": row["episode_sha256"], "stale_sha256": [],
                    "memory_key": None, "lineage_sha256": [row["episode_sha256"]],
                }
            )
    for index in range(32):
        add_episode(
            domain=DOMAINS[index % 4], key=None,
            subject=f"unrelated archive note {index+1}",
            value=f"reference-{index+1:02d}", version=None, kind="distractor",
        )
    for version_index in (1, 2):
        for domain in DOMAINS:
            for index, subject in enumerate(UPDATED_SUBJECTS[domain]):
                key = f"{domain}:{index:02d}"
                parent = updated[key][-1]["episode_sha256"]
                row = add_episode(
                    domain=domain, key=key, subject=subject,
                    value=VALUE_STEMS[domain][index][version_index],
                    version=version_index + 1, kind="updated", supersedes=parent,
                )
                updated[key].append(row)

    for domain in DOMAINS:
        for index, subject in enumerate(UPDATED_SUBJECTS[domain]):
            key = f"{domain}:{index:02d}"
            rows = updated[key]
            query_id = f"natural:updated:{key}"
            queries.append({"query_id": query_id, "text": _query(domain, subject)})
            key_rows.append(
                {
                    "query_id": query_id, "kind": "updated", "domain": domain,
                    "current_sha256": rows[-1]["episode_sha256"],
                    "stale_sha256": [row["episode_sha256"] for row in rows[:-1]],
                    "memory_key": key,
                    "lineage_sha256": [row["episode_sha256"] for row in rows],
                }
            )

    queries.sort(key=lambda row: row["query_id"])
    key_rows.sort(key=lambda row: row["query_id"])
    if len(episodes) != 256 or len(registrations) != 192 or len(queries) != 96:
        raise AssertionError("SUP-001 generated population count mismatch")
    identities = [row["episode_sha256"] for row in episodes]
    if len(set(identities)) != len(identities):
        raise AssertionError("SUP-001 episode identities are not unique")
    values = [
        value for domain in DOMAINS for triple in VALUE_STEMS[domain] for value in triple
    ] + [f"fixed-{domain}-{index+1:02d}" for domain in DOMAINS for index in range(8)]
    if len(values) != len(set(values)):
        raise AssertionError("SUP-001 values are not unique")

    mechanism = {
        "schema": "sup001-mechanism-v1",
        "episodes": episodes,
        "registrations": registrations,
        "queries": queries,
        "top_k": TOP_K,
        "budget_chars": BUDGET_CHARS,
    }
    measurement = {
        "schema": "sup001-sealed-key-v1",
        "rows": key_rows,
        "history_queries": [
            {"history_query_id": f"history:{row['memory_key']}", **row}
            for row in key_rows if row["kind"] == "updated"
        ],
    }
    return mechanism, measurement


def write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite SUP-001 artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )


def run(output_dir: Path) -> dict[str, Any]:
    mechanism, measurement = build()
    mechanism_path = output_dir / "mechanism_manifest.json"
    key_path = output_dir / "SEALED_KEY_DO_NOT_OPEN.json"
    report_path = output_dir / "corpus_lock.json"
    write_json(mechanism_path, mechanism)
    write_json(key_path, measurement)
    report = {
        "status": "PASS",
        "mechanism_digest": canonical_digest(mechanism),
        "sealed_key_digest": canonical_digest(measurement),
        "episode_count": len(mechanism["episodes"]),
        "registration_count": len(mechanism["registrations"]),
        "natural_query_count": len(mechanism["queries"]),
        "history_query_count": len(measurement["history_queries"]),
    }
    write_json(report_path, report)
    return report
