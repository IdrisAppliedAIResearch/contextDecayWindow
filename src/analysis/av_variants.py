"""AV-READER-001 - vary the reader, hold retrieval fixed.

AV-MATRIX established that 80.4% of errors happen on items whose gold evidence
was already delivered, and that accuracy-given-evidence is flat at 74-75% across
every composition and budget. The binding constraint is downstream of retrieval.

Three variants, all on frozen contexts, nothing about selection changed:

* ``V1_THINK``    A_CC80@32k, vendor prompt, Qwen native reasoning ON.
                  AV-MATRIX disabled thinking to match gpt-4o-mini, which means
                  it measured the reader with its reasoning switched off. One
                  flag, and it targets the hypothesis directly.
* ``V2_PROMPT``   A_CC80@32k, an instructed prompt that asks the model to locate
                  the bearing turns and handle dates before answering, with
                  native thinking OFF - so prompt-elicited reasoning and native
                  reasoning stay separable.
* ``V3_SEALED``   HH-003's sealed A_EPISODIC contexts, byte-identical to what
                  gpt-4o-mini read, vendor prompt, thinking OFF. Isolates the
                  pure model gap with no composition confound.

Baseline for V1 and V2 is AV-MATRIX's ``A_CC80@32k``. Baseline for V3 is
HH-003's own ``A_EPISODIC/judged_r1.json``.
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
REPO = Path(__file__).resolve().parents[2]
MATRIX = REPO / "experiments/components/aspect_v3/artifacts/av_matrix"
HH003 = REPO / "experiments/comparisons/hh_003/artifacts/run"

REASONED_SYSTEM = (
    "You are answering a question about a long conversation between two people. "
    "The conversation is given to you as dated turns."
)

REASONED_TEMPLATE = """# Question:
{question}

# Context:
{context}

# Instructions:
Work through these steps before answering.
1. Find the turns in the context that bear on the question. Note their dates.
2. If the question is about time - when, how long, before or after - compute the
   answer relative to the dates on those turns, not relative to today.
3. If answering needs more than one turn, combine them explicitly.
4. If the context does not contain the answer, give the closest thing it does
   contain rather than inventing a fact.

Then give the final answer on its own last line, formatted exactly as:
ANSWER: <shortest possible answer>

The final answer must be as short as possible, use words taken directly from the
conversation where possible, and omit the subject."""

_ANSWER_LINE = re.compile(r"^ANSWER:\s*(.*)$", re.MULTILINE)

VARIANTS: dict[str, dict[str, Any]] = {
    "V1_THINK": {
        "contexts": "A_CC80@32k.json",
        "prompt": "vendor",
        "thinking": True,
        "max_tokens": 2048,
    },
    "V2_PROMPT": {
        "contexts": "A_CC80@32k.json",
        "prompt": "reasoned",
        "thinking": False,
        # Unbounded. There is ample context (200k) and VRAM headroom, and a cap
        # is not part of the hypothesis: the question is whether the model can
        # reason without a reasoning mode, not how tersely it can do it.
        # finish_reason is recorded so a wall would be visible, not guessed at.
        "max_tokens": -1,
    },
    # The composition arms. AV-MATRIX found CC80 / ASPECT / DA flat within 2.38
    # points, but it measured them under the vendor prompt - a reader that was
    # not reasoning over the context. "Composition does not separate" was
    # therefore conditional on the reader, and was reported as unconditional.
    # These re-run the same three compositions under the instructed prompt, so
    # the interaction can be read directly against the committed baselines.
    "V2_ASPECT": {
        "contexts": "B_CC80_ASPECT@32k.json",
        "prompt": "reasoned",
        "thinking": False,
        "max_tokens": -1,
    },
    "V2_DA": {
        "contexts": "C_CC80_ASPECT_DA@32k.json",
        "prompt": "reasoned",
        "thinking": False,
        "max_tokens": -1,
    },
    "V3_SEALED": {
        "contexts": HH003 / "A_EPISODIC/contexts.json",
        "prompt": "vendor",
        "thinking": False,
        "max_tokens": -1,
    },
}


class AVVariantError(RuntimeError):
    pass


def _chat(
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    thinking: bool,
    json_mode: bool = False,
) -> tuple[str, str]:
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
        "chat_template_kwargs": {"enable_thinking": thinking},
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
            choice = payload["choices"][0]
            return (
                str(choice["message"]["content"]),
                str(choice.get("finish_reason", "")),
            )
        except (urllib.error.URLError, OSError, KeyError, ValueError) as error:
            last = error
            time.sleep(5 * (attempt + 1))
    raise AVVariantError(f"reader call failed after retries: {last}")


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)


def extract_answer(raw: str, style: str) -> tuple[str, bool]:
    """Return (short answer, whether the expected format was found)."""
    body = _strip_think(raw).strip()
    if style == "vendor":
        return body, True
    matches = _ANSWER_LINE.findall(body)
    if matches:
        for candidate in reversed(matches):
            if candidate.strip():
                return candidate.strip(), True
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return (lines[-1] if lines else ""), False


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


def _contexts_path(spec: dict[str, Any], contexts_dir: Path | None) -> Path:
    value = spec["contexts"]
    if isinstance(value, Path):
        return value
    if contexts_dir is None:
        raise AVVariantError("--contexts-dir is required for this variant")
    return contexts_dir / str(value)


def answer(
    name: str,
    out_dir: Path,
    contexts_dir: Path | None = None,
    only: set[str] | None = None,
) -> None:
    spec = VARIANTS[name]
    out_dir.mkdir(parents=True, exist_ok=True)
    source = json.loads(
        _contexts_path(spec, contexts_dir).read_text(encoding="utf-8")
    )["items"]
    path = out_dir / f"{name}.answers.jsonl"
    done = _done(path)
    pending = [k for k in sorted(source) if k not in done]
    if only is not None:
        # A paired subset: every arm answers the same items, so a partial
        # run is still a like-for-like contrast rather than three different
        # samples compared to each other.
        pending = [k for k in pending if k in only]
    print(f"[{name}] {len(done)} done, {len(pending)} pending", flush=True)
    started = time.time()
    with path.open("a", encoding="utf-8") as handle:
        for index, key in enumerate(pending, start=1):
            item = source[key]
            if spec["prompt"] == "vendor":
                messages = [
                    {"role": "system", "content": ANSWER_SYSTEM_MESSAGE},
                    {
                        "role": "user",
                        "content": render_answer_prompt(
                            item["question"], item["context"]
                        ),
                    },
                ]
            else:
                messages = [
                    {"role": "system", "content": REASONED_SYSTEM},
                    {
                        "role": "user",
                        "content": REASONED_TEMPLATE.format(
                            question=item["question"], context=item["context"]
                        ),
                    },
                ]
            raw, finish = _chat(
                messages,
                max_tokens=spec["max_tokens"],
                thinking=spec["thinking"],
            )
            response, well_formed = extract_answer(raw, spec["prompt"])
            repaired = False
            if spec["prompt"] == "reasoned" and not well_formed:
                # The model ran out of budget mid-working, so the fallback
                # would score a fragment of its own reasoning. Ask once for
                # the answer line only, reusing the same prefix (and its KV
                # cache). Bounded, counted, and never changes the prompt.
                followup, _f = _chat(
                    [
                        *messages,
                        {"role": "assistant", "content": _strip_think(raw)},
                        {
                            "role": "user",
                            "content": (
                                "Output only the final line, formatted "
                                "exactly as:\nANSWER: <shortest possible "
                                "answer>"
                            ),
                        },
                    ],
                    max_tokens=64,
                    thinking=False,
                )
                fixed, ok = extract_answer(followup, "reasoned")
                if ok and fixed:
                    response, well_formed, repaired = fixed, True, True
            handle.write(
                json.dumps(
                    {
                        "key": key,
                        "sample_id": item["sample_id"],
                        "source_index": item["source_index"],
                        "category": item["category"],
                        "question": item["question"],
                        "answer": item["answer"],
                        "response": response,
                        "raw_chars": len(raw),
                        "well_formed": well_formed,
                        "finish_reason": finish,
                        "repaired": repaired,
                        "truncated": finish == "length",
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
                    f"  [{name}] {index}/{len(pending)} {rate:.2f}s/item "
                    f"eta {remaining:.0f}m",
                    flush=True,
                )


def _label(text: str) -> str:
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


def judge(name: str, out_dir: Path) -> None:
    answers = _done(out_dir / f"{name}.answers.jsonl")
    path = out_dir / f"{name}.judged.jsonl"
    done = _done(path)
    pending = [k for k in sorted(answers) if k not in done]
    print(f"[{name}] judging {len(pending)} ({len(done)} done)", flush=True)
    started = time.time()
    with path.open("a", encoding="utf-8") as handle:
        for index, key in enumerate(pending, start=1):
            row = answers[key]
            text, _finish = _chat(
                [
                    {
                        "role": "user",
                        "content": render_judge_prompt(
                            row["question"], row["answer"], row["response"]
                        ),
                    }
                ],
                max_tokens=256,
                thinking=False,
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
                        "well_formed": row.get("well_formed", True),
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
                    f"  [{name}] {index}/{len(pending)} {rate:.2f}s/item "
                    f"eta {remaining:.0f}m",
                    flush=True,
                )


def _sign_p(gains: int, losses: int) -> float:
    from math import comb

    total = gains + losses
    if total == 0:
        return 1.0
    smaller = min(gains, losses)
    return min(
        1.0, 2 * sum(comb(total, i) for i in range(smaller + 1)) / 2**total
    )


def score(out_dir: Path) -> dict[str, Any]:
    baselines = {
        "V1_THINK": MATRIX / "live/A_CC80@32k.judged.jsonl",
        "V2_PROMPT": MATRIX / "live/A_CC80@32k.judged.jsonl",
        "V2_ASPECT": MATRIX / "live/B_CC80_ASPECT@32k.judged.jsonl",
        "V2_DA": MATRIX / "live/C_CC80_ASPECT_DA@32k.judged.jsonl",
        "V3_SEALED": HH003 / "A_EPISODIC/judged_r1.json",
    }
    result: dict[str, Any] = {"schema": "av-reader-001-v1", "variants": {}}
    for name in VARIANTS:
        rows = _done(out_dir / f"{name}.judged.jsonl")
        if not rows:
            continue
        base_path = baselines[name]
        if base_path.suffix == ".json":
            base = {
                r["key"]: r
                for r in json.loads(base_path.read_text(encoding="utf-8"))["records"]
            }
            base_label = "gpt-4o-mini (HH-003 A_EPISODIC)"
        else:
            base = _done(base_path)
            base_label = f"vendor prompt, same composition ({base_path.stem})"
        common = sorted(set(rows) & set(base))
        gains = sum(
            1 for k in common if rows[k]["llm_score"] > base[k]["llm_score"]
        )
        losses = sum(
            1 for k in common if rows[k]["llm_score"] < base[k]["llm_score"]
        )
        result["variants"][name] = {
            "n": len(common),
            "score": round(
                100 * sum(rows[k]["llm_score"] for k in common) / len(common), 2
            ),
            "baseline": base_label,
            "baseline_score": round(
                100 * sum(base[k]["llm_score"] for k in common) / len(common), 2
            ),
            "gains": gains,
            "losses": losses,
            "net": gains - losses,
            "p": round(_sign_p(gains, losses), 4),
            "malformed_judge": sum(
                rows[k]["judge_label"] == "__MALFORMED__" for k in common
            ),
            "format_misses": sum(
                1 for k in common if not rows[k].get("well_formed", True)
            ),
        }
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AV reader variants")
    parser.add_argument("stage", choices=("answer", "judge", "score"))
    parser.add_argument("--variant", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--contexts-dir", default=None)
    parser.add_argument("--keys", default=None, help="JSON list of item keys")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    names = [args.variant] if args.variant else list(VARIANTS)
    contexts_dir = Path(args.contexts_dir) if args.contexts_dir else None
    only = (
        set(json.loads(Path(args.keys).read_text(encoding="utf-8")))
        if args.keys
        else None
    )
    if args.stage == "answer":
        for name in names:
            answer(name, out_dir, contexts_dir, only)
    elif args.stage == "judge":
        for name in names:
            judge(name, out_dir)
    else:
        result = score(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
