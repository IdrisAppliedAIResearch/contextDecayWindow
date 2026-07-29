# DR-001 - Rendering Expansion Report

**Type:** component correctness report; not a study
**Status:** PASS
**Design anchor:** `094cbea2`
**Amendments:** `ad74b991`, `2d453cbe`
**Implementation:** `202b1883`
**G-R1 evidence:** `4046fd4c`
**G-R2 evidence:** `20227d59`
**Downstream re-derivation:** `4aa3bf4a`

## Outcome

The source-episode renderer had two distinct properties that the supplied draft
had conflated. Whole-source rendering was a registered content choice; it was
not changed. Repeated diagnostic markup was structural overhead, and LTM budget
selection did not charge it.

The fix introduces one shared compact episode element:

```text
<episode turn="TURN">
<user>USER_MESSAGE</user>
<assistant>ASSISTANT_MESSAGE</assistant>
</episode>
```

Turn and speaker attribution remain model-visible. Topic, similarity,
promotion, dreaming, and distilled-record metadata remain in observability logs
but no longer consume the model window. LTM selection now charges the complete
serialized block, including wrappers and separators.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| G-R1 pre-fix replay | PASS | Study 010 Q13/Q14 matched committed prompts character-for-character and by SHA-256 |
| Pre-fix determinism | PASS | Two separate processes emitted byte-identical CSV/JSON/Markdown |
| G-R2 identity/order | PASS | 80/81 Study 010 and 15 bakeoff identities remained in historical order |
| G-R2 source content | PASS | Every compact element parsed back to the original user/assistant strings |
| Post-fix determinism | PASS | Two separate processes emitted byte-identical artifacts |
| Source integrity | PASS | Every immutable input hash matched before and after |

## Measurements

| Block | Episodes | Pre-fix chars | Post-fix chars | Reduction |
|---|---:|---:|---:|---:|
| Study 010 Q13 | 80 | 53,726 | 37,619 | 16,107 |
| Study 010 Q14 | 81 | 53,839 | 37,545 | 16,294 |
| Bakeoff Tier 6 Q4 historical payload | 15 | 59,708 | 58,808 | 900 |

The historical Study 010 `ltm_chars_used` values, 31,991 and 31,847, were
undercharged source-content totals. They were not serialized block lengths.
Amendment 001 and `ERRATA.md` preserve and correct that distinction.

## Re-Derivation

The existing registered budget sweep was replayed with the carried,
hash-verified embedding model and no generative calls.

| Parameter | Decision | Evidence |
|---|---|---|
| `B_ltm` | KEEP 32,000 | Fixed context allocation; changing it requires a new design |
| N cap | KEEP 32 | Q4 turn-55 remains rank 27 and in-cap |
| Per-domain floor | KEEP `k_min=1` | Every represented topic retained its floor at 32k |
| Containment dedup | KEEP | Source-episode identity invariant passed |
| N-first packing | FLAG ONLY | AS-001 owns the Q4 packing decision |

At exact 32k cost, Study 010 Q13/Q14 select 69 and 71 episodes and serialize to
31,993 and 31,796 characters. Study 007's two probes select 8 and 9 episodes.
The full 16k-64k frontier and selected identities are committed in
`artifacts/rederivation/rederivation.json`.

## Integrity and Limits

- No generative inference or new conversation run occurred.
- Amendment 002 authorizes four deterministic query embeddings because rejected
  candidate scores were not preserved in historical logs.
- No run artifact, score, selection rule, N/K value, floor policy, packing
  order, span renderer, or store record changed.
- G-R2 establishes availability and content identity, not whether a model would
  attribute the compact format correctly under inference.
- AS-001's post-fix Q4 fitted-slot count was not opened in this branch.

## Deliverables

- [x] Locked design before implementation.
- [x] Pre-fix distributions for three blocks.
- [x] G-R1 and deterministic repeat.
- [x] Compact renderer and exact-cost tests.
- [x] G-R2 and deterministic repeat.
- [x] Post-fix distributions.
- [x] Budget, cap, floor, packing, and containment re-derivation.
- [x] `README.md`, `AGENTS.md`, `ERRATA.md`, and memory update.
- [ ] Independent correctness-fix PR.
