"""HH-001's own reader client.

`src.inference.provider.InferenceProvider` is a carried subsystem and is not
modified here. It is also not usable for this study's cost reporting: it keeps
`tokens_predicted` and throws `tokens_evaluated` away, and prompt tokens are
precisely the axis on which these arms differ. A1 sends a whole conversation,
A3 sends a couple of thousand characters, and a report that cannot say so has
lost the comparison.

So this talks to the same llama.cpp server directly and keeps everything:
prompt tokens, completion tokens, wall clock, cache hits, and the seed.

**Sampling is sent explicitly rather than inherited.** The server is started
with `--temp 1 --top-p 0.95 --top-k 20`, and the start script is immutable, but
a run that silently inherits whatever the server was launched with is not
reproducible on a server launched differently. The values below are the
server's own, pinned here so the record is self-contained.

**The seed varies with the replicate, deliberately.** A fixed seed on an
identical prompt makes every replicate byte-identical, and the per-item
unanimity rate — this instrument's own noise reading — would read 1.0 by
construction and measure nothing. `seed = seed_base + replicate` keeps the run
reproducible across reruns while leaving genuine variation across replicates.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

#: The running server's sampling, pinned so a rerun does not inherit a
#: different launch. See the module docstring.
TEMPERATURE = 1.0
TOP_P = 0.95
TOP_K = 20
MIN_P = 0.0
REPEAT_PENALTY = 1.0
PRESENCE_PENALTY = 0.0

#: Answers are short facts. Long enough for a sentence with a date in it.
N_PREDICT = 512

SEED_BASE = 5005


class HH001ReaderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReaderReply:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    seconds: float
    seed: int
    truncated: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cached_tokens": self.cached_tokens,
            "seconds": round(self.seconds, 3),
            "seed": self.seed,
            "truncated": self.truncated,
        }


class LlamaReader:
    """One call, one reply, everything recorded."""

    def __init__(
        self,
        base_url: str,
        *,
        seed_base: int = SEED_BASE,
        n_predict: int = N_PREDICT,
        timeout: float = 600.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.seed_base = seed_base
        self.n_predict = n_predict
        self.timeout = timeout

    def __call__(self, prompt: str, replicate: int = 0) -> ReaderReply:
        seed = self.seed_base + replicate
        # Qwen spends the response budget on a visible reasoning trace in raw
        # completion mode unless a closed think block is prefilled. This
        # matches the carried provider's handling so the two ask the model for
        # the same thing.
        body = json.dumps(
            {
                "prompt": f"{prompt}\n<think>\n</think>\n",
                "n_predict": self.n_predict,
                "seed": seed,
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "top_k": TOP_K,
                "min_p": MIN_P,
                "repeat_penalty": REPEAT_PENALTY,
                "presence_penalty": PRESENCE_PENALTY,
                "reasoning_format": "none",
                "cache_prompt": True,
                "stream": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/completion",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            raise HH001ReaderError(
                f"Unable to reach the reader at {self.base_url}: {error}"
            ) from error
        elapsed = time.perf_counter() - started

        timings = payload.get("timings") or {}
        prompt_tokens = int(
            payload.get("tokens_evaluated", timings.get("prompt_n", 0)) or 0
        )
        completion_tokens = int(
            payload.get("tokens_predicted", timings.get("predicted_n", 0)) or 0
        )
        return ReaderReply(
            text=str(payload.get("content", "")).strip(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=int(payload.get("tokens_cached", 0) or 0),
            seconds=elapsed,
            seed=seed,
            # `stop_type == "limit"` means the answer was cut at n_predict.
            truncated=str(payload.get("stop_type", "")) == "limit",
        )

    def runtime_record(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "seed_base": self.seed_base,
            "seed_rule": "seed_base + replicate",
            "n_predict": self.n_predict,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "top_k": TOP_K,
            "min_p": MIN_P,
            "repeat_penalty": REPEAT_PENALTY,
            "presence_penalty": PRESENCE_PENALTY,
            "sampling_source": (
                "pinned here to the running server's launch flags, not inherited"
            ),
        }


def normalize(reply: Any) -> ReaderReply:
    """Accept a plain string from a test double, or a real reply."""
    if isinstance(reply, ReaderReply):
        return reply
    if isinstance(reply, str):
        return ReaderReply(
            text=reply,
            prompt_tokens=0,
            completion_tokens=0,
            cached_tokens=0,
            seconds=0.0,
            seed=-1,
            truncated=False,
        )
    raise HH001ReaderError(f"Reader returned {type(reply)!r}, not text or a reply")


__all__ = [
    "HH001ReaderError",
    "LlamaReader",
    "N_PREDICT",
    "ReaderReply",
    "SEED_BASE",
    "normalize",
]
