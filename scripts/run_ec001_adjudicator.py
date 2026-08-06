"""Run the pinned independent AI adjudicator on EC-001 trigger packets."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.run_ec001_rater import (  # noqa: E402
    RaterClient,
    _calibrate,
    _validate_local_server,
)
from src.analysis.ec001_longmemeval import (  # noqa: E402
    AMENDMENT_004_SHA,
    assert_repository_ready,
    sha256_file,
)
from src.analysis.ec001_tier2 import (  # noqa: E402
    build_rationale_prompt,
    parse_binary_label,
)


def _jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _adjudication_prompt(packet: dict) -> str:
    prompt = str(packet["label_prompt"])
    judgments = packet.get("blinded_judgments")
    if judgments:
        rendered = "\n".join(
            f"- {row['pass']}: {'yes' if row['label'] else 'no'} — "
            f"{row['rationale']}"
            for row in judgments
        )
        prompt += (
            "\n\nThree blinded raters disagreed. Their model identities are "
            f"withheld:\n{rendered}\n\nResolve the disagreement independently "
            "under the question's locked criterion. Answer yes or no only."
        )
    return prompt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--runtime-record", type=Path, required=True)
    parser.add_argument("--server-url")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository = assert_repository_ready(require_clean=True)
    if args.output.exists():
        raise FileExistsError(
            f"Refusing to overwrite adjudication output: {args.output}"
        )
    runtime = json.loads(args.runtime_record.read_text(encoding="utf-8"))
    if runtime.get("amendment_004_sha") != AMENDMENT_004_SHA:
        raise RuntimeError("Runtime record predates Amendment 004")
    config = runtime.get("adjudicator")
    if not isinstance(config, dict):
        raise RuntimeError("Runtime record has no adjudicator")
    rater_families = {
        str(row["model_family"]).casefold() for row in runtime["raters"]
    }
    if str(config["model_family"]).casefold() in rater_families:
        raise RuntimeError("Adjudicator must not duplicate a rater family")
    server_props = _validate_local_server(config, args.server_url)
    client = RaterClient(config, args.server_url)
    calibration = _calibrate(
        client,
        json.loads(args.calibration.read_text(encoding="utf-8")),
    )

    packets = [row for path in args.packet for row in _jsonl(path)]
    if len({row["anon_id"] for row in packets}) != len(packets):
        raise RuntimeError("Adjudication packets contain duplicate items")
    packets.sort(key=lambda row: row["anon_id"])
    outputs: list[dict] = []
    started = time.time()
    for index, packet in enumerate(packets, 1):
        prompt = _adjudication_prompt(packet)
        label_surface = client.complete(prompt, max_tokens=10)
        label = parse_binary_label(label_surface)
        if packet["mechanical_zero"] and label:
            raise RuntimeError(
                f"Adjudicator scored mechanical zero above zero: "
                f"{packet['anon_id']}"
            )
        rationale = client.complete(
            build_rationale_prompt(prompt, label),
            max_tokens=180,
        ).strip()
        if not rationale:
            raise RuntimeError(
                f"Missing adjudicator rationale: {packet['anon_id']}"
            )
        outputs.append(
            {
                "anon_id": packet["anon_id"],
                "trigger_class": packet["trigger_class"],
                "adjudicator_family": config["model_family"],
                "adjudicator_model_id": config["model_id"],
                "label": label,
                "label_response": label_surface,
                "rationale": rationale,
            }
        )
        if index % 10 == 0 or index == len(packets):
            print(f"{index:3d}/{len(packets)} adjudications")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in outputs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    header = {
        "record": "EC-001 independent AI adjudication",
        "head": repository["head"],
        "adjudicator_family": config["model_family"],
        "adjudicator_model_id": config["model_id"],
        "provider": config["provider"],
        "server_props": server_props,
        "calibration": calibration,
        "calibration_status": "PASS",
        "packet_sha256": {
            path.name: sha256_file(path) for path in args.packet
        },
        "runtime_record_sha256": sha256_file(args.runtime_record),
        "item_count": len(outputs),
        "call_count": client.call_count,
        "started_utc": datetime.fromtimestamp(
            started, timezone.utc
        ).isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "output_sha256": sha256_file(args.output),
        "limitation": "AI adjudication; not human adjudication",
    }
    args.output.with_suffix(args.output.suffix + ".header.json").write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Adjudication complete: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
