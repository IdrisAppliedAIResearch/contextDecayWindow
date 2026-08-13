"""Rater B: the carried local model, used as an annotator and nothing else.

The compiler this stage builds must be model-free. Rater B is on the other side
of that line - it is measurement, like the plant key, and `AGENTS.md` §4 permits
measurement to use what mechanism may not. Nothing in
`src/biological_memory/` may import this module, and the import-boundary test
enforces it.

The prompt is committed verbatim below. It restates the protocol's semantic
rules and shows the model one query at a time. It never mentions the grammar,
never shows the compiler's output, and never shows rater A's labels, so B's
judgement is independent of the mechanism in the only sense available here.

The runtime is not bit-reproducible even at a fixed seed, so the artifact this
writes - raw response text, one per query - is the record. A rerun is not
expected to reproduce it byte for byte and no gate depends on that.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Sequence

ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
SEED = 5005

SYSTEM_PROMPT = """You are annotating user queries for a memory-retrieval study.

You see the query text and nothing else. You do not see answers, stored
memories, retrieval output, or any label. Judge only from the words in the
query.

For each query decide three things.

1. finite (true or false)

true when a fixed number of stored items, knowable from the query text alone,
would fully satisfy the request.

false when satisfying the request needs an unknown number of stored items. This
includes counting, summing, averaging, computing a duration or a difference,
comparing across an unstated period, ordering a set whose size the query does
not state, picking the most recent or the largest out of an unnumbered set, and
any request whose extent depends on what happens to be stored.

Example: "How many bikes do I own?" is false. The answer is a count over an
unknown number of stored mentions; that the answer is one number does not make
the evidence one item.

2. plan_class, applied in this precedence order

HISTORY - the query asks how a value changed over time, or asks for a
superseded value as distinct from the current one. A reference to a prior
CONVERSATION ("in our previous chat about X") points at where to look, not at
what changed, and is NOT HISTORY.

ENUMERATE_N - the query states an integer N and asks for the N members of a
set. An integer that is a price, a date, a model number, a distance, a
duration, or an ordinal position is not N.

CONJUNCT - the query contains two or more requests, each of which would be a
valid standalone lookup if asked alone.

LOOKUP - the query asks for exactly one fact, satisfiable by one stored item.

OPEN - everything else: unbounded requests, ambiguous reference, requests whose
extent the text does not fix, and anything that is none of the above.

3. requested_count

The integer N when plan_class is ENUMERATE_N, otherwise null.

Answer with one JSON object and nothing else:
{"finite": true, "plan_class": "LOOKUP", "requested_count": null}"""

_JSON = re.compile(r"\{[^{}]*\}")
_THINK = re.compile(r"<think>.*?</think>", re.S)

VALID_CLASSES = ("LOOKUP", "HISTORY", "ENUMERATE_N", "CONJUNCT", "OPEN")


class RaterError(RuntimeError):
    pass


@dataclass(frozen=True)
class Rating:
    query_id: str
    finite: bool | None
    plan_class: str | None
    requested_count: int | None
    raw: str
    parsed: bool


def _post(payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def rate_one(query_id: str, text: str, *, timeout: float = 180.0) -> Rating:
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.0,
        "top_k": 1,
        "seed": SEED,
        "max_tokens": 2048,
        "stream": False,
    }
    try:
        body = _post(payload, timeout)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RaterError(f"rater B unreachable: {error}") from error

    raw = body["choices"][0]["message"]["content"] or ""
    # Only content outside a reasoning block counts, per the scoring protocol.
    visible = _THINK.sub("", raw).strip()
    matches = _JSON.findall(visible)
    if not matches:
        return Rating(query_id, None, None, None, raw, False)
    try:
        parsed = json.loads(matches[-1])
    except json.JSONDecodeError:
        return Rating(query_id, None, None, None, raw, False)

    finite = parsed.get("finite")
    plan_class = parsed.get("plan_class")
    count = parsed.get("requested_count")
    if not isinstance(finite, bool) or plan_class not in VALID_CLASSES:
        return Rating(query_id, None, None, None, raw, False)
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        count = None
    return Rating(query_id, finite, plan_class, count, raw, True)


def rate_many(items: Sequence[tuple[str, str]], *, progress=None) -> list[Rating]:
    ratings: list[Rating] = []
    for index, (query_id, text) in enumerate(items, start=1):
        ratings.append(rate_one(query_id, text))
        if progress is not None:
            progress(index, len(items), ratings[-1])
    return ratings


def to_payload(split: str, ratings: Sequence[Rating], split_manifest_sha256: str) -> dict[str, Any]:
    return {
        "schema": "dmr004-annotation-v1",
        "rater": "B",
        "split": split,
        "protocol": "DMR_004_ANNOTATION_PROTOCOL.md",
        "split_manifest_sha256": split_manifest_sha256,
        "endpoint": ENDPOINT,
        "seed": SEED,
        "decoding": "temperature 0, top_k 1",
        "system_prompt_sha256": __import__("hashlib").sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "count": len(ratings),
        "unparsed": sum(1 for rating in ratings if not rating.parsed),
        "labels": [
            {
                "query_id": rating.query_id,
                "finite": rating.finite,
                "plan_class": rating.plan_class,
                "requested_count": rating.requested_count,
                "parsed": rating.parsed,
                "raw": rating.raw,
            }
            for rating in ratings
        ],
    }
