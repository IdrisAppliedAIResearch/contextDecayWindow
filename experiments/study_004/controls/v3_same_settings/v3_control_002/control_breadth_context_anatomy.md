# Study 004 A005 v3 Control — Breadth-Context Anatomy

**Run:** `v3_control_002`

**Analysis date:** 2026-07-21

**Sequence:** Performed after the rubric score was committed at `6f34069` and
before the fresh v4 run.

## Method

The `k_episodes` and `n_episodes` recorded in the preserved turn log were
inspected for Q11 (turn 120) and Q14 (turn 121). A domain was marked present
only when its context episodes contained a correctly attributed planted
specific from the locked rubric. Domain names in the probe text do not count
as evidence, nor do coincidentally similar numbers from another domain.

Source: `iterative/logs/turns.jsonl`, SHA-256
`0AAA72CB9F40AFEE0F7FCEA0C99B8FADA74BF27FE40C3873EA91ED199C6AD7E8`.

## Q11 — turn 120

- K tier: turn 114 only (behavioral-rule recall); no planted domain fact.
- N tier: turns 1–9 and 119.
- Bridge engineering: present through early Halcyon Crossing episodes,
  including the planted project facts.
- Marine biology: present through turn 119, including photophore/mantle
  material.
- Renaissance art: absent. No episode from the turn-55–60 art block and no
  planted art specific appears in the selected context.
- Monetary policy: absent. No planted Federal Reserve, Taylor Rule,
  Dr. Priya Mehta, 2.3%, or 2% inflation-target evidence appears.

Turn 9 contains an unrelated seismic-design statement about a 2% probability
of exceedance in 50 years. It is not the planted 2% inflation target and is not
counted as monetary-policy evidence.

## Q14 — turn 121

- K tier: empty.
- N tier: turns 1–9 and 120.
- Bridge engineering: present through the early Halcyon Crossing episodes and
  repeated in the turn-120 response.
- Marine biology: present at least as the planted species entity repeated in
  the turn-120 response.
- Renaissance art: absent. The selected context contains no planted art
  specific.
- Monetary policy: absent. The selected context contains no correctly
  attributed planted monetary-policy specific; the unrelated seismic 2% value
  remains non-evidence.

## A005 attribution implication

The control failed both breadth probes while each probe context lacked the
Renaissance-art and monetary-policy specifics required for a pass. Therefore,
a later v4 breadth pass is eligible for read-path attribution if its probe logs
show those missing specifics arriving through LTM-provenance episodes. XML
tagging alone cannot create absent planted facts.

This check does not pre-score or assume the v4 outcome. Actual attribution
still requires the v4 Q11/Q14 responses to pass and the corresponding
arbitration/provenance logs to identify the necessary LTM episodes.
