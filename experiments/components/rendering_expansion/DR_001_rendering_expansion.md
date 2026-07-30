# DR-001 - Rendering Expansion Defect and Fix

**Type:** Decision record. **Not a study.** No inference run, no
pre-registration, no score, and no study verdict.
**Repository:** `contextDecayWindow`
**Branch:** `fix/rendering-expansion`
**Status:** LOCKED by the commit that first adds this file
**Date:** 2026-07-29
**Companions:** `AS_001_q4_packing_reanalysis.md`;
`experiments/audits/scoring_integrity/PROTOCOL_scoring_integrity.md` (not
implicated)

## 1. Defect

The production source-episode renderers add repeated tags, retrieval metadata,
indentation, and separators to every episode. The budget authority for LTM
episode rendering charges only the concatenated user and assistant content, not
the serialized element the model receives. The widened-STM packer charges its
full payload exactly, but uses the same expanded episode structure.

The result is an avoidable loss of usable context and, on the LTM path, an
accounting mismatch between the selection budget and the rendered block.

### 1.1 Historical observations

| Quantity | Value | Artifact |
|---|---:|---|
| Study 010 Arm L block at Q13 | 31,991 chars | `runs/study_010_full_001/arm_l/constructed_prompts/turn_999.txt` |
| Study 010 Arm L block at Q14 | 31,847 chars | `runs/study_010_full_001/arm_l/constructed_prompts/turn_1000.txt` |
| Registered `B_ltm` | 32,000 chars | Study 007 pre-registration at `d920fd8` |
| Study 010 distilled spans | 18,951 raw chars | Study 010 store artifact |

The 31,991/18,951 comparison is store-level, not per-record. It cannot estimate
an expansion ratio or recovered slots. The delivered block contains selected
source episodes; the raw quantity covers every stored distilled span.

### 1.2 Scope correction to the supplied draft

Artifact inspection before lock found that the supplied draft's statement
"the expansion is structural, not content" was too broad. Study 008 explicitly
registered episode rendering as the entire source user/assistant turn and span
rendering as a separate factor. The current episode renderer therefore expands
a distilled span in two ways:

1. **Registered content expansion:** the selected span resolves to its whole
   source episode.
2. **Structural expansion:** tags, attributes, indentation, and separators.

This record fixes only item 2 and exact-cost accounting. Replacing source
episodes with stored spans would change a previously registered rendering
factor and is prohibited here.

This correction is authorized by the author's 2026-07-29 instruction that
amendments are allowed. It narrows the fix rather than making any criterion
easier.

## 2. Locked renderer contract

Source-episode content remains byte-identical after HTML escaping. Each episode
is serialized as:

```text
<episode turn="TURN">
<user>USER_MESSAGE</user>
<assistant>ASSISTANT_MESSAGE</assistant>
</episode>
```

The enclosing block identifies whether the episode is recent, STM-retrieved, or
LTM-retrieved. The element retains only:

| Element | Reason retained |
|---|---|
| `<episode>` boundary | Separates independently retrieved turns |
| `turn` | Supports temporal attribution and updates |
| `<user>` / `<assistant>` | Preserves speaker attribution |
| escaped message text | Preserves the registered whole-source content |
| enclosing block | Preserves retrieval-tier provenance |

The model-facing element removes `topic`, `similarity`, `promoted_at_turn`,
`trigger_type`, `distilled_id`, `dream_event`, `event_type`, `source_turns`,
indentation, and verbose message tag names. Those values remain in observability
logs; none is required to attribute or separate the episode.

The contract applies to the duplicated source-episode serializers in
`context_builder.py` and `stm_context_builder.py`. Span rendering, rule
rendering, current-turn rendering, store contents, retrieval, ranking, N/K,
floor/fill, packing order, and containment logic are unchanged.

## 3. Measurement

Before renderer code changes, commit per-episode measurements for:

1. Study 010 Arm L Q13 (turn 999).
2. Study 010 Arm L Q14 (turn 1000).
3. Retrieval bakeoff Tier 6 corrected Q4 (turn 115).

For each historically delivered episode, report:

- stable episode identity and source turn;
- stored span length when a distilled span exists;
- source user/assistant content length;
- pre-fix serialized element length;
- structural overhead (`serialized - escaped source content`);
- block-level delivered episode count and serialized characters.

Report distributions with minimum, p25, median, p75, p95, maximum, and total.
Do not report a global store/block ratio as a per-episode measurement.

## 4. Replay gates - binding

### G-R1 - pre-fix replay

On unmodified renderer code, reconstruct the Study 010 Arm L Q13 and Q14 LTM
blocks from the immutable run database and historical selected-episode log.
Require character identity, SHA-256 identity, episode identity/order identity,
and no source-tree mutation.

- PASS: commit the replay and measurement artifacts, then implement.
- FAIL: STOP. Diagnose the harness before touching renderer code. AS-001 is
  void until this gate passes.

The original run header records Qwen3.6 27B UD-Q6_K_XL, llama.cpp build 9294
(`0f3cb3fc8`), RTX 5090 32 GB, `--ctx-size 50000`, q8_0 KV, seed 5005,
`--parallel 1`, and speculative decoding off. This replay is offline and makes
no inference call; it records and verifies that historical runtime provenance.

### G-R2 - post-fix replay

Load the same historically selected episode identity/order list used by G-R1
and serialize it with the compact renderer. Require:

- selected episode identity and order unchanged;
- source user/assistant content unchanged after unescaping;
- only structural serialization differs;
- post-fix block SHA and length recorded;
- no source-run artifact mutation.

G-R2 isolates serialization. Production capacity under exact post-fix costs is
reported separately and must not be substituted for this identity gate.

### Determinism spot-check

Run each offline replay twice in separate processes and require byte-identical
JSON/CSV artifacts after excluding no fields. A timestamp is therefore
prohibited in generated evidence.

## 5. Exact serialized cost

The production renderer is the sole cost authority.

- Per-episode cost is the exact serialized element plus its block separator.
- Non-empty block opening and closing tags are charged once.
- An empty block remains representable within its exact serialized cost.
- Selection must assert that the rendered LTM block length is at most
  `B_ltm`.
- Observability reports both content characters and serialized characters.

The fix reduces structural cost; it does not estimate cost from stored text.

## 6. Downstream re-derivation

No parameter may be tuned from post-fix outcomes. Re-derivation uses existing
registered values and mechanical invariants:

| Parameter | Locked treatment |
|---|---|
| `B_ltm` | Keep the registered 32,000-char production allocation. Report capacity over the existing Study 007 sweep: 16k, 20k, 24k, 28k, 32k, 36k, 40k, 48k, 64k. A smaller production budget requires a separately authorized design. |
| N candidate cap | Keep 32. Verify the Q4 turn-55 episode remains rank 27 and therefore in-cap. |
| N-first packing | Flag only. AS-001 may indict it; this record cannot change it. |
| Per-domain floor | Keep the registered policy. Replay the Study 007 probes over the existing sweep and report whether the floor remains protected under exact costs. |
| Containment dedup | Keep unchanged. Prove by tests that content identity, not serialization, remains its authority. |

Each result must trace to the artifact and code SHA used to compute it.

## 7. Surrogate audit

| Check | Can pass falsely? | Mitigation |
|---|---|---|
| G-R1 block-length match | Yes, with different content | Require character and SHA identity |
| G-R2 selected-count match | Yes, with compensating identity changes | Require identity and order equality |
| "Overhead reduced" | Yes, if content was removed | Compare unescaped source content per identity |
| More fitted episodes | Yes, while fewer content chars are delivered | Report episode and content-char totals jointly |
| Test-suite pass | Yes, without exact-cost coverage | Add committed serialized-cost fixtures |

Accepted residual: offline checks cannot establish that the model attributes the
compact tags correctly. No inference is authorized here, and AS-001 establishes
availability rather than answer correctness.

## 8. Deliverables

- [ ] Pre-fix per-episode distributions for all three blocks.
- [ ] G-R1 PASS committed before renderer changes.
- [ ] Compact renderer with per-element retention rationale.
- [ ] Exact serialized-cost selection and regression fixtures.
- [ ] G-R2 PASS with identity/order and content invariants.
- [ ] Post-fix per-episode distributions.
- [ ] Downstream re-derivation table and containment test.
- [ ] `README.md` and `AGENTS.md` updated in the same PR.
- [ ] `ERRATA.md` assessment recorded, including a no-change decision if the
      historical measured numbers remain correct.
- [ ] Independent correctness-fix PR.

## 9. Exclusions

No inference run, score, or architectural verdict is produced. This record does
not change source-episode content, span rendering, store formation, selection
ranking, N, K, floor/fill, packing order, or any committed run artifact.

