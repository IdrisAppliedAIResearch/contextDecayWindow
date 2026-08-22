"""The paper-era Mem0 evaluation harness, reproduced.

Source: ``mem0ai/mem0`` at commit ``7b3abd06`` (2 May 2025), directory
``evaluation/``, retired from that repository in June 2026.  That tree carries
the arXiv:2504.19413 badge in its own README and contains one implementation
file per row of the published Table 2.

**What is reproduced verbatim.** The answer prompt, the answer system message
and the LLM-judge prompt are not retyped here - they are extracted from the
canonical git blobs and vendored under ``experiments/comparisons/hh_002/vendor/``,
and this module refuses to import if their SHA-256 no longer matches.  The
call shapes (``temperature=0``, the judge's ``response_format``, the retry
count) follow the same source.

**What is deliberately different, and why none of it can move a score.**

* *Concurrency.*  Their ``rag.py`` answers questions in a single loop; their
  ``evals.py`` already judges with ten threads.  Both stages run threaded here.
  Each call is independent and the results are re-keyed by item, so ordering
  cannot change any answer.
* *Rate-limit backoff.*  Their retry is three attempts one second apart, which
  cannot survive a sustained 429.  Backoff here is exponential and 429-aware.
  A retry returns the same prompt to the same model.
* *Dated model pin.*  Their code passes the ``gpt-4o-mini`` alias.  This module
  pins the snapshot the alias currently resolves to, because an alias that
  moves silently would make the run unreadable later.  ``AGENTS.md`` §4's
  byte-identical rerun rule cannot be met against a vendor API regardless.
* *Category 5 is not generated.*  Their pipeline answers all 1,986 questions
  and then discards the 446 adversarial ones at scoring time
  (``evals.py:22``, ``llm_judge.py:86``).  Skipping generation for records that
  reach no metric saves roughly a fifth of the spend and provably cannot move
  a number that is computed over the other 1,540.
* *Instrumentation.*  Token counts and latencies are recorded per call.  Their
  harness records latency only.  Reading a usage field does not change a
  response.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import string
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from jinja2 import Template

# --------------------------------------------------------------------------
# Vendored prompt text, byte-pinned
# --------------------------------------------------------------------------

VENDOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "comparisons"
    / "hh_002"
    / "vendor"
)

#: SHA-256 of each vendored prompt, taken from the upstream git blob.  These
#: are the study's fidelity anchors: if a prompt drifts, the run stops.
VENDOR_DIGESTS = {
    "rag_answer_prompt.txt":
        "744495b77f2955d437017fd33a0b7156ef41426b7ae8277e5efb92382f234b78",
    "rag_system_message.txt":
        "0c6b92630ba4c22fd29e718d095abb2d6ffba10c04d00962e94bca4a65b23249",
    "llm_judge_accuracy_prompt.txt":
        "44fb3d8f7a1f37b2430772cf90518a32172e4056b7a0dec085402763fd179b9f",
}

UPSTREAM = {
    "repository": "https://github.com/mem0ai/mem0",
    "commit": "7b3abd06",
    "tree": "evaluation/",
    "paper": "arXiv:2504.19413",
}


class HH002HarnessError(RuntimeError):
    pass


def _load_vendor(name: str) -> str:
    path = VENDOR_DIR / name
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != VENDOR_DIGESTS[name]:
        raise HH002HarnessError(
            f"{name} does not match the upstream blob: "
            f"{digest} != {VENDOR_DIGESTS[name]}"
        )
    if b"\r" in raw:
        raise HH002HarnessError(f"{name} has CRLF; the upstream blob is LF")
    return raw.decode("utf-8")


#: ``rag.py``'s jinja template.  The trailing spaces after ``# Question:`` and
#: ``# Context:`` are theirs and are load-bearing for byte fidelity.
ANSWER_PROMPT_TEMPLATE = _load_vendor("rag_answer_prompt.txt")

#: ``rag.py`` builds this from five adjacent string literals with no separating
#: spaces, so the rendered message runs sentences together
#: ("...provided context.If the question involves timing...").  That is the
#: string the published rows were produced with and it is kept exactly.
ANSWER_SYSTEM_MESSAGE = _load_vendor("rag_system_message.txt")

#: ``metrics/llm_judge.py``'s ACCURACY_PROMPT, curly apostrophes included.
JUDGE_PROMPT_TEMPLATE = _load_vendor("llm_judge_accuracy_prompt.txt")

DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


#: Compiled once.  ``rag.py`` builds a fresh ``Template`` per call; compiling
#: is not observable in the rendered string.
_ANSWER_TEMPLATE = Template(ANSWER_PROMPT_TEMPLATE)


def render_answer_prompt(question: str, context: str) -> str:
    """``Template(PROMPT).render(CONTEXT=..., QUESTION=...)``.

    jinja2 is used rather than emulated.  A literal two-step ``str.replace``
    looks equivalent and is not: jinja2 defaults to
    ``keep_trailing_newline=False`` and drops the template's final newline, so
    every prompt the published rows were produced with ends at
    ``# Short answer:`` with nothing after it.  Substitution also re-enters
    text that a real render never touches.  Neither difference is worth
    carrying for a study whose whole claim is that the prompt is theirs.
    """
    return _ANSWER_TEMPLATE.render(CONTEXT=context, QUESTION=question)


def render_judge_prompt(
    question: str, gold_answer: str, generated_answer: str
) -> str:
    """``ACCURACY_PROMPT.format(...)`` - str.format, not jinja, upstream."""
    return JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        gold_answer=gold_answer,
        generated_answer=generated_answer,
    )


# --------------------------------------------------------------------------
# Deterministic metrics, ported from metrics/utils.py
# --------------------------------------------------------------------------


def simple_tokenize(text: str) -> list[str]:
    """``metrics/utils.py::simple_tokenize``."""
    text = str(text)
    return (
        text.lower()
        .replace(".", " ")
        .replace(",", " ")
        .replace("!", " ")
        .replace("?", " ")
        .split()
    )


def deterministic_metrics(prediction: str, reference: str) -> dict[str, float]:
    """The live half of ``metrics/utils.py::calculate_metrics``.

    ROUGE, BERTScore, METEOR and SBERT are commented out in the upstream
    function and contribute to nothing in the published table; they are not
    computed here either.  BLEU needs nltk and is likewise absent from the
    table, whose column is ``llm_score``.

    ``f1`` is a set-overlap over ``simple_tokenize`` and involves no model.
    It is this study's second endpoint for exactly that reason.
    """
    if not prediction or not reference:
        return {"exact_match": 0.0, "f1": 0.0}

    prediction = str(prediction).strip()
    reference = str(reference).strip()
    exact = float(prediction.lower() == reference.lower())

    pred_tokens = set(simple_tokenize(prediction))
    ref_tokens = set(simple_tokenize(reference))
    common = pred_tokens & ref_tokens
    if not pred_tokens or not ref_tokens:
        f1 = 0.0
    else:
        precision = len(common) / len(pred_tokens)
        recall = len(common) / len(ref_tokens)
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
    return {"exact_match": exact, "f1": f1}


# --------------------------------------------------------------------------
# Metered client
# --------------------------------------------------------------------------


@dataclass
class Usage:
    """Cumulative spend, so the report can price the run rather than guess."""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    embedding_tokens: int = 0
    embedding_calls: int = 0
    retries: int = 0
    seconds: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int,
        seconds: float,
    ) -> None:
        with self._lock:
            self.calls += 1
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.cached_tokens += cached_tokens
            self.seconds += seconds

    def record_embedding(self, tokens: int, calls: int = 1) -> None:
        with self._lock:
            self.embedding_calls += calls
            self.embedding_tokens += tokens

    def record_retry(self) -> None:
        with self._lock:
            self.retries += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cached_tokens": self.cached_tokens,
            "embedding_calls": self.embedding_calls,
            "embedding_tokens": self.embedding_tokens,
            "retries": self.retries,
            "seconds": round(self.seconds, 3),
        }


#: gpt-4o-mini list price, USD per million tokens, as of the run date.
PRICE_PER_M = {
    "gpt-4o-mini-2024-07-18": {"input": 0.150, "cached": 0.075, "output": 0.600},
    "text-embedding-3-small": {"input": 0.020, "cached": 0.020, "output": 0.0},
}

#: The Batch API bills generation at half the synchronous rate.  Almost all of
#: this study's generation went through it, so quoting the synchronous price
#: would overstate what the run cost by roughly a factor of two.  Embeddings
#: are not batched and are not discounted.
BATCH_DISCOUNT = 0.5


def price(
    usage: Usage, model: str = DEFAULT_MODEL, batch: bool = False
) -> float:
    rate = PRICE_PER_M[model]
    factor = BATCH_DISCOUNT if batch else 1.0
    fresh = max(usage.prompt_tokens - usage.cached_tokens, 0)
    embed = PRICE_PER_M[DEFAULT_EMBEDDING_MODEL]["input"]
    return (
        (
            fresh * rate["input"]
            + usage.cached_tokens * rate["cached"]
            + usage.completion_tokens * rate["output"]
        )
        * factor
        + usage.embedding_tokens * embed
    ) / 1_000_000


class MeteredClient:
    """Thin wrapper over the OpenAI client with retry, backoff and metering."""

    def __init__(
        self,
        client: Any,
        model: str = DEFAULT_MODEL,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        max_retries: int = 6,
        usage: Usage | None = None,
        cache: Any | None = None,
    ) -> None:
        self._client = client
        self.model = model
        self.embedding_model = embedding_model
        self.max_retries = max_retries
        self.usage = usage if usage is not None else Usage()
        self._embed_cache: dict[str, list[float]] = {}
        self._embed_lock = threading.Lock()
        #: Optional ``hh002_embed_cache.EmbedCache``; survives restarts.
        self.cache = cache

    # -- internals ---------------------------------------------------------

    def _with_retry(self, call: Callable[[], Any], what: str) -> Any:
        delay = 1.0
        last: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return call()
            except Exception as exc:  # noqa: BLE001 - upstream catches bare too
                last = exc
                if attempt == self.max_retries:
                    break
                self.usage.record_retry()
                # Rate limits need room; other faults are usually transient.
                sleep = delay * (4.0 if "429" in str(exc) else 1.0)
                # A silent retry loop is indistinguishable from a hang, and a
                # run this long cannot be watched any other way.
                print(
                    f"    retry {attempt + 1}/{self.max_retries} {what}: "
                    f"{str(exc)[:120]} (sleep {sleep:.1f}s)",
                    flush=True,
                )
                time.sleep(sleep + random.uniform(0, 0.4))
                delay = min(delay * 2, 60.0)
        raise HH002HarnessError(f"{what} failed after retries: {last}") from last

    # -- generation --------------------------------------------------------

    def answer(self, question: str, context: str) -> tuple[str, float, dict]:
        """``RAGManager.generate_response``: same messages, ``temperature=0``."""
        prompt = render_answer_prompt(question, context)

        def call() -> Any:
            return self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ANSWER_SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )

        started = time.time()
        response = self._with_retry(call, "answer")
        elapsed = time.time() - started
        cached = _cached_tokens(response)
        self.usage.record(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            cached,
            elapsed,
        )
        text = (response.choices[0].message.content or "").strip()
        return (
            text,
            elapsed,
            {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "cached_tokens": cached,
                "prompt_chars": len(prompt),
            },
        )

    # -- judging -----------------------------------------------------------

    def judge(
        self, question: str, gold_answer: str, generated_answer: str
    ) -> tuple[int, str]:
        """``metrics/llm_judge.py::evaluate_llm_judge``.

        Upstream does ``json.loads(...)['label']`` and returns
        ``1 if label == "CORRECT" else 0``; any other label, including a
        malformed one, is a zero.  That behaviour is kept, but the raw label is
        returned alongside so malformed verdicts can be counted rather than
        silently absorbed into the score.
        """
        prompt = render_judge_prompt(question, gold_answer, generated_answer)

        def call() -> Any:
            return self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

        started = time.time()
        response = self._with_retry(call, "judge")
        elapsed = time.time() - started
        cached = _cached_tokens(response)
        self.usage.record(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            cached,
            elapsed,
        )
        content = response.choices[0].message.content or ""
        try:
            label = str(json.loads(content)["label"])
        except Exception:  # noqa: BLE001
            label = "__MALFORMED__"
        return (1 if label == "CORRECT" else 0), label

    # -- embeddings --------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        """``RAGManager.calculate_embedding``: one text, one call.

        Memoised by text.  Every arm embeds the same 1,540 questions with the
        same model in the same one-text-per-call shape, so the second request
        would be the first request repeated; issuing it three times would cost
        three times as much and buy a vector this programme has already
        measured to be stable under an identical call shape.  Candidate
        corpora are not memoised - they go through ``embed_many``.
        """
        cached = self._embed_cache.get(text)
        if cached is not None:
            return cached
        if self.cache is not None:
            stored = self.cache.get(self.embedding_model, text, "single")
            if stored is not None:
                with self._embed_lock:
                    self._embed_cache[text] = stored
                return stored

        def call() -> Any:
            return self._client.embeddings.create(
                model=self.embedding_model, input=text
            )

        response = self._with_retry(call, "embed")
        self.usage.record_embedding(response.usage.prompt_tokens)
        vector = response.data[0].embedding
        with self._embed_lock:
            self._embed_cache[text] = vector
        if self.cache is not None:
            self.cache.put(self.embedding_model, text, "single", vector)
        return vector

    def embed_many(self, texts: Sequence[str], batch: int = 256) -> list[list[float]]:
        """Batched embedding for the candidate corpus.

        Upstream embeds one chunk per call inside ``create_chunks``.  Batching
        is a transport change; the vectors returned for a given text are the
        same model's.  Query embeddings still go one per call, matching the
        search path exactly.
        """
        out: list[list[float]] = []
        for start in range(0, len(texts), batch):
            window = list(texts[start : start + batch])
            if self.cache is not None:
                stored = [
                    self.cache.get(self.embedding_model, text, "batch")
                    for text in window
                ]
                if all(vector is not None for vector in stored):
                    out.extend(vector for vector in stored)  # type: ignore[misc]
                    continue

            def call(window: list[str] = window) -> Any:
                return self._client.embeddings.create(
                    model=self.embedding_model, input=window
                )

            response = self._with_retry(call, "embed_many")
            self.usage.record_embedding(response.usage.prompt_tokens)
            vectors = [
                item.embedding
                for item in sorted(response.data, key=lambda d: d.index)
            ]
            if self.cache is not None:
                self.cache.put_many(
                    self.embedding_model, "batch", zip(window, vectors)
                )
            out.extend(vectors)
        return out


def _cached_tokens(response: Any) -> int:
    details = getattr(response.usage, "prompt_tokens_details", None)
    if details is None:
        return 0
    return int(getattr(details, "cached_tokens", 0) or 0)


__all__ = [
    "ANSWER_PROMPT_TEMPLATE",
    "ANSWER_SYSTEM_MESSAGE",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_MODEL",
    "HH002HarnessError",
    "JUDGE_PROMPT_TEMPLATE",
    "MeteredClient",
    "PRICE_PER_M",
    "UPSTREAM",
    "Usage",
    "VENDOR_DIGESTS",
    "deterministic_metrics",
    "price",
    "render_answer_prompt",
    "render_judge_prompt",
    "simple_tokenize",
]
