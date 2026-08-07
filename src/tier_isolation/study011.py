"""Study 011: run one memory tier, the other, or both in either order.

The deployed engine cannot express three of the four registered arms. Its
constructor requires ``n_cap > 10`` and ``0.0 <= k_threshold < 0.50``, so
there is no value that disables either tier -- Arm A (K off) and Arm B
(recency off) are both rejected before they start -- and its packer walks
recency first only, so Arm C has no order to run in.

This module adds the two switches the registered design needs and nothing
else. No selector, no formation change, no threshold change: the
similarity and recency candidate sets are computed by the carried engine's
own methods, unmodified. What changes is whether a tier is consulted and
which tier gets first claim on the budget.

**Arm D is not served here.** Section 5 requires the control to run on the
deployed configuration as committed, from checked-out prior code in a
separate worktree, never a flag-off runner. Asking this module for Arm D
raises.

Packing is IC-001's ``pack_arm``, imported unchanged. Its recency-first
order is byte-identical to the deployed packer -- IC-001's
``assert_b0_matches_deployed_packer`` is the standing proof -- so the two
orders differ in fill order and in nothing else.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from src.db.retrieval import (
    get_all_episodes_with_embeddings,
    update_retrieval_metadata,
)
from src.db.rule_store import get_all_rules
from src.internal_packing.ic001 import build_tier_state, pack_arm
from src.memory.context_matched_stm import (
    ContextMatchedStmResult,
    ContextMatchedStmRetrievalEngine,
    extract_stm_payload,
)
from src.memory.stm_context_builder import build_stm_context, render_rules_block
from src.memory.stm_retrieval_engine import StmRetrievalEngine


class TierIsolationError(RuntimeError):
    """Raised when an arm is asked for something it does not express."""


@dataclass(frozen=True)
class ArmConfig:
    """One registered arm. ``order`` names IC-001's packing order key."""

    arm: str
    recency_enabled: bool
    k_enabled: bool
    order: str
    label: str


# Section 3's table. Arm D is present so that asking for it fails with the
# reason rather than with a KeyError.
ARM_CONFIGS: dict[str, ArmConfig] = {
    "A": ArmConfig("A", True, False, "B0", "STM only (N = 32, K disabled)"),
    "B": ArmConfig("B", False, True, "B1", "LTM only (recency disabled, K = 0.48)"),
    "C": ArmConfig("C", True, True, "B1", "both, K-first"),
    "D": ArmConfig("D", True, True, "B0", "both, recency-first (deployed)"),
}
CONTROL_ARM = "D"
SERVED_ARMS = ("A", "B", "C")


class TierIsolationEngine(ContextMatchedStmRetrievalEngine):
    """The carried engine with a tier switch and a fill-order switch."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        arm: str,
        n_cap: int,
        k_threshold: float,
        payload_budget: int,
        embedding_provider=None,
        system_prompt: str | None = None,
    ) -> None:
        try:
            config = ARM_CONFIGS[arm]
        except KeyError as error:
            raise TierIsolationError(f"Unregistered arm: {arm}") from error
        if arm == CONTROL_ARM:
            raise TierIsolationError(
                "Arm D is the control and must run on the deployed "
                "configuration as committed, from checked-out prior code in "
                "a separate worktree -- never from this module"
            )

        # The carried validators reject a disabled tier by construction, so
        # they are replaced rather than bypassed silently: each surviving
        # constraint below is the carried one, applied to the tiers this arm
        # actually uses.
        StmRetrievalEngine.__init__(
            self,
            conn,
            embedding_provider=embedding_provider,
            system_prompt=system_prompt,
        )
        if config.recency_enabled and n_cap <= 10:
            raise TierIsolationError(
                "Context matching requires N above the carried cap"
            )
        if config.k_enabled and not 0.0 <= k_threshold < 0.50:
            raise TierIsolationError(
                "Context matching requires K below the carried threshold"
            )
        if payload_budget < 1:
            raise TierIsolationError("Payload budget must be positive")

        self.config = config
        self.n_cap = n_cap if config.recency_enabled else 0
        self.k_threshold = k_threshold
        self.payload_budget = payload_budget
        self.last_result: ContextMatchedStmResult | None = None
        self._last_generations: dict[str, int] = {}

    # -- tier switches -----------------------------------------------------
    #
    # A disabled tier contributes no candidates. It is not thresholded out
    # of contention, which would leave it able to return something; it is
    # not consulted at all.

    def _k_retrieve_widened(self, query_embedding, episodes):
        if not self.config.k_enabled:
            return [], {}
        return super()._k_retrieve_widened(query_embedding, episodes)

    def _n_retrieve_widened(self, episodes):
        if not self.config.recency_enabled:
            # The generation table is still read: it is state the carried
            # engine maintains, and skipping it would change more than the
            # tier switch.
            super()._n_retrieve_widened(episodes)
            return [], {}
        return super()._n_retrieve_widened(episodes)

    # -- retrieval ---------------------------------------------------------

    def retrieve(
        self,
        user_message: str,
        turn_number: int,
    ) -> ContextMatchedStmResult:
        rule_episodes = self._fetch_rule_episodes(get_all_rules(self.conn))
        rows = get_all_episodes_with_embeddings(self.conn)
        episodes = self._deserialize(rows)

        if self.config.k_enabled:
            query_embedding = self._embedding_provider(user_message)
            k_candidate_ids, all_k_scores = self._k_retrieve_widened(
                query_embedding,
                episodes,
            )
        else:
            # No K tier means no query vector is needed. Embedding the
            # query anyway would spend a call the arm does not use and
            # would make the arms differ in calls as well as in tiers.
            k_candidate_ids, all_k_scores = [], {}
        n_candidate_ids, all_n_scores = self._n_retrieve_widened(episodes)

        by_id = {
            str(episode["id"]): self._clean_episode(episode)
            for episode in episodes
        }
        n_candidate_set = set(n_candidate_ids)
        for episode_id in k_candidate_ids:
            if episode_id in by_id and episode_id not in n_candidate_set:
                by_id[episode_id] = {
                    **by_id[episode_id],
                    "similarity": all_k_scores[episode_id],
                    "provenance": "stm",
                }

        state = build_tier_state(
            probe_turn=turn_number,
            n_candidate_ids=[i for i in n_candidate_ids if i in by_id],
            k_candidate_ids=[i for i in k_candidate_ids if i in by_id],
            by_id=by_id,
        )
        packed = pack_arm(state, arm=self.config.order, budget=self.payload_budget)

        delivered_ids = set(packed.selected_ids)
        delivered_n_ids = [
            str(episode["id"]) for episode in packed.recent_episodes
        ]
        delivered_k_only_ids = [
            str(episode["id"]) for episode in packed.stm_episodes
        ]
        delivered_k_ids = [
            episode_id
            for episode_id in k_candidate_ids
            if episode_id in delivered_ids
        ]
        dropped = set(packed.dropped_ids)

        if packed.selected_ids:
            update_retrieval_metadata(
                self.conn,
                list(packed.selected_ids),
                datetime.now(timezone.utc).isoformat(),
            )
        k_scores = {
            episode_id: all_k_scores[episode_id]
            for episode_id in delivered_k_ids
        }
        n_scores = {
            episode_id: all_n_scores[episode_id]
            for episode_id in delivered_n_ids
            if episode_id in all_n_scores
        }
        self._log_retrieval_events(
            turn_number,
            episodes,
            delivered_k_ids,
            k_scores,
            delivered_n_ids,
            n_scores,
        )

        prompt = build_stm_context(
            system_prompt=self._system_prompt,
            current_user_message=user_message,
            rule_episodes=rule_episodes,
            recent_episodes=list(packed.recent_episodes),
            stm_episodes=list(packed.stm_episodes),
        )
        if extract_stm_payload(prompt) != packed.payload:
            raise AssertionError("Packed payload differs from live prompt")
        rule_text = render_rules_block(rule_episodes)

        result = ContextMatchedStmResult(
            k_episode_ids=delivered_k_ids,
            k_scores=k_scores,
            n_episode_ids=delivered_n_ids,
            n_scores=n_scores,
            constructed_prompt=prompt,
            estimated_tokens=len(prompt) // 4,
            n_total_in_store=len(episodes),
            rule_episodes=rule_episodes,
            rule_token_estimate=(len(rule_text) // 4 if rule_episodes else 0),
            recent_episodes=list(packed.recent_episodes),
            retrieved_stm_episodes=list(packed.stm_episodes),
            payload_budget=self.payload_budget,
            retrieval_payload_chars=packed.serialized_chars,
            retrieval_payload_sha256=hashlib.sha256(
                packed.payload.encode("utf-8")
            ).hexdigest(),
            n_candidate_count=len(n_candidate_ids),
            k_candidate_count=len(k_candidate_ids),
            n_candidate_ids=list(n_candidate_ids),
            k_candidate_ids=list(k_candidate_ids),
            delivered_k_only_ids=delivered_k_only_ids,
            n_k_duplicate_ids=[
                episode_id
                for episode_id in k_candidate_ids
                if episode_id in n_candidate_set
            ],
            n_candidate_last_generations={
                episode_id: self._last_generations.get(episode_id)
                for episode_id in n_candidate_ids
            },
            skipped_n_ids=[i for i in n_candidate_ids if i in dropped],
            skipped_k_ids=[i for i in k_candidate_ids if i in dropped],
        )
        self.last_result = result
        return result


def arm_accounting(arm: str) -> dict:
    """What this arm claims to be, for the run header."""

    config = ARM_CONFIGS[arm]
    return {
        "arm": config.arm,
        "label": config.label,
        "recency_enabled": config.recency_enabled,
        "k_enabled": config.k_enabled,
        "packing_order": (
            "recency -> K" if config.order == "B0" else "K -> recency"
        ),
        "served_by": (
            "deployed code in a separate worktree"
            if config.arm == CONTROL_ARM
            else "src/tier_isolation/study011.py"
        ),
    }
