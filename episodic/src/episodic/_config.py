"""The frozen configuration every constant the studies swept or pinned.

Nothing is buried in module globals: every value that shaped a committed
number is a field here, the config serializes to JSON, and it is stored
alongside the store on first open. Reopening with a mismatched config
raises unless explicitly overridden.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields

from ._errors import EpisodicError

# SHA-256 of the carried Qwen3-Embedding-0.6B Q8_0 GGUF artifact. Every
# committed retrieval number in the source repository was produced by this
# exact file.
CARRIED_EMBEDDER_SHA256 = (
    "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
)

_CANDIDATE_POLICIES = ("full_store", "unsafe_cosine_top_n")
_CALL_SHAPES = ("solo",)


@dataclass(frozen=True)
class EpisodicConfig:
    """Deployed defaults, each traceable to a committed measurement.

    ``recency_window_n`` and ``k_threshold`` are the values of the carried
    recency/similarity paths in the corrected 121-turn run (N cap 32,
    K 0.48). ``candidate_policy`` defaults to the full store: DR-002 found
    that dropping the 19 lowest-cosine episodes from a 119-episode pool
    cost an entire domain, because the coverage selector clusters over the
    pool and tail removal reshuffles the objective rather than removing
    options. The trimming option is therefore named ``unsafe_``.

    The selector is E005's primary configuration ``A3_l0.1_r0.0_k16``:
    relevance plus cluster-diversity, lambda 0.1, cost exponent 0.0,
    16 clusters. Budget accounting is exact serialized characters (DR-001).

    ``embedder_sha256`` and ``embed_call_shape`` pin the embedder identity
    jointly: the model artifact AND how it is called. The same text embedded
    alone versus inside a batch yields materially different vectors from the
    carried model (DX-001), so the call shape is part of the identity, not
    an implementation detail. ``seed`` is recorded for provenance; no code
    path in this package draws randomness.
    """

    recency_window_n: int = 32
    k_threshold: float = 0.48
    candidate_policy: str = "full_store"
    unsafe_cosine_top_n: int = 100
    selector: str = "A3"
    selector_lambda: float = 0.1
    selector_cost_exponent: float = 0.0
    selector_cluster_count: int = 16
    budget_accounting: str = "exact_serialized"
    embedder_sha256: str = CARRIED_EMBEDDER_SHA256
    embed_call_shape: str = "solo"
    seed: int = 5005

    def __post_init__(self) -> None:
        if self.recency_window_n < 0:
            raise EpisodicError("recency_window_n must be non-negative")
        if not 0.0 <= self.k_threshold <= 1.0:
            raise EpisodicError("k_threshold must be a cosine in [0, 1]")
        if self.candidate_policy not in _CANDIDATE_POLICIES:
            raise EpisodicError(
                f"candidate_policy must be one of {_CANDIDATE_POLICIES}; "
                "the unsafe_ prefix is deliberate - see EpisodicConfig"
            )
        if self.unsafe_cosine_top_n < 1:
            raise EpisodicError("unsafe_cosine_top_n must be positive")
        if self.selector != "A3":
            raise EpisodicError(
                "A3 is the only extracted selector; A1/A2 build an O(n^2) "
                "similarity matrix and were disqualified at scale"
            )
        if self.selector_cluster_count < 1:
            raise EpisodicError("selector_cluster_count must be positive")
        if self.budget_accounting != "exact_serialized":
            raise EpisodicError(
                "exact_serialized is the only supported budget accounting"
            )
        if self.embed_call_shape not in _CALL_SHAPES:
            raise EpisodicError(
                f"embed_call_shape must be one of {_CALL_SHAPES}: production "
                "embeds one text per call, and vectors are not comparable "
                "across call shapes"
            )

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "EpisodicConfig":
        payload = json.loads(text)
        known = {field.name for field in fields(cls)}
        unknown = sorted(set(payload) - known)
        if unknown:
            raise EpisodicError(f"Unknown config fields: {unknown}")
        return cls(**payload)
