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
    """Deployed episodic-chat defaults and historical compatibility fields.

    The default timeline unions raw-cosine matches with the last
    ``recency_window_n`` exchanges and renders the union chronologically.
    Set that count to zero to disable continuity. ``legacy_cc80`` retains
    budgeted CC80 and optional ASPECT; its capacity/ranking settings are unused
    by the timeline. The K-threshold/A3 fields remain
    solely for the private pre-CC-007 builder used by historical checks; they
    do not alter ``EpisodeStore.context``.

    ``embedder_sha256`` and ``embed_call_shape`` jointly pin the model artifact
    and solo-call behavior. ``seed`` is provenance only; the package draws no
    randomness.
    """

    recency_window_n: int = 32
    retrieval_budget_chars: int = 32_000
    semantic_dense_weight: float = 0.8
    bm25_k1: float = 1.2
    bm25_b: float = 0.75
    aspect_enabled: bool = False
    aspect_share: float = 0.5
    aspect_model: str = "en_core_web_sm"
    # Legacy compatibility parameters below remain for the private pre-CC-007
    # ``build_context`` function.  EpisodeStore.context no longer consumes
    # them; retaining them keeps historical registered checks runnable.
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
    read_policy: str = "timeline"
    timeline_threshold: float = 0.48

    def __post_init__(self) -> None:
        if self.read_policy not in ("timeline", "legacy_cc80"):
            raise EpisodicError("read_policy must be timeline or legacy_cc80")
        if not 0.0 <= self.timeline_threshold <= 1.0:
            raise EpisodicError("timeline_threshold must be a finite cosine in [0, 1]")
        if not isinstance(self.recency_window_n, int) or isinstance(self.recency_window_n, bool) or self.recency_window_n < 0:
            raise EpisodicError("recency_window_n must be a non-negative integer")
        if self.retrieval_budget_chars < 0:
            raise EpisodicError("retrieval_budget_chars must be non-negative")
        if self.semantic_dense_weight != 0.8:
            raise EpisodicError(
                "semantic_dense_weight is frozen at the registered CC80 value 0.8"
            )
        if self.bm25_k1 != 1.2 or self.bm25_b != 0.75:
            raise EpisodicError("BM25 is frozen at k1=1.2 and b=0.75")
        if not isinstance(self.aspect_enabled, bool):
            raise EpisodicError("aspect_enabled must be a boolean")
        if self.aspect_share != 0.5:
            raise EpisodicError(
                "aspect_share is frozen at the registered protected share 0.5"
            )
        if self.aspect_model != "en_core_web_sm":
            raise EpisodicError(
                "aspect_model is frozen at the registered en_core_web_sm model"
            )
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
        # Serialized pre-0.3 configurations retain their original read policy.
        payload.setdefault("read_policy", "legacy_cc80")
        return cls(**payload)
