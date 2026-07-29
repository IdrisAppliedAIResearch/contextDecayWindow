from __future__ import annotations

import statistics
import time

from .config import CACHE_ROOT, DEFAULT_BUDGET, CorpusSpec
from .corpus import build_raw_spans, load_distilled_ltm, load_raw_episodes
from .embedding import CarriedEmbedder
from .embedding_cache import EmbeddingCache
from .methods import BuiltMethod, METHOD_IDS, build_method
from .models import Query, RetrievalResult
from .serialization import PackResult, pack_ranked_candidates


class RetrievalHarness:
    """Read-only, deterministic retrieval and exact-budget assembly."""

    def __init__(
        self,
        spec: CorpusSpec,
        *,
        embedder=None,
        embedding_cache: EmbeddingCache | None = None,
    ) -> None:
        self.spec = spec
        self.embedder = embedder or CarriedEmbedder()
        self.embedding_cache = embedding_cache
        self._owns_cache = False
        self._methods: dict[str, BuiltMethod] = {}

    def build(self, method_id: str) -> BuiltMethod:
        if method_id in self._methods:
            return self._methods[method_id]
        if method_id not in METHOD_IDS:
            raise ValueError(f"Unsupported method: {method_id}")
        if method_id == "M1" and not self.spec.has_distilled_ltm:
            raise ValueError(f"{self.spec.corpus_id} has no M1 baseline")

        start = time.perf_counter()
        if method_id == "M1":
            candidates = load_distilled_ltm(self.spec)
        else:
            raw = load_raw_episodes(self.spec)
            if method_id == "M5_span":
                cache = self._span_cache()
                candidates = build_raw_spans(raw, self.embedder, cache)
            else:
                candidates = raw
        method = build_method(method_id, candidates)
        method.index_build_ms = (time.perf_counter() - start) * 1000.0
        self._methods[method_id] = method
        return method

    def retrieve(
        self,
        method_id: str,
        query: Query,
        *,
        budget: int = DEFAULT_BUDGET,
        repetitions: int = 9,
    ) -> RetrievalResult:
        if repetitions < 1:
            raise ValueError("repetitions must be positive")
        method = self.build(method_id)

        encode_start = time.perf_counter()
        encoded = method.encode(query, self.spec, self.embedder)
        query_encode_ms = (time.perf_counter() - encode_start) * 1000.0

        warm_ranked = method.rank(query, encoded)
        warm_pack = pack_ranked_candidates(
            method_id,
            method.ordered_for_packing(warm_ranked),
            budget,
        )

        rank_times: list[float] = []
        pack_times: list[float] = []
        combined_times: list[float] = []
        final_ranked = warm_ranked
        final_pack = warm_pack
        for _ in range(repetitions):
            repetition_start = time.perf_counter()
            rank_start = repetition_start
            ranked = method.rank(query, encoded)
            rank_elapsed = (time.perf_counter() - rank_start) * 1000.0
            pack_start = time.perf_counter()
            packed = pack_ranked_candidates(
                method_id,
                method.ordered_for_packing(ranked),
                budget,
            )
            pack_elapsed = (time.perf_counter() - pack_start) * 1000.0
            combined_elapsed = (time.perf_counter() - repetition_start) * 1000.0
            if packed.rendered_block != warm_pack.rendered_block:
                raise AssertionError("Retrieval changed across benchmark repetitions")
            rank_times.append(rank_elapsed)
            pack_times.append(pack_elapsed)
            combined_times.append(combined_elapsed)
            final_ranked = ranked
            final_pack = packed

        self._assert_result_bounds(final_pack)
        return RetrievalResult(
            corpus_id=self.spec.corpus_id,
            method_id=method_id,
            query=query,
            budget=budget,
            ranked_count=len(final_ranked),
            selected=final_pack.selected,
            rendered_block=final_pack.rendered_block,
            phases=final_pack.phases,
            skipped_oversized=final_pack.skipped_oversized,
            duplicate_drops=final_pack.duplicate_drops,
            query_encode_ms=query_encode_ms,
            rank_ms=statistics.median(rank_times),
            pack_ms=statistics.median(pack_times),
            rank_pack_ms=statistics.median(combined_times),
            index_build_ms=method.index_build_ms,
            benchmark_repetitions=repetitions,
        )

    def close(self) -> None:
        if self._owns_cache and self.embedding_cache is not None:
            self.embedding_cache.close()
            self.embedding_cache = None
            self._owns_cache = False

    def _span_cache(self) -> EmbeddingCache:
        if self.embedding_cache is not None:
            return self.embedding_cache
        model_sha256 = getattr(self.embedder, "model_sha256", None)
        if not model_sha256:
            raise ValueError(
                "M5_span requires an explicit cache for a custom embedder"
            )
        path = CACHE_ROOT / f"{self.spec.corpus_id}_span_embeddings.sqlite"
        self.embedding_cache = EmbeddingCache(path, str(model_sha256))
        self._owns_cache = True
        return self.embedding_cache

    def _assert_result_bounds(self, packed: PackResult) -> None:
        violations = [
            item.candidate.turn_number
            for item in packed.selected
            if not self.spec.eligible_turn_min
            <= item.candidate.turn_number
            <= self.spec.eligible_turn_max
        ]
        if violations:
            raise AssertionError(
                f"Retrieval selected out-of-range turns: {sorted(set(violations))}"
            )

    def __enter__(self) -> "RetrievalHarness":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
