# Study 003 — Protocol Amendment 002: Topic Representation

**Recorded:** July 2026, after Amendment 001's 35-turn re-verification remained NO-GO.

## Diagnosis

The topic manager received embeddings of `User + Assistant` episode text. Assistant responses are substantially longer and vary in structure even within the same scripted domain. As a result, generation-style variation fragmented the continuous civil-engineering phase into topic clusters and triggered premature LTM promotion.

## Amendment

Topic assignment and consolidation centroids will use a 1,024-dimensional embedding of the **user message only**. The stored episode embedding remains the full `User + Assistant` representation and continues to be used for retrieval and LTM storage/scoring. This separates domain classification from generation variation without changing the embedding model, filter definitions, weights, thresholds, script, rubric, or study scope.

## Required re-verification

Run a fresh 35-turn iterative ablation. Promotion must not occur during turns 1–30, must fire after the first turn-31 Renaissance-art episode is stored, and `ltm_episodes.episode_id` must remain unique.
