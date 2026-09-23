# AF-PRE-010 (registered before code runs, 2026-09-21): does an anchor miss cost the deployed system anything?

**Question.** The AF arc scores top-1 against LoCoMo's *earliest evidence turn* (AF-PRE-005:
56/120, `a237be71`; audit AF-PRE-009: 64 misses, `88669824`). The product does not pick one turn:
it **delivers a pack** to a reader. Nothing in this arc has shown that picking the earliest
evidence turn changes what the deployed context contains. This probe measures, with **zero model
or reader calls**, whether the 64 misses changed delivered evidence at all.

**Why now.** Two of AF-PRE-009's findings say the metric and the product want different things:
E1 (10 misses) returned *other* annotated evidence — delivery succeeds under the metric's failure;
X1 (32 misses) has the answer value in no turn, which is a *coverage* question, not a top-1 one.
If most misses are delivery-neutral, then 56/120 is a non-operational metric and the arc's
product-facing claim is only the E-gap delivery result (17/17 anchors absent from context,
recovered) — and the reader pilot must not be funded.

## Populations and inputs (all committed; read-only)

- `unified_anchor/artifacts/sample2.json` — the frozen 120 items (AF-PRE-009 input).
- `miss_audit/artifacts/e5_subpartition.json` (`88669824`) — per-item hit/miss, gold, prediction,
  answer-presence. 64 misses; **the 120-item item set is the audit's, unchanged.**
- **D-product:** `experiments/comparisons/hh_003/artifacts/run/A_EPISODIC/contexts.json` — the
  episodic read path at a 32,000-char budget, **1,540 LoCoMo items, 10 conversations,
  120/120 of sample2 covered** (`38e46b20`). Primary measure.
- **D-ranked:** `biological_memory/nf_004/artifacts/g6_holdout_outcomes.json` — the NF-004
  confirmation arms (`P_PAIR_RANK` 16k/32k, `S_SESSION_RANK` 16k/32k, `SOURCE_ORDER`) with
  `any_evidence` / `all_evidence` / `best_evidence_rank`; **63/120 items, 6 conversations**.
  Secondary measure, different packer, reported separately — never pooled with D-product.
- **D-comp:** `hh_004/artifacts/run/A_DA098_ARCH32_DECODED/contexts.json` — compressed pack,
  63/120 items; used only to check that the delivered-turn identity recovery is correct against
  its own `units_delivered` field (absmax mismatch 1, zero duplicate turn texts within a
  conversation, `38e46b20`).

## Delivered-set recovery (the one new mechanism, and its gate)

NF-004 gives evidence flags but not turn identities; the contexts files give rendered text. For an
item, the delivered turn set is the set of turns whose exact rendering (`"{speaker}: {text}"`)
occurs as a line of that item's context string. Within a conversation LoCoMo turn texts are unique
(0 duplicate texts, `38e46b20`), so a line match names one turn.

**Identity gate (run before any reported number):** on D-comp, recovered-vs-`units_delivered`
mismatch must be ≤ 1 for every item (observed at PF4); on D-product, the share of context lines
that match no turn is reported (the episodic arm renders consolidated blocks, so unmatched lines
are expected and delivered evidence is a **lower bound** — stated in Limits). If the D-comp gate
fails, identity recovery is abandoned and only NF-004's own flags are reported.

## Measures (all mechanical, no reader)

For each of the 120 items, split by AF-PRE-009 hit/miss:

- **(i) annotated-evidence delivery:** `any` / `all` of the item's annotated evidence turns in the
  delivered set. For NF-004 this is its registered `any_evidence` / `all_evidence`, reused as
  committed — not recomputed.
- **(ii) answer-bearing delivery:** at least one delivered turn contains the answer value under
  AF-PRE-009's **frozen** presence rule (lowercase, strip punctuation, substring or all content
  tokens len > 2 outside the 40-word stop list). Same function, no new parameters.
- **cost_set:** misses where **neither** `all` annotated evidence **nor** any answer-bearing turn
  was delivered — the items where forcing the anchor into the pack could change what the reader
  sees. This is the only quantity that can justify a reader pilot.

## Registered dispositions (fixed before the joint numbers exist)

`silent_rate` = share of in-population misses satisfying (`all` evidence **or** answer-bearing
delivered), on D-product:

- **OPERATIONAL_SILENT** if `silent_rate` ≥ 0.80 — the top-1 anchor result carries no delivery
  consequence; 56/120 is declared a non-operational metric for the product, the reader pilot is
  **not** registered, and the arc's product-facing claim is limited to the E-gap delivery result.
- **OPERATIONAL_COST** if `silent_rate` < 0.50 — a reader pilot is registerable.
- **MIXED** between them: pilot registerable only if `|cost_set|` ≥ 10.

**Power fact (PF4, registered now).** Under D-ranked at 16k, 23/36 in-population misses already
deliver *all* annotated evidence and 3 deliver none (`38e46b20`), so `cost_set` is arithmetically
bounded by roughly a dozen items. A paired exact test cannot reach p < .05 on fewer than ~10
discordant items even with a perfect effect; that is why the pilot threshold is a count and not a
p-value, and why an OPERATIONAL_SILENT outcome closes the pilot rather than deferring it.

**Hits control.** The same two measures on the in-population **hits**. If the delivery rate differs
by less than 15 points between hits and misses, top-1 anchor accuracy is statistically unrelated to
what the deployed pack contains, independently of any threshold choice. (Hits are not trivially
delivered: the pack is built by a different system than the reranker.)

## Preflight (`PREFLIGHT.md` §4)

- **PF1 inputs:** the four committed artifacts above, each counted now: sample2 120; audit items
  120/64; D-product 1,540 items / 120 covered / 10 conversations; D-ranked 1,104 rows / 63 covered
  / 6 conversations; D-comp 842 items / 63 covered. All read-only, none written.
- **PF2 mechanism identity:** the "deployed pack" is the committed output of the arm named in each
  file (`A_EPISODIC`, budget 32,000; `P_PAIR_RANK`, budget 16,000/32,000). No pack is rebuilt and
  no arm is re-simulated here; the probe reads the artifact of the system, not a model of it.
  The currently adopted 0.3.0 timeline composition has **no** per-item LoCoMo pack artifact, so
  this audit cannot speak to it (Limits).
- **PF3 gate ordering:** identity-recovery gate executes before any measure is written; on failure
  the script writes only the gate report.
- **PF4 reachability:** dispositions reachable in both directions by construction (`silent_rate`
  is 0–100%); the pilot threshold is paired with the registered power bound above rather than
  claimed achievable; the cost_set upper bound is a measured fact, not assumed.
- **PF5 comparison keys:** `(sample_id, qa_index)` — present in sample2, derivable in the audit
  file, and stored as `source_index` in all three artifact families. No generated ids. Note the
  D-product/D-ranked join is on these keys only; items absent from D-ranked are excluded from the
  secondary measure and counted.
- **PF6 reproduction anchor:** the audit's 64/120 split is read from `e5_subpartition.json`,
  asserted to contain exactly 120 items and 56 hits; NF-004's own counts are asserted against its
  committed `P_PAIR_RANK` totals on its 63 covered items before use.
- **PF7 absorbing states:** n/a — no feedback loop, single pass over frozen artifacts.
- **PF8 adequacy:** this measures whether *content was delivered*, which is necessary but not
  sufficient for a correct answer. HH-004 is the precedent that an evidence ceiling did **not**
  transfer to answer accuracy, so an OPERATIONAL_SILENT result means "no measurable delivery
  cost", never "no answer cost". It cannot detect a reader-side benefit of ordering.
- **PF9 surrogate audit:** `all_evidence` can be true while the reader still fails (dilution,
  NF-005/NF-006); the answer-value rule can be true of a turn that does not answer (an answer
  mentioned in passing) and false of a turn that legitimately does (inference items, X1). Both
  directions are recorded as residuals; the two measures are reported side by side precisely
  because neither alone certifies "the reader could answer".
- **PF10 live evaluation:** availability is not a verdict. This probe can only decide whether a
  reader pilot is *worth running*; it cannot produce a capability or product claim.

## Limits (pre-stated)

Coverage is 63/120 for the NF-004 arms (6 of 10 conversations) — the secondary measure is not a
population estimate. D-product's episodic arm renders consolidated blocks, so its delivered set is
a **lower bound** and its `silent_rate` is conservative in the direction of calling misses costly.
Answer-value presence is lexical (AF-PRE-009's registered residual). No reader, no model, no
retrieval calls; characterization only under the standing partition ruling — no claim transfers to
the adopted 0.3.0 composition until a reader pilot says so.
