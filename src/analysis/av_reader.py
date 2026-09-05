"""AV-MATRIX live scoring - drive the six cells through the local reader.

Six cells x 842 items. The reader and judge are the local Qwen3.8-27B stack on
127.0.0.1:8000, using HH-002's frozen vendor prompts verbatim so the answer and
judge surfaces are identical to HH-003's.

Deviations from HH-003, both deliberate and both recorded here:

1. **Model.** HH-003's reader and judge were gpt-4o-mini-2024-07-18. These are
   Qwen3.8-27B-UD-Q4_K_XL judged by itself. Scores are therefore NOT comparable
   to HH-003's published numbers in absolute terms; only the contrasts *within
   this run* are. Same-model judging is a known weakness, not an improvement.
2. **Temperature 0**, deviating from LV-009's registered `.6`. The paired
   contrasts here rest on small numbers of moved items, and one sample per arm
   at `.6` has a sampling floor larger than the effects being measured. This
   does not make the runtime deterministic - it removes deliberate sampling
   only.

Single-pass judging, matching HH-003's `judged_r1`. Everything checkpoints to
JSONL after every call and resumes on restart.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

from analysis.hh002_harness import (
    ANSWER_SYSTEM_MESSAGE,
    deterministic_metrics,
    render_answer_prompt,
    render_judge_prompt,
)

SERVER = "http://127.0.0.1:8000"
SEED = 5005
CELLS = (
    "A_CC80@16k",
    "B_CC80_ASPECT@16k",
    "C_CC80_ASPECT_DA@16k",
    "A_CC80@32k",
    "B_CC80_ASPECT@32k",
    "C_CC80_ASPECT_DA@32k",
)


class AVReaderError(RuntimeError):
    pass


def _chat(messages: list[dict[str, str]], *, max_tokens: int, json_mode: bool) -> str:
    body: dict[str, Any] = {
        "messages": messages,
        "temperature": 0.0,
        "top_k": 1,
        "top_p": 1.0,
        "min_p": 0.0,
        "repeat_penalty": 1.0,
        "presence_penalty": 0.0,
        "seed": SEED,
        "max_tokens": max_tokens,
        "cache_prompt": True,
        "stream": False,
        "reasoning_format": "none",
        # Qwen3.8 is a hybrid reasoning model. Left on, it spends the token
        # budget on a <think> block and the actual answer never arrives.
        # HH-003's gpt-4o-mini had no thinking mode, so disabling it is the
        # closer match as well as the only way to get an answer out.
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = json.dumps(body).encode("utf-8")
    last: Exception | None = None
    for attempt in range(4):
        try:
            request = urllib.request.Request(
                f"{SERVER}/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=900) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = str(payload["choices"][0]["message"]["content"])
            return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        except (urllib.error.URLError, OSError, KeyError, ValueError) as error:
            last = error
            time.sleep(5 * (attempt + 1))
    raise AVReaderError(f"reader call failed after retries: {last}")


def _done(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[row["key"]] = row
    return out


def answer(contexts_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for cell in CELLS:
        source = json.loads(
            (contexts_dir / f"{cell}.json").read_text(encoding="utf-8")
        )["items"]
        path = out_dir / f"{cell}.answers.jsonl"
        done = _done(path)
        pending = [k for k in sorted(source) if k not in done]
        print(f"[{cell}] {len(done)} done, {len(pending)} pending", flush=True)
        started = time.time()
        with path.open("a", encoding="utf-8") as handle:
            for index, key in enumerate(pending, start=1):
                item = source[key]
                text = _chat(
                    [
                        {"role": "system", "content": ANSWER_SYSTEM_MESSAGE},
                        {
                            "role": "user",
                            "content": render_answer_prompt(
                                item["question"], item["context"]
                            ),
                        },
                    ],
                    max_tokens=512,
                    json_mode=False,
                )
                handle.write(
                    json.dumps(
                        {
                            "key": key,
                            "sample_id": item["sample_id"],
                            "source_index": item["source_index"],
                            "category": item["category"],
                            "question": item["question"],
                            "answer": item["answer"],
                            "response": text.strip(),
                            "context_chars": item["context_chars"],
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
                handle.flush()
                if index % 25 == 0 or index == len(pending):
                    rate = (time.time() - started) / index
                    remaining = rate * (len(pending) - index) / 60
                    print(
                        f"  [{cell}] {index}/{len(pending)} "
                        f"{rate:.2f}s/item eta {remaining:.0f}m",
                        flush=True,
                    )


def _label(text: str) -> str:
    """Strict. A judge that did not emit parseable JSON is MALFORMED.

    An earlier version fell back to searching the prose for "correct". That is
    unsafe: the model's own reasoning text contains the word constantly, so the
    fallback silently scored malformed judgements as CORRECT.
    """
    for candidate in (text, *re.findall(r"\{.*?\}", text, re.DOTALL)):
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict) and "label" in value:
            label = str(value["label"]).strip().upper()
            if label in ("CORRECT", "WRONG"):
                return label
    return "__MALFORMED__"


def judge(out_dir: Path) -> None:
    for cell in CELLS:
        answers = _done(out_dir / f"{cell}.answers.jsonl")
        path = out_dir / f"{cell}.judged.jsonl"
        done = _done(path)
        pending = [k for k in sorted(answers) if k not in done]
        print(f"[{cell}] judging {len(pending)} ({len(done)} done)", flush=True)
        started = time.time()
        with path.open("a", encoding="utf-8") as handle:
            for index, key in enumerate(pending, start=1):
                row = answers[key]
                text = _chat(
                    [
                        {
                            "role": "user",
                            "content": render_judge_prompt(
                                row["question"], row["answer"], row["response"]
                            ),
                        }
                    ],
                    max_tokens=256,
                    json_mode=True,
                )
                label = _label(text)
                metrics = deterministic_metrics(row["response"], row["answer"])
                handle.write(
                    json.dumps(
                        {
                            "key": key,
                            "sample_id": row["sample_id"],
                            "source_index": row["source_index"],
                            "category": row["category"],
                            "judge_label": label,
                            "llm_score": int(label == "CORRECT"),
                            "f1": metrics["f1"],
                            "exact_match": metrics["exact_match"],
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
                handle.flush()
                if index % 50 == 0 or index == len(pending):
                    rate = (time.time() - started) / index
                    remaining = rate * (len(pending) - index) / 60
                    print(
                        f"  [{cell}] {index}/{len(pending)} "
                        f"{rate:.2f}s/item eta {remaining:.0f}m",
                        flush=True,
                    )


def score(out_dir: Path) -> dict[str, Any]:
    judged = {cell: _done(out_dir / f"{cell}.judged.jsonl") for cell in CELLS}
    populated = [rows for rows in judged.values() if rows]
    common = set.intersection(*(set(rows) for rows in populated)) if populated else set()
    if len(populated) != len(CELLS):
        common = set()
    arms: dict[str, Any] = {}
    for cell, rows in judged.items():
        subset = [rows[k] for k in sorted(common) if k in rows]
        if not subset:
            continue
        arms[cell] = {
            "n": len(subset),
            "correct": sum(r["llm_score"] for r in subset),
            "llm_score": round(
                100 * sum(r["llm_score"] for r in subset) / len(subset), 2
            ),
            "f1": round(sum(r["f1"] for r in subset) / len(subset), 4),
            "malformed": sum(r["judge_label"] == "__MALFORMED__" for r in subset),
        }
    contrasts = []
    cells = [c for c in CELLS if c in arms]
    for i, left in enumerate(cells):
        for right in cells[i + 1 :]:
            gains = sum(
                1
                for k in common
                if judged[left][k]["llm_score"] > judged[right][k]["llm_score"]
            )
            losses = sum(
                1
                for k in common
                if judged[left][k]["llm_score"] < judged[right][k]["llm_score"]
            )
            contrasts.append(
                {
                    "left": left,
                    "right": right,
                    "gains": gains,
                    "losses": losses,
                    "net": gains - losses,
                }
            )
    return {
        "schema": "av-matrix-live-v1",
        "population": len(common),
        "reader": "Qwen3.8-27B-UD-Q4_K_XL @ temperature 0, local",
        "judge": "same model, single pass, temperature 0",
        "not_comparable_to": (
            "HH-003 absolute scores - different reader and judge model. Only "
            "the within-run contrasts are interpretable."
        ),
        "arms": arms,
        "contrasts": sorted(contrasts, key=lambda row: -abs(row["net"])),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score the AV matrix live")
    parser.add_argument("stage", choices=("answer", "judge", "score", "all"))
    parser.add_argument("--contexts", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    contexts_dir, out_dir = Path(args.contexts), Path(args.out)
    if args.stage in ("answer", "all"):
        answer(contexts_dir, out_dir)
    if args.stage in ("judge", "all"):
        judge(out_dir)
    if args.stage in ("score", "all"):
        result = score(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
