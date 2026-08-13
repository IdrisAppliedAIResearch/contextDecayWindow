# NF-004 Pre-Registration - LoCoMo Ranking Granularity Confirmation

**Status:** `PRE-REGISTERED - HOLDOUT NOT RUN`
**Integrity anchor:** the commit that first contains this file; record its SHA
in the run report without editing this file
**Authorized by:** user, August 13, 2026
**Predecessors:** NF-002, NF-003, and the LoCoMo development controls
**Corpus:** six sealed LoCoMo conversations
**Seed:** 5005
**Planned model calls:** 0
**Planned embedding calls during measurement:** 0
**Date:** August 13, 2026

## 1. Claim

On the sealed LoCoMo holdout, ranking adjacent-turn pairs by their own query
cosine will improve **complete exact-evidence delivery** over making every pair
inherit the maximum pair cosine of its session, when both arms pack the same
pairs under the same 16,000-character budget and skip-on-overflow policy.

This is a directional, corpus-specific availability claim. It does not claim
that fine ranking is universally better, that oversubscription alone determines
the sign, or that a reader answers more questions correctly.

## 2. Why this is the registered claim

LongMemEval's three-arm characterization supports `rank coarse, pack fine` at
32k: strict delivery is 375 for session/session, 388 for session/episode, and
351 for episode/episode. Its 63 coarse-rank rescues have median own-cosine rank
46. That result stands on the exhausted corpus.

LoCoMo development moves in the opposite direction. At 32k, pair ranking beats
session-score inheritance 826 to 773 on complete evidence, with 71 gains and 18
losses. A locked 4k-96k sweep remains positive at every truncated budget. The
source-order control scores only 279 at 32k, refuting the idea that the result
comes from a slack budget. LongMemEval development crosses from positive to
negative complete-evidence net between 16k and 24k, but overlapping binding
ratios retain opposite corpus signs. The cross-corpus relative-budget rule is
therefore rejected before this lock.

NF-004 confirms the bounded LoCoMo direction instead of forcing the
LongMemEval rule onto a corpus whose development data contradict it.

## 3. Population and stable keys

The source is the exact 2,805,274-byte `locomo10.json` file at SHA-256
`79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`,
from official repository commit
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

The split was locked before QA content or outcomes were opened. Holdout IDs are
`conv-26`, `conv-30`, `conv-43`, `conv-44`, `conv-49`, and `conv-50`.

The metadata-only inventory at SHA-256
`cde6e37ad046198f9b9326497c9d13db4c906fb02026df16243afede2b820789`
records:

- 6 conversations;
- 1,104 source QA records;
- 1,104 canonical unique QA records and 0 exact duplicates;
- 1,098 unique records whose full evidence list resolves;
- 6 malformed evidence references.

The primary population is the 1,098 fully resolvable canonical unique records.
Both arms may run key-blind on all 1,104 questions; the six malformed records
are excluded mechanically before primary scoring. They are not repaired,
imputed, or moved to the any-evidence denominator. Canonical QA
identity is SHA-256 over `sample_id`, a NUL byte, and sorted compact JSON of the
complete source QA record. Source paths, generated IDs, and timestamps are not
comparison keys.

## 4. Candidate and score definitions

Within each conversation, process `session_N` keys by numeric N. Within a
session, pair turns at source offsets 0-1, 2-3, and so on. If a session has an
odd final turn, retain it as a one-turn candidate. Candidate text is exactly:

```text
speaker: text
speaker: text
```

with one LF between members and no trailing LF. A singleton has one line. Cost
is Python `len(candidate_text)`, matching development. Evidence dialogue IDs
map to the unique candidate containing them.

Vectors use the carried Qwen3-Embedding-0.6B Q8_0 model at SHA-256
`06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`,
exact solo calls, float32 storage, 1,024 dimensions, and `llama-cpp-python`
0.3.25. Holdout vectors may be captured only after this registration commits.
The resulting cache is sealed by file SHA-256 plus canonical
text-to-vector-content SHA-256. Measurement reopens it read-only; any miss is a
hard stop rather than an embedding call.

Arm `S_SESSION_RANK`:

1. Compute each pair's cosine against the question.
2. Give every pair in a session that session's maximum constituent-pair cosine.
3. Rank descending by inherited score; break ties by session order and pair
   order.

Arm `P_PAIR_RANK`:

1. Rank each pair by its own question cosine.
2. Break ties by session order and pair order.

Both arms scan their order under a 16,000-character budget. A candidate that
would overflow is skipped; scanning continues. No separator, tag, or reader
prompt cost is charged. This is the same candidate-text availability instrument
used on development, not a serialized-context cost claim.

The only experimental component is the score assignment unit. Candidate pool,
candidate text, embedding model and call shape, budget, packing unit, overflow
policy, tie breaks, and evidence mapping are identical.

## 5. Endpoint and statistic

Primary per-item outcome: `1` if every exact evidence-bearing candidate is
delivered, otherwise `0`.

Primary comparison: paired discordant counts between `S_SESSION_RANK` and
`P_PAIR_RANK` over all 1,098 primary items. Report gains, losses, ties, net,
discordant N, gain/loss ratio, and the one-sided exact binomial sign-test p value
for pair ranking being better.

Secondary, unable to change disposition:

- any exact evidence candidate delivered at 16k;
- primary outcome by conversation and source category;
- delivered-candidate and packed-character distributions;
- best exact-evidence rank distributions;
- a 32k replay of both registered arms;
- source-order packing at 16k.

No other budget, ranking rule, endpoint, subgroup, or p value may determine the
registered disposition. The development sweep is not rerun on holdout.

## 6. Disposition

The tiers are inherited unchanged from NF-002 and fixed before holdout outcomes:

| Disposition | Primary condition |
|---|---|
| **WORKS** | gains >= 2 * losses and one-sided exact p <= 0.05 |
| **CARRIES_SIGNAL** | gains > losses and p <= 0.20, and not WORKS |
| **NULL** | gains <= losses, or p > 0.20 |

`WORKS` confirms the registered LoCoMo **availability** direction. It does not
promote the mechanism or supersede LongMemEval's opposite characterization.
`CARRIES_SIGNAL` reports the lower pre-registered signal tier. `NULL` closes
this LoCoMo directional claim under the registered instrument.

Reachability at N=1,098 is mechanical. Six gains and zero losses give p=.015625
and reach WORKS. Four gains and one loss give p=.1875 and reach CARRIES_SIGNAL
without reaching WORKS. One gain and one loss give p=.75 and reach NULL. The
direction can also reverse. No tier is unreachable or guaranteed by base rate.

## 7. Gate order

Gates execute in this order and stop on first failure:

1. **G0 registration identity.** The runner contains this file's locked LF
   SHA-256 and first-commit SHA. Any mismatch stops before corpus access.
2. **G1 source and population.** Dataset, split manifest, and metadata-only
   inventory hashes match; exactly 1,104 arm inputs and 1,098 primary
   comparison keys are identified.
3. **G2 leakage.** Grep and import-graph checks prove mechanism code cannot read
   answers, categories, or evidence IDs. Evidence joins exist only in the
   measurement module. A planted forbidden import must fail.
4. **G3 vector seal.** The read-only holdout cache matches its file, content,
   model, dtype, dimension, and solo-call manifest; expected unique texts equal
   cache entries; zero misses.
5. **G4 development reproduction.** The same runner on the four development
   conversations reproduces the 16k primary totals 702 and 773, paired 104/33,
   and the 32k totals 773 and 826, paired 71/18, by comparison-key identity.
6. **G5 determinism.** Two complete development replays are byte-identical.
7. **G6 holdout run.** Execute both arms over the 1,098 locked primary keys and
   write one sealed outcome artifact.
8. **G7 result integrity.** Recompute totals from rows, verify zero model and
   embedding calls, require a byte-identical holdout replay, then apply the
   disposition table once.

No result is opened until G0-G5 pass and their report is committed.

## 8. Preflight Part 1 - Exploration

**Behavioral identity.** The baseline ranks pair candidates in session-sized
score plateaus using the best query match anywhere in that session; treatment
ranks the same pair candidates by their own query match; both spend the budget
one pair at a time.

**Name-to-behavior checks.** Development tests prove session-score inheritance,
pair-level cosine ordering, source-order independence from query vectors,
skip-on-overflow continuation, singleton retention, exact evidence-pair joins,
canonical QA deduplication, and read-only cache behavior. The 32k result
reproduces 773/868 versus 826/868 on complete evidence and 820/871 versus
855/871 on any evidence.

**Distribution.** The locked 4k-96k development sweep reports every cell. At
16k, median oversubscription is 4.96x; the session baseline is 702/868 and pair
ranking 773/868, with 104 gains and 33 losses. At 32k, packed characters have
median 31,992 in both arms. The treatment sign is positive at every truncated
LoCoMo budget and reaches zero only when the full store fits.

**Degenerate states.** Source order is much worse at 32k (279/868), so ranking
discriminates. At 96k all three arms reach 868/868, proving the full-store
absorbing ceiling. Singleton candidates are retained. Overflow skips and
continues. The six malformed holdout records are excluded before primary
scoring, not exposed to ranking.

## 9. Preflight Part 2 - Checklist

**PF1 - Inputs exist.** Verified at metadata commit `30a391ac`: source bytes and
hash above; 6 holdout conversations; 1,104 unique QA identities; 1,098 primary
records; metadata artifact SHA-256 above. The development vector cache and both
control artifacts are present and hash-bound. Holdout vector capture is a
post-registration execution step and G3 blocks without its committed manifest.

**PF2 - Mechanism identity.** Verified on committed development data by
`ranking_budget_controls.json` at SHA-256
`8ff8bd529f1af00331147b345915dc128ef45acf6c633d04be9d0f9243a79e3b`.
The arm names match the behaviors in §4; neither arm ranks whole-session text.

**PF3 - Gate ordering.** G0-G5 precede G6 in the runner and receive planted
tests that make holdout execution unreachable after each failure. The preflight
report is committed before G6 may run.

**PF4 - Thresholds achievable.** §6 gives exact discordant configurations for
all three dispositions at the actual N. Development demonstrates both gains and
losses and an off-ceiling 80.9% baseline at 16k. A null and a reversed direction
remain mechanically possible.

**PF5 - Comparison keys stable.** Canonical content hashes are committed in the
metadata inventory. There are no holdout duplicates. Generated IDs, paths, and
timestamps are excluded.

**PF6 - Reproduction anchor.** G4 reproduces 16k and 32k development rows by
identity and totals from the artifact above. The historical three-arm artifact
at SHA-256 `4473c8c5c4ed5337f912b6de665bb131d7cb3a00bc38cd67502be5572a16c1b6`
separately reproduces LongMemEval's 375/388/351.

**PF7 - Absorbing state.** The mechanism has no feedback. The relevant
absorbing ceiling is full-store fit: all LoCoMo development arms become
868/868 at 96k. G4 also tests inherited-score tie plateaus and skip-on-overflow.

**PF8 - Ablation length.** The offline holdout covers all 1,098 eligible items,
not a short ablation. It can detect paired availability direction under one
budget. It cannot detect reader correctness, model sensitivity, or whether the
direction transfers beyond LoCoMo.

**PF9 - Surrogate audit.** Complete evidence can pass while the reader fails,
while an annotated evidence list is insufficient, or while pair ranking wins
through favorable character ordering rather than semantic precision. The claim
is explicitly availability under the composite ranking-plus-packing path.
Any-evidence and session-touch cannot certify the primary property and cannot
set disposition.

**PF10 - Live evaluation.** Availability is not a verdict. No NF-004 outcome,
including WORKS, authorizes a working-memory, answer-quality, promotion, or
adoption claim. Before any such claim, a separate prospective live registration
must lock reader model/build, prompt serialization and exact cost, question
population, answer rubric, determinism check, success bar, no-regression bar,
and both disposition tiers. NF-004 itself makes zero model calls.

## 10. Leakage and reporting

Ranking and packing modules receive candidate text, candidate identities,
session membership, source order, question text, vectors, and budget only. They
must not read `qa.answer`, `qa.category`, `qa.evidence`, dialogue `dia_id`, the
holdout inventory, or measurement rows. The measurement adapter joins delivered
candidate identities to evidence only after both arm outputs are frozen.

The report states the registration SHA, every gate, primary totals and paired
counts, exact p, disposition, secondary diagnostics, cache/model call counts,
and the live-evaluation boundary. Mechanism logs remain unopened until the
primary result and disposition are committed.

## 11. Stops and exclusions

Stop without a result on any failed gate, changed input, cache miss, unexpected
duplicate, population other than 1,098, model or embedding call, non-identical
replay, or leakage violation. Record whether the mechanism failed or the
instrument could not test it.

No retuning, alternate budget, session-text embedding, mean pooling, category
exclusion, evidence repair, threshold change, second embedder, live inference,
or adoption is authorized. Any such change requires a standalone amendment
before its affected outcome is opened, or a new study if it adds a factor.
