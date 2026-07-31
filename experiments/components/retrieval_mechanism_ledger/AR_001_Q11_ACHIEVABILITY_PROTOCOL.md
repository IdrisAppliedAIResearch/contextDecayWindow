# AR-001 Q11 Exact-Budget Achievability Protocol

**Status:** PROSPECTIVE - no achievability output generated
**Type:** Post-hoc offline bar audit; no model, retrieval, or inference
**Parent:** `RETRIEVAL_MECHANISM_LEDGER.md`
**Decision affected:** Interpretation of F1, not the registered E002 outcome

## Question

What is the minimum exact serialized character cost of any eligible set of raw
episodes whose rendered payload contains at least 14 of the 17 registered Q11
atomic items?

If the exact minimum is at most 32,000 characters, the Q11 bar is achievable
from the committed store at the enforced budget and F1 remains a retrieval
problem. If the minimum exceeds 32,000 characters, the bar is unreachable from
this store under the current rendering and budget policy; F1 is a budget or
capture problem rather than a retrieval-mechanism problem.

This audit cannot change E002's locked criterion or KILL after output.

## Inputs

- Corrected Tier 6 committed turn log:
  `experiments/surveys/retrieval_bakeoff/tier6/runs/`
  `tier6_live_121_corrected_001/context_matched_stm/logs/turns.jsonl`.
- Eligibility: every row with a non-empty `stored_episode_id` and
  `turn_number < 120`.
- Episode identity and content: `stored_episode_id`, `turn_number`,
  `user_message`, and `assistant_message` reconstructed only from the committed
  turn log. The ignored local `study.db` is not read.
- Atomic items: the 17 committed `ATOMIC_ITEMS` used by the corrected Tier 6
  and E002 measurement layers.
- Renderer: post-DR-001 `render_episode_element` through
  `render_stm_payload([], selected_episodes)`.
- Budget: 32,000 Python characters over the complete two-block serialized
  payload.

The input log, renderer source, atomic-item source, protocol, and execution
source are hashed in the output. Mechanism code is not invoked.

## Coverage

Normalize rendered episode text exactly as E002 does: Unicode NFKD, remove
combining characters, and lowercase. An episode covers an atomic item when the
item's committed normalized needle occurs in that normalized rendered episode.

Episodes covering no Q11 item are excluded from optimization but remain counted
in the inventory. A selected set's reported coverage is recomputed from its
complete rendered payload, not inferred only by unioning episode masks.

## Exact Minimum

Greedy set cover does not establish a minimum. The authoritative result uses
dynamic programming over all `2^17` fact-coverage masks.

For each eligible episode, compute:

- its 17-bit coverage mask; and
- its additive serialized weight, `len(render_episode_element(episode)) + 1`.

The `+1` is the inter-line separator contributed by each episode inside the
non-empty `<retrieved_stm>` block. The fixed two-block wrapper cost is added
once. The resulting cost must equal
`len(render_stm_payload([], selected_episodes))`; mismatch is fatal.

For every reachable coverage mask, retain the candidate with:

1. lowest exact serialized cost;
2. fewest episodes;
3. lexicographically lowest sequence of `(turn_number, episode_id)`.

The authoritative threshold solution is the best retained mask with at least
14 set bits under the same tie-break. The analysis also reports exact minima
for every achievable fact count from 0 through 17.

## Greedy Check

Run deterministic greedy set cover as a descriptive upper bound. At each step,
choose the remaining episode by:

1. highest newly covered facts per additive serialized character;
2. highest newly covered fact count;
3. lowest additive serialized weight;
4. lowest source turn;
5. lowest episode ID.

Stop when 14 facts are covered or no episode adds coverage. Greedy is never
called the minimum and cannot determine bar unreachability.

## Domain Analysis

For each of the four Q11 domains, run the same exact optimization restricted to
that domain's fact mask and require all facts in that domain:

- civil: 5/5;
- art: 4/4;
- monetary: 4/4;
- marine: 4/4.

Report each domain's minimum complete payload cost, selected episode identities,
turns, per-episode serialized costs, and covered items. Also report the
domain/item composition and episode costs of the global 14-item optimum. If one
episode covers multiple domains, display all of them rather than assigning its
cost to one domain.

These are independent domain optima and are not additive because episodes and
fixed wrappers can overlap.

## Gates

- Input turn log is tracked at `HEAD`.
- Exactly 119 eligible stored episodes exist before Q11.
- Exactly 17 unique atomic items across domain sizes 5/4/4/4 exist.
- Every atomic item is present in at least one eligible episode; otherwise the
  store itself makes the bar unreachable and the missing item is reported.
- Exact dynamic-programming output reproduces its rendered payload cost and
  coverage.
- A synthetic small-corpus test compares the dynamic program with exhaustive
  subset enumeration.
- Repeated execution produces byte-identical result artifacts.

## Outputs

- `artifacts/ar_001/achievability.json`
- `artifacts/ar_001/exact_frontier.csv`
- `artifacts/ar_001/episode_coverage.csv`
- `artifacts/ar_001/global_optimum_payload.txt`
- `artifacts/ar_001/AR_001_report.md`
- deterministic rerun and source-hash manifest

The report must state one of:

- `ACHIEVABLE_AT_32K`;
- `UNREACHABLE_AT_32K`;
- `STORE_INCOMPLETE`;
- `INVALID` if any integrity gate fails.
