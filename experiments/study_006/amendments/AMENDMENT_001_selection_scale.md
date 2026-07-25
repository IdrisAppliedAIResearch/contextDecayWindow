# AMENDMENT 001 — Per-Topic Cap Rescaled for Span Granularity

**Study:** 006
**Date:** 2026-07-25
**Amends:** `experiments/study_006/pre_registration.md` (LOCKED v1, SHA `5def302`)
**Trigger:** Retrospective Replay Gate failure — `experiments/study_006/replay/replay_report.md`
**Status:** REGISTERED before re-replay and before any live run.

---

## 1. Why this amendment exists

The pre-registered policy failed its own Retrospective Replay Gate at **0 of 4
domains**. The pre-registration anticipates this and specifies the response:

> **If the gate fails:** do not run. Revise the policy (or re-derive F) against
> replay data, record the revision in a decision record, and re-replay.
> Parameters that ship must be justified by replay evidence, not by post-hoc
> tuning on a live run.

This amendment is that revision. It changes **one parameter value** and clarifies
**one application rule**. It adds no pipeline component and does not touch the
read path, arbitration, tagging, cadence, the raw store, or the extractive
constraint.

## 2. The defect

**The per-topic cap was never rescaled when the selection unit changed.**

The pre-registration carried **C = 3** from Study 005 while changing the selection
unit from whole turns to sentence-level spans. Study 005 selected 3 records from
~30 episodes — a **top-10%** requirement. Study 006 selected 3 from 177–393
spans — a **top-1%** requirement.

Span granularity multiplied the candidate pool roughly tenfold and the cap was
held fixed, so **selection became about ten times harder rather than easier.**
That single carried-over constant is the whole failure: the planted facts were
ranked 6th, 29th, 36th and 8th in their topics — all comfortably inside a
proportionally equivalent cap, and all outside a cap of 3.

## 3. Changes

| Item | Pre-registered | Amended |
|---|---|---|
| Per-topic cap C | 3 | **50** |
| Coverage floor F application | top span only | **per span** |

Everything else in the selection policy is **unchanged**, including the salience
formula, which remains exactly as pre-registered:

```
base(s)     = named_entity_count(s) + 2 × numeric_token_count(s)
density(s)  = base(s) / word_count(s)
salience(s) = density(s) × source_weight(role)      # user 1.5, assistant 1.0
```

**Why the floor now applies per span.** Under C = 3 the distinction was almost
never observable — the top three spans in a real topic all cleared F comfortably.
At C = 50 it decides the outcome: a top-span-only test would admit up to fifty
spans on the strength of the first one, writing bare acknowledgments into the
store as facts. Per-span application is also what F's own pre-registered
definition asks for — *"minimum density-scaled salience to count as a salient
fact"*. The marker path is unchanged: if no span clears F, a single
`present_no_salient_fact` marker is written and no sub-floor span is ever
promoted to satisfy coverage.

**F remains 0.15.** The value is unchanged and needs no re-derivation, because
the salience scale it sits on is unchanged. This satisfies S6-T-013. No post-run
F changes are permitted.

## 4. Explicitly unchanged

- **Salience formula** — density normalization by word count, the study's core
  correction, is untouched.
- **Source weights user 1.5 / assistant 1.0.** This matters. Source weighting is
  the most script-correlated parameter in the policy, because on this script the
  planted facts are user-authored. Weight sweeps up to 6.0 were evaluated and are
  **not adopted**: the amendment reaches 4/4 with the pre-registered weight
  untouched, so the gate is not being passed by tuning toward the answer key.
- ×2 numeric weight; 4–60 word eligibility window; dedup at 0.95 cosine; spaCy
  `en_core_web_sm` 3.8.0 segmenter and NER extractor; sentence-level granularity;
  character-offset provenance; the zero-inference-call extractive assertion.
- All three bars, including **Bar 1 at 4 of 4 domains**. The bar is not relaxed.
- The 121-turn script, seed 5005, and the full runtime configuration.

## 5. Alternatives evaluated and rejected

Recorded so the chosen revision can be judged against what it beat.

| Alternative | Result | Rejected because |
|---|---|---|
| Re-derive F only | 0/4 at every F from 0.05–0.30 | F gates *whether* records are written, never their order. It cannot promote a plant into the cap. |
| Raise the eligibility lower bound | 0/4 from 4 to 16 words | Improves plant ranks only marginally; never forms a domain. |
| Soften normalization to `base/√words` | 4/4 at C≥25 | **Breaks the adversarial fixture** — the plant stops leading, because √ normalization moves the policy partway back toward Study 005's absolute counting. Rejected on that basis. |
| Restrict candidacy to user spans | 3/4 | Reaches its ceiling by discarding ~90% of the pool, and is aligned with the answer key on this script. Never reaches 4/4 regardless. |
| Raise source weight to 2.0–6.0 | 3/4 max | Tunes the most script-correlated parameter, and still never reaches 4/4. |
| One span per source turn | 2/4 max | Can *remove* the plant when it is not the densest span in its own turn — marine's plant was filtered out by it. |

The exponent alternative deserves emphasis: it passed the replay gate and was
still rejected, because the adversarial fixture — authored before this failure —
caught that it weakened the very correction the study exists to test. **The
fixture constrained the amendment rather than the reverse.**

## 6. Evidence

Measured on replay data at the amended values, formula and weights unchanged:

| Domain | Eligible spans | Best plant rank | Within C=50 |
|---|---:|---:|---|
| civil_engineering | 320 | 6 | yes (margin 44) |
| renaissance_art | 393 | 29 | yes (margin 21) |
| monetary_policy | 327 | 36 | yes (margin 14) |
| marine_biology | 177 | 8 | yes (margin 42) |

**Compression is preserved.** A larger cap sounds like it must cost compression,
but spans are sentences where Study 005 stored whole turns:

| | Records | Chars | % of raw store |
|---|---:|---:|---:|
| Study 005 (C=3, whole turns) | 12 | 49,785 | 11.04% |
| Study 006 amended (C=50, spans) | 200 | 31,023 | **6.88%** |

Seventeen times as many records occupy **0.62×** the distilled text — better
compression *and* 4/4 formation.

**C = 50 rather than the minimum passing value.** C = 40 also reaches 4/4, but
leaves the binding domain (monetary, rank 36) a margin of 4. C = 50 gives every
domain at least 14 ranks of margin while staying well inside Study 005's
compression envelope. The cap was chosen for robustness, not to clear the bar.

## 7. Limitations — recorded, not minimised

**This value was selected using the replay data.** The pre-registration sanctions
re-deriving parameters from replay evidence and that is what was done, but the
consequence must be stated plainly: **the replay gate can no longer serve as
independent validation of C.** It validated C = 3 and rejected it; it has now
been used to choose the replacement.

Mitigating this, and worth weighing:

1. The amendment changes **one value**, with a structural argument that stands
   independently of the replay outcome: a cap calibrated for a 30-item pool was
   applied unchanged to a 300-item pool. That error is identifiable from the
   design alone.
2. The **adversarial fixture** (S6_004) was authored before the failure, is not
   modified by this amendment, and still discriminates between the two policies.
   It rejected the alternative revision that the replay gate would have accepted.
3. The **live 121-turn run** remains genuinely out-of-sample.

Risks carried forward:

- **`renaissance_art` and `monetary_policy` have the least margin.** Art is the
  same domain that drove Study 005's PARTIAL outcome. If either fails in the live
  run, that is a predicted failure, not a surprise.
- **`art_pigment` (rank 265), `art_patron_role` (rank 162), `marine_photophores`
  (64) and `marine_feeding` (85) remain unselected even at C = 50.** Bar 1 needs
  only one fact per domain, so formation is unaffected — but **Q5 and Q8 depend on
  exactly these facts**, so the Bar 3 regression risk recorded at lock is
  unchanged and arguably now confirmed in advance.
- **A 200-record store is ~17× larger than Study 005's 12.** Retrieval and
  arbitration were exercised at 12 records. Their behaviour at 200 is untested and
  is **not** modified by this amendment, since the read path is explicitly out of
  scope. This could help breadth (Q11 needs all four domains present) or hurt
  precision. It is an observational measure in S6_008, not a tuned parameter.

## 8. Required actions

1. Implement the cap change and per-span floor. — done in the commit carrying this file.
2. Re-run the Retrospective Replay Gate: 4/4 domains, zero non-content, 100% offset-verbatim.
3. Re-run the adversarial fixture; it must still discriminate between the Study 005 and Study 006 policies.
4. Record the outcome in the replay report and proceed to S6_006 only on a pass.

**Authorized by:** Muzaffer Ozen, Idris Applied AI Research — 2026-07-25
