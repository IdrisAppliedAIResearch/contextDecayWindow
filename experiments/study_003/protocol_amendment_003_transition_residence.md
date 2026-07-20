# Study 003 — Protocol Amendment 003: Transition Residence Safeguard

**Recorded:** July 2026, after Amendment 002's 35-turn re-verification.

## Trigger

Amendment 002 produced the intended stable scripted domains: turns 1–30 were one civil-engineering topic and turns 31–35 were Renaissance art. It nevertheless emitted one zero-promotion event at turn 3 from a transient two-episode cluster that was later consolidated into the engineering domain. The event contradicts the pre-registered definition of exactly three genuine scripted transitions.

## Amendment

An outgoing canonical topic must contain at least **three episodes** before it may emit an LTM promotion event. Smaller transient clusters are ignored. This safeguard applies only to event emission; it does not alter embeddings, topic assignment, consolidation, filter scores, weights, or promotion thresholds. The scripted 30-turn domains exceed this requirement by construction.

## Required re-verification

Run a fresh 35-turn iterative ablation. `promotion_events.csv` must have no rows before turn 31 and one turn-31 row evaluating the 30 civil-engineering episodes.

## Re-verification outcome

The fresh run `ablation_35_amendment_003` met the transition criterion. `promotion_events.csv` contains exactly one row: turn 31, 30 episodes evaluated, and 15 promoted. No event occurred before turn 31. The run also retained unique LTM episode IDs and a stable 30-turn civil-engineering / 5-turn Renaissance-art topic split.
