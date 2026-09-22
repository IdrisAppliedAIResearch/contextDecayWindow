# ROUTE-001 — Question-Type Routing to Retrieval Mechanisms (draft v1, NOT LOCKED)

**Status: DRAFT for user review. Stages 0–1 are zero-LLM and can run alongside AF-READ-003.
Nothing here is pre-registered until the user approves and it is moved to the anchor_reader directory.**

---

## 1. Theory in one paragraph

Universal top-k retrieval (what B does today) applies one ranking function to a
question distribution whose failure modes are structurally different: temporal
questions need date arithmetic against record headers, multi-hop/enumeration
questions need set coverage across sessions, and single-hop semantic questions
are exactly what ANN ranking is good at. The 002 error forensics
(scratch/audit002_*, committed 65edf7ce) showed that 72% of B-arm misses have
zero gold evidence in the pack — misses concentrated in cat2 (temporal) and
multi-part cat1 — while the reader fails even with perfect context on relative
dates because nothing resolves them. A trained BERT-class router that
dispatches each question to a mechanism built for its structure, **with zero
additional LM (generation) calls**, targets exactly the misses that universal
retrieval cannot fix and the reader cannot fix. Deterministic (regex) intent
routing failed in the early Study-001 arc; a learned encoder router is the
second shot at the cornerstone.

## 2. What the 002 forensics already established (the econ)

From the audited 120 items (A=85, B=66, C=81):

| finding | number | implication |
|---|---|---|
| B misses with zero gold evidence in pack | 72% of 24 B✗∧A✓ | admission, not reading, kills B |
| Failure rate cat2 (temporal) | 45% of items | largest addressable class; universal ANN is structurally blind |
| Failure rate cat1 (multi-hop/enum) | 38% | second addressable class (set coverage) |
| Failure rate cat4 (single-hop) | 12% | semantic ANN is already near-parity — routing must not touch these |
| Relative-date anchoring failures with evidence present in BOTH arms | 7 items | fixable at WRITE time by date normalization — a mechanism no arm (A or C) has |
| Gold noise / judge-form floor (all classes) | ~11% of all items | irreducible; caps every condition equally |

**The write-time insight:** R-TEMP below does not only retrieve better — it
*rewrites* evidence with resolved absolute dates ("Starting tomorrow" + record
dated 27 Jul 2023 → "2023-07-28"). The anchoring failures that A and C both
suffered are fixed by construction. This is the one place ROUTE-001 could beat
arm A, not just arm B. Routing is the enabling mechanism; the transformation
is the novelty.

## 3. Classes and mapping

LoCoMo labels (train/test from question text only; category-5 adversarial
excluded from main as in 002/003):

- **TEMPORAL** (cat2) → R-TEMP
- **MULTIHOP** (cat1; enumeration subtype tracked separately in analysis) → R-MH
- **SEMANTIC** (cat3+cat4 pooled) → R-SEM (current ANN top-k, the control mechanism)

## 4. Router spec (zero additional LM calls — the cornerstone)

Two candidate routers, both evaluated in Stage 1; a lexical baseline is required:

1. **R1 — head-on-existing-embedding (preferred).** A linear/MLP head on the
   Qwen3-Embedding question vector that retrieval already computes. Marginal
   cost: microseconds and zero new model server. Routing for free out of the
   vector you already paid for.
2. **R2 — small encoder.** Fine-tuned DeBERTa/MiniLM-class classifier run on
   CPU. Still not an LM call; adds ~ms latency and one small model artifact.
3. **Baselines (mandatory):** (a) the failed deterministic regex router
   re-implemented with post-forensics lessons; (b) TF-IDF + logistic
   regression. **If TF-IDF-LR matches R1/R2, we report the dispatcher as the
   contribution, not the router pedigree — honestly.**

**Label-leakage protocol.** Dev questions are the eval set; a router trained on
them is leakage. Protocol: conversation-level K-fold CV (train on 9 of 10 LoCoMo
conversations' labeled questions, test on the held-out conversation; rotate).
Report CV accuracy and per-class recall/confusion. Additionally an **oracle-
dispatch** condition (gold labels, free) isolates router error from mechanism
headroom — the standard funnel decomposition, same discipline as 001.

## 5. Mechanisms (all non-generative)

- **R-SEM** = today's rank-then-top-k (unchanged control).
- **R-TEMP** = date-normalized retrieval:
  (a) *write time*: resolve every element's absolute date from its record header
  into the index; append `[abs date]` stamps into rendered evidence;
  (b) *query time*: deterministic date-expression parsing (dateparser library,
  regex — no LM) → candidate set = elements within parsed date window ∪ ANN
  top-k; rank by date-proximity blended with similarity;
  (c) render with absolute dates visible to the reader.
- **R-MH** = set-coverage retrieval: session-stratified selection (≤1–2 elements
  per session) + MMR diversity at the same token budget; second-pass expansion
  by NER-extracted entities from top-1 (spaCy-class tool, no LM); union packs.
- Token budget held at the B-arm budget so every comparison is accuracy-at-cost.

## 6. Stages and kill rules

**Stage 0 — oracle ceiling (zero LLM; run immediately, days).**
Build R-TEMP/R-MH packs for the 002 120 items with gold dispatch; measure
admission of gold evidence vs the actual B packs; convert to potential accuracy
with the observed 002 admission→correct conversion rate. **KILL if oracle
dispatch cannot lift B by ≥+8pp at ≤1.1× tokens** (below that, the whole
program cannot clear any reasonable bar and the answer is "scale changes
nothing", which 003 is already measuring for free).
Stage 0 also reports the per-class ceiling split: how much is admission vs the
write-time date-transformation bonus.

**Stage 1 — router feasibility (zero LLM).**
CV accuracy ≥0.85 macro AND ≥0.90 recall on TEMPORAL (the asymmetric class:
misrouting a temporal question to ANN recreates today's failure; misrouting a
semantic question to R-MH is nearly harmless — report the asymmetric-cost
matrix). **KILL if <0.85.** Report vs regex and TF-IDF-LR baselines. If the
lexical baselines match, proceed but reframe the claim.

**Stage 2 — mechanisms at gold dispatch (after 003 finishes, frozen server).**
Answer the 002 120 items under oracle dispatch (only re-ask items whose pack
changed vs B; A/C answers reused). Arms: B-universal (have), oracle-dispatch,
learned-dispatch. Metrics: accuracy, tokens, admission rate, per-class deltas.
Secondary headline test: **does R-TEMP beat arm A on cat2?** (the anchoring
claim — a result no budget-matched arm achieves today).

**Stage 3 — bars.**
WORKS = learned dispatch beats B-universal by ≥+8pp at ≤1.1× B-tokens AND
captures ≥50% of the oracle gain. DEAD = within noise of B-universal.
Then (if alive) ROUTE-002 at n=1,420 scale, same server, and the real paper:
routing + transformation vs universal retrieval vs full timeline at cost.

## 7. Honest expected-value math (before running anything)

Ceiling from 002: cat2 failures convertible via admission+anchoring, plus
cat1 set-coverage on the class-B side, minus irreducible gold/judge noise
(~11%). Realistic oracle ceiling ≈ B 55% → 63–68%; learned dispatch at 0.9
class recall ≈ 61–66%. **The WORKS bar is reachable but not roomy.** The
stronger claim is qualitative: R-TEMP > A on cat2 at ~40% of A's tokens —
evidence that structure beats scale, not just beats one retrieval config.

## 8. Costs and constraints

- No new LM calls anywhere; R1 router adds zero embedding calls (reuses the
  question vector). Router training: CPU, one-time, hours.
- Embedding amortization: 002 measured pack-building (+33% embedding) — routing
  inherits this accounting; per-query cost story is unchanged from B/C.
- Server: frozen 9100 config; Stage 2+ runs only after 003 completes (single-
  server decision preserved).
- Category-5 adversarial: excluded from main; router may additionally learn an
  ABSTAIN class as a secondary (this is where BERT-class routing has an easy
  win: "what did the author eat for lunch last Tuesday" questions have no
  evidence — routing to abstain instead of retrieving is itself a mechanism).

## 9. Risks (foreseen, disclosed)

1. **Gold categories ≠ functional classes.** Enumeration hides inside cat1;
   some cat2 has no date expression at all (relative-only). Mitigation:
   subtype analysis in Stage 0; mechanisms keyed to question features, labels
   used only for dispatch evaluation.
2. **Label noise ~7.5%** (forensics) — router learns noisy targets; report
   label-noise audit on a 40-item hand-check sample.
3. **The failed regex ghost.** Deterministic intent routing died in 001. The
   claim is not "learned > regex" (probably trivially true at 3 classes) but
   "dispatch-with-right-mechanisms converts admission that no single ranker
   can", with the oracle-dispatch ceiling as the load-bearing evidence.
4. **Small n.** 120 items over 3 classes: per-class cells ~20–40. Stage 2 is a
   pilot by design; the scale judgment is ROUTE-002.

---

*Draft authored for review. Nothing locked, nothing built. Stage 0 needs only
the 002 artifacts (already on disk) + the R-TEMP/R-MH builders + embeddings.*
