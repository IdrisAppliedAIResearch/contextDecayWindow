# NF-005 Pre-Registration - Source-Turn Candidate Information Dilution

**Status:** `PRE-REGISTERED - TREATMENT NOT RUN`
**Integrity anchor:** the commit that first contains this file; record its SHA
in the run report without editing this file
**Authorized by:** user, August 13, 2026
**Predecessors:** NF-002, NF-003, NF-004, and NF-005 exploration
**Corpus:** the same 465 LongMemEval items used by NF-003
**Budget:** 32,000 candidate-text characters
**Seed:** not applicable; every operation is deterministic
**Planned successful vector-capture calls:** 167,919
**Planned embedding calls during measurement:** 0
**Planned generation calls:** 0
**Date:** August 13, 2026

## 1. Claim

On the frozen LongMemEval population, ranking source turns by their own query
cosine will improve **any exact evidence-turn delivery** over making those same
turns inherit their parent episode's cosine, when both arms pack the same turns
under the same 32,000-character budget and skip-on-overflow policy.

The mechanism prediction is candidate information dilution: an evidence turn
whose own embedding remains informative can be hidden when it is aggregated
with a longer, unrelated turn before cosine is computed. A positive registered
ranking contrast supports that moderator and reconciles LongMemEval's negative
episode-ranking sign with LoCoMo's positive pair-ranking sign. A null does not;
the corpus-specific scope then remains.

This is a post-NF-003 directional characterization on an exhausted corpus. It
cannot independently confirm a general law. Source-turn splitting changes
length and semantic localization together, so it does not identify raw
character count as the sole cause.

## 2. Pre-lock basis

The three-arm LongMemEval result is 375/465 for session ranking/session packing,
388/465 for session ranking/episode packing, and 351/465 for episode
ranking/episode packing. Finer packing helps while finer ranking hurts. The 63
coarse-rank rescues have median own-episode cosine rank 46.

NF-004 prospectively confirms the opposite ranking sign on LoCoMo: adjacent-pair
ranking improves complete evidence delivery from 843/1,098 to 935/1,098 at 16k.
Relative budget did not reconcile the corpora.

The committed NF-005 exploration instead finds a candidate-scale difference.
Median LoCoMo pairs are 241 characters. LongMemEval evidence episodes are 2,550
characters, 10.58 times larger, while their exact evidence turns are 298
characters. Of 881 evidence flags, 831 are on user turns. Longer LongMemEval
evidence episodes have worse normalized own-cosine rank overall (Spearman rho
0.484) and within every question class.

The treatment has not been computed: none of the 167,918 unique source-turn
texts exists in the retained vector cache. The control is computable from
retained episode vectors and was explored before lock. Episode-score inheritance
with turn packing delivers any evidence on 361/465 and all evidence on 208/465;
it leaves 104 primary misses. Every store exceeds 32k, with minimum 400,126
characters, and median packed characters are 31,992.

## 3. Population and stable identities

The source is the exact LongMemEval file at SHA-256
`d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.
It contains 500 items. Population membership is the 465 source `question_id`
values in NF-003 Part 1 at LF SHA-256
`2d29387251b109f780d7a2fe86e7a1d3244eb0f5a73515b1be1d8e7dda7e506f`.
These are the answerable NF-002 items with at least one paired source turn whose
LongMemEval `has_answer` flag is true. The same five answerable items without a
paired turn-level flag remain excluded; the abstention stratum remains excluded.

The item comparison key is source `question_id`. Candidate identity is SHA-256
over `question_id`, source session identity, accepted episode ordinal, turn
offset, role, and complete rendered text. Generated IDs, timestamps, paths, and
vector row order are not identities.

## 4. Candidates, ranking, and packing

Sessions follow corpus order. At offsets 0-1, 2-3, and so on, retain only exact
`user`/`assistant` pairs, matching NF-003's carried episode construction. An
episode candidate is exactly:

```text
User: {user content}
Assistant: {assistant content}
```

with one LF and no trailing LF. Its two source-turn candidates are exactly the
two lines above, each without a trailing LF. Cost is Python `len(candidate_text)`.
No tag, separator, prompt, or reader cost is charged. Four source-turn
occurrences exceed 32k; they remain in the pool and can never fit.

Vectors use the carried Qwen3-Embedding-0.6B Q8_0 model at SHA-256
`06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`,
`llama-cpp-python` 0.3.25, 1,024-dimensional float32 output, `n_ctx=512`,
`n_gpu_layers=0`, `n_threads=1`, `n_threads_batch=1`, and exactly one text per
call. Before population capture, one solo call on
`episodic call-shape sentinel: one text per call` must reproduce vector SHA-256
`baecf77627380f36f75a69c4454b064d886133f04255c5e5b4d3f24f00e7c4b8`
from the retained EC-002 cache. The remaining 167,918 successful calls capture
each unique source-turn text once. The new cache is then sealed by file and
canonical text-to-vector SHA-256 and reopened read-only for measurement.

All arms rank descending and break exact score ties by source session order,
episode order, then turn offset. All pack with skip-on-overflow: a candidate
that would exceed 32k is skipped and scanning continues.

Arm `E_EPISODE_RANK_EPISODE_PACK`:

1. Compute each episode's own query cosine from the retained EC-002 vectors.
2. Rank and pack whole episodes.

Arm `E_EPISODE_RANK_TURN_PACK`:

1. Give both source turns their parent episode's retained cosine.
2. Rank and pack source turns.

Arm `T_TURN_RANK_TURN_PACK`:

1. Compute each source turn's own query cosine from the sealed NF-005 cache.
2. Rank and pack source turns.

The primary one-factor contrast is `T_TURN_RANK_TURN_PACK` versus
`E_EPISODE_RANK_TURN_PACK`. Candidate pool, candidate text, cost, packing unit,
budget, overflow behavior, and tie breaks are identical; only score assignment
changes. The first arm is a reproduction anchor and packing diagnostic.

## 5. Endpoint and statistic

Primary per-item outcome: `1` if at least one delivered candidate is the exact
source turn whose corpus `has_answer` flag is true, otherwise `0`. For whole
episode packing, an evidence turn is delivered only when its containing episode
is delivered.

Primary comparison: paired discordant counts between the two turn-packed arms
over all 465 items. Report gains, losses, ties, net, discordant N, gain/loss
ratio, and the one-sided exact binomial sign-test p value for turn ranking being
better.

Secondary analyses cannot alter disposition:

- all exact evidence turns delivered;
- `E_EPISODE_RANK_EPISODE_PACK` versus `E_EPISODE_RANK_TURN_PACK`;
- delivered-candidate and packed-character distributions;
- best evidence rank and normalized rank under each ranking unit;
- primary outcome and rank movement by question class, evidence role, evidence
  turn-length quartile, and parent episode-length quartile;
- source-order turn packing as a slack/ranking control;
- discordant-item own-turn and parent-episode rank distributions.

No alternate split, budget, endpoint, pooling rule, length normalization,
padding rule, subgroup, or p value may set the disposition.

## 6. Disposition

The tiers are fixed before source-turn vectors exist:

| Disposition | Primary condition |
|---|---|
| **INFORMATION_DILUTION_SUPPORTED** | gains >= 2 * losses and one-sided exact p <= 0.05 |
| **CARRIES_SIGNAL** | gains > losses and p <= 0.20, and not INFORMATION_DILUTION_SUPPORTED |
| **NOT_SUPPORTED** | gains <= losses, or p > 0.20 |

Every disposition is capped at `CHARACTERIZED` because the corpus and motivating
opposite sign were already observed. `INFORMATION_DILUTION_SUPPORTED` means the
registered finer ranking unit wins after the evidence-bearing candidate is
localized to turn scale; it supports, but does not isolate, information
dilution. `CARRIES_SIGNAL` reports only the separately registered lower tier.
`NOT_SUPPORTED` leaves the NF-003/NF-004 corpus-specific scope unchanged.

PF4 reachability is mechanical at the observed 361/465 control baseline. Six
gains and zero losses give p=.015625 and reach the upper tier. Four gains and
one loss give p=.1875 and reach `CARRIES_SIGNAL` only. One gain and one loss
give p=.75 and reach `NOT_SUPPORTED`. There are 104 control misses available
for gains and 361 hits available for losses; neither direction is constrained
away.

## 7. Gate order

Gates execute in this order and stop on first failure:

1. **G0 registration identity.** The runner pins this file's first-commit SHA
   and LF SHA-256. A mismatch stops before treatment-vector access.
2. **G1 inputs and population.** Verify the dataset, NF-003 Part 1, NF-003
   three-arm summary, CC-006 adoption record, and NF-005 exploration hashes;
   recover exactly 465 stable item keys, 106,412 episodes, 212,824 source-turn
   occurrences, 881 evidence flags, and 167,918 unique source-turn texts.
3. **G2 leakage.** Grep and import-graph checks prove ranking and packing code
   cannot read `has_answer`, answer sessions, answers, question type, or
   measurement rows. A planted forbidden import and planted forbidden field
   access must both fail.
4. **G3 anchor and control reproduction.** With the retained EC-002 cache,
   reproduce the 351/465 episode-ranked/episode-packed result and all 465 item
   identities. Reproduce the explored turn-pack control at 361/465 any,
   208/465 all, paired packing gains/losses 10/0, and its full row digest.
5. **G4 implementation tests.** Prove exact source adaptation, identities,
   role rendering, inherited scores, own-turn scores, stable ties,
   skip-on-overflow continuation, over-budget retention, evidence-blind
   selection, and exact post-selection evidence joins.
6. **G5 call-shape and vector seal.** Before accepting a population vector,
   reproduce the registered sentinel hash. Capture exactly 167,918 unique
   source-turn vectors by solo calls, seal the cache, commit its manifest, and
   reopen read-only with zero misses. Any partial or extra population, batch
   call, sentinel mismatch, or embedding error stops without a result.
7. **G6 preflight and determinism.** Run two evidence-blind complete selection
   replays from the read-only caches; require byte-identical ordered candidate
   identities and payload digests. Commit the G0-G6 report before evidence is
   joined or any treatment outcome is opened.
8. **G7 sealed outcome.** Join frozen selections to `has_answer` identities,
   execute all three arms over 465 items, and commit one sealed outcome artifact
   before opening mechanism diagnostics.
9. **G8 result integrity.** Recompute every total from rows, verify zero calls
   during measurement, require a byte-identical outcome replay, apply the
   disposition table once, then open secondary diagnostics.

## 8. Preflight Part 1 - Exploration

**Behavioral identity.** A carried LongMemEval episode computes one cosine over
a short user turn and a much longer assistant turn; source-turn splitting
computes and packs those same lines independently.

**Name-to-behavior checks.** The committed exploration executes the carried
episode formatter and exact valid-pair filter. It verifies turn role labels,
turn-level `has_answer`, inherited episode scoring, turn packing, exact budget
charging, and read-only cache behavior on all 465 items. No answer-string match
defines evidence.

**Distribution.** The complete candidate and evidence distributions are in
`artifacts/exploration.json` at LF SHA-256
`00d78ad3bd113abb2fd39c8419ccd0a1e6e6513db6d52c01fadd572a9021bec7`.
LongMemEval evidence episode/turn medians are 2,550/298 characters; LoCoMo's pair
median is 241. Length/rank rho is positive overall and in all question classes.
The inherited-score turn-pack control is 361/465, packs median 31,992
characters and median 46 turns, and no full store fits.

**Degenerate states.** There is no feedback. The only absorbing ceiling is a
full-store fit, absent at 32k. Four over-budget turns are retained but cannot be
selected. Source order and exact ties are deterministic. A cache miss and a
zero-norm vector fail closed rather than becoming a constant score.

## 9. Preflight Part 2 - Checklist

**PF1 - Inputs exist.** Verified at exploration commit `cc607eda`: the corpus
hash above; 500 source items; the exact 465-item Part 1 population; 106,412
episodes; 212,824 accepted turn occurrences; 881 flags; the 96,585-entry EC-002
cache; and the exploration artifact hash above. The post-lock turn cache is a
G5 deliverable and absence blocks measurement.

**PF2 - Mechanism identity.** The exploration executes, rather than infers, the
carried episode construction and the proposed source-turn packing control. G4
tests every arm name against score assignment and packing behavior.

**PF3 - Gate ordering.** The runner enforces G0-G6 before the measurement join.
Planted failures at each gate make G7 unreachable. The committed preflight
artifact must be an ancestor of the G7 outcome commit.

**PF4 - Thresholds achievable.** Section 6 gives exact reachable discordant
configurations. The control has 104 misses and 361 hits, all stores bind, and
the primary direction can improve, tie, or reverse.

**PF5 - Comparison keys stable.** Item keys are source `question_id`; candidate
keys include source position and complete content. Digests are canonical JSON
over sorted stable identities. Paths, SQLite row order, and timestamps are
excluded.

**PF6 - Reproduction anchor.** G3 reproduces NF-003's 351/465 strict result by
all 465 identities from the three-arm artifact at LF SHA-256
`4473c8c5c4ed5337f912b6de665bb131d7cb3a00bc38cd67502be5572a16c1b6`,
then reproduces the committed 361/465 turn-pack control and full row digest.

**PF7 - Absorbing state.** The mechanism has no feedback. All 465 stores exceed
budget and the minimum store is 400,126 characters, so no item begins at the
full-store ceiling. G4 proves skip-on-overflow continues after an impossible
candidate.

**PF8 - Ablation length.** This is an offline replay over the complete 465-item
population, not a 120-turn live run, so no short ablation precedes it. It can
detect paired availability direction at one budget. It cannot detect reader
correctness, raw-length causality, or transfer to a new corpus.

**PF9 - Surrogate audit.** “Any turn from an answer episode” could pass while
the flagged evidence turn is omitted; the primary joins exact turn identities.
Even exact evidence delivery can pass while evidence is insufficient or a
reader fails. A positive rank contrast can arise from semantic localization as
well as shorter text. Those residuals are accepted and bound the claim.

**PF10 - Live evaluation.** Availability is not a verdict. No outcome
authorizes a reader-quality, working-memory, promotion, or adoption claim. Any
such claim needs a separate prospective live registration with fixed reader,
prompt, exact serialized budget, scoring rubric, determinism gate, success bar,
and no-regression bar.

## 10. Leakage and result order

Mechanism code receives candidate identity, parent identity, source order,
candidate text, vector, and budget only. It must not read `has_answer`,
`answer_session_ids`, `answer`, `question_type`, NF-003 result rows, or NF-005
measurement artifacts. The adapter may read corpus fields to construct stable
candidates, but strips evidence and metadata before invoking the mechanism.
Measurement joins frozen selected identities to exact evidence identities only
after G0-G6 pass and their report is committed.

The G7 commit contains primary rows and disposition inputs before any
discordant rank inspection or secondary interpretation. G8 may then report
mechanism diagnostics. Git order is the evidence.

## 11. Stops and exclusions

Stop without a result on any registration mismatch, input drift, population
drift, anchor mismatch, leakage violation, sentinel mismatch, changed model or
call shape, cache miss, non-finite or zero vector, vector-capture cardinality
mismatch, non-identical selection replay, model/generation call, evidence join
before preflight commit, or outcome replay mismatch.

No retry may silently reuse a partial unsealed cache. No batching, mean/max
pooling, sentence splitting, evidence-aware candidate filtering, truncation of
over-budget turns, budget sweep, alternate endpoint, padding control, reader
run, promotion, or production adoption is authorized. A controlled padding or
aggregation study would be required to identify raw character count separately
from semantic localization.
