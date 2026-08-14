# NF-006 Pre-registration - Internal Statement Ranking

**Status:** `PRE-REGISTERED - NOT RUN`
**Authorization:** user instruction in the NF-005 successor thread, August 13,
2026
**Part 1 anchor:** `6035e916`
**Registration anchor:** the commit adding this file; its LF-normalized SHA-256
is recorded in the first run header before implementation executes
**Evidence ceiling:** `CHARACTERIZED`; the 121-turn corpus, Q11, E005 result,
and turn-90 spot check are already observed

## 1. Question

Does statement-level candidate ranking rescue the internal 121-turn corpus's
remaining Q11 evidence without regressing targeted evidence?

DX-001 localized E005's remaining oracle gap to turn 90: one eligible episode
with four monetary items, cosine 0.05599035, rank 112/119, and required frontier
0.225. After NF-005, an authorized causal spot check reproduced the parent
cosine under E005's exact query call shape and found that all four numbered
sections individually exceed 0.225. That spot check motivates this study but is
not an outcome: it did not split the full store, run the selector, pack 32k, or
measure Q11 or targeted availability.

The registered prediction is that own-statement ranking, not statement packing
alone, increases Q11 availability by bringing monetary evidence into the packed
payload. Any targeted loss is binding regardless of the breadth result.

## 2. Frozen inputs

| Input | Frozen value |
|---|---|
| Corpus | corrected `c121_l` context-matched STM store |
| Database SHA-256 | `5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41` |
| Q11 probe | exact user message at turn 120 |
| Q11 eligible episodes | all 119 episodes with `turn_number < 120` |
| Targeted probes | E005's 21-item grid at turns 112, 113, and 115-119 |
| Budget | 32,000 serialized characters |
| Selector | frozen A3 `lambda=0.1`, `r=0.0`, `k=16` |
| E005 Q11 anchor | 12/17 facts, 4/4 domains, 31,569 chars, 15 episodes |
| Embedding model SHA-256 | `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439` |
| Statement population | 791 unique units at turn 120 |

The mechanism reads only the store, probe text, embeddings, source turn, role,
ordinal, parent identity, inherited domain, and exact serialization cost. It may
not read Q11 atoms, targeted terms, rubrics, prior selections, availability, or
the turn-90 identity.

## 3. Statement identity

The Part 1 splitter is frozen without change:

1. Preserve each non-empty user message as one statement.
2. Normalize line endings to LF and trim only leading/trailing whitespace.
3. If assistant text contains at least two top-level `^<integer>. ` starts,
   split at those starts. Preserve any non-empty prefix as its own statement.
4. Otherwise split assistant text at one or more blank lines.
5. Drop only a standalone case-insensitive `(Risk: ...)` block. Preserve inline
   risk text.
6. Identity is SHA-256 over parent content hash, source turn, role, ordinal, and
   exact UTF-8 statement text. Generated database ids and paths are forbidden.
7. Inherit source turn and ground-truth domain from the parent episode. No text
   is summarized, rewritten, deduplicated, or generated.

At turn 120 this must reproduce 119 user plus 672 assistant units, 791 unique
texts, median 564 characters, p90 821, and turn 90's five registered text hashes
from `artifacts/part1_exploration.json`.

## 4. Arms

All arms use the full temporally eligible pool, frozen A3 selector, exact 32k
serializer, deterministic tie order, and the same probe embedding.

| Arm | Candidate unit | Relevance | Cluster | Packing |
|---|---|---|---|---|
| **C0_EPISODE** | whole episode | stored parent episode cosine | frozen E005 episode cluster | whole episode |
| **C1_INHERITED_STATEMENT** | statement | inherits parent episode cosine | inherits parent episode cluster | statement |
| **T1_OWN_STATEMENT** | statement | own statement cosine | inherits parent episode cluster | statement |

C0 is the reproduction anchor. C1 isolates finer packing. T1 versus C1 isolates
statement-level relevance while preventing statement vectors from silently
changing A3's cluster-coverage route. Parent cluster assignments are recomputed
by the unchanged deterministic E005 algorithm separately at each eligible
prefix, then inherited by child statements in both statement arms.

Statement serialization uses the existing episode element with exactly one
non-empty role: user text for a user statement or assistant text for an
assistant statement. Parent id, role, and ordinal are rendered in deterministic
metadata. The other role is empty. Exact rendered length is the charged cost;
no candidate may be partially rendered.

## 5. Vector capture and call shape

The run is CPU-only, one process, one thread, fixed seed 5005, and no speculative
execution.

- Probe vectors reproduce E005 exactly: the nine unique probe texts are sorted
  lexicographically and embedded in one nine-text batch. The Q11/parent turn-90
  cosine must reproduce `0.05599035` within `1e-7` before any selection.
- Each of the 791 statement texts is embedded in its own sequential exact-solo
  call, in stable identity order. No batching or parallel capture is permitted.
- A content-addressed SQLite cache records exact float32 bytes and binds file
  SHA-256, canonical text-to-vector SHA-256, model SHA-256, ordered text
  manifest, and call shape. Measurement opens it read-only and fails on a miss.
- Capture may commit incrementally, but an incomplete or unsealed cache is not
  resumable or reusable. The final manifest is committed before selection.
- No generation calls occur.

## 6. Measures

### 6.1 Q11 breadth

After all selections are committed outcome-blind, measurement opens the locked
17-item Q11 key and reports for every arm:

- total exact available items out of 17;
- per-domain counts for civil, art, monetary, and marine;
- selected statement and distinct-parent counts;
- serialized characters;
- selected turn-90 statement identities and their four monetary item matches;
- gains and losses versus C0 and C1.

The 14/17 rubric threshold is reported as availability only. No answer is
generated and no Q11 score is assigned.

### 6.2 Binding targeted no-regression arm

At each carried E005 probe prefix, C0 and T1 run from their own temporally
eligible pools under the same selector and budget. Only after selection artifacts
are committed does measurement open the frozen 21-item targeted grid.

For every item, report C0 availability, T1 availability, gain/loss/tie, probe,
domain, selected identities, and payload hash. The binding bar is:

1. **zero losses among all 21 items;**
2. T1 total targeted availability is not below C0;
3. no probe or domain has lower targeted availability.

One loss fails the gate. Breadth cannot compensate for a targeted loss. This is
stricter than the requested warning that two or three losses would be fatal and
directly carries TA-001/SR-001's zero-loss precedent.

## 7. Gates, in order

| Gate | Requirement | Binding failure |
|---|---|---|
| **G0 registration** | first-parent commit and LF SHA match this lock; lock contains no implementation files | `REGISTRATION_INVALID` |
| **G1 inputs** | every frozen file exists, is readable, hash-identical, and counted | `INPUT_INVALID` |
| **G2 leakage** | static grep/import graph plus planted violation prove mechanism cannot read either key | `LEAKAGE` |
| **G3 reproduction** | C0 reproduces E005 Q11 identities, payload SHA, 12/17, 4/4, 31,569 chars, plus carried targeted anchors | `ANCHOR_FAIL` |
| **G4 statements** | Part 1 distribution, identities, turn-90 hashes, temporal eligibility, and exact costs reproduce | `UNIT_IDENTITY_FAIL` |
| **G5 vectors** | 791/791 statement hits, zero misses; parent cosine and all file/content/model/call-shape seals pass | `VECTOR_INVALID` |
| **G6 determinism** | two complete evidence-blind C0/C1/T1 selections are byte-identical at Q11 and every targeted prefix | `NONDETERMINISTIC` |
| **G7 selection seal** | commit all selected identities, order, costs, chars, and payload hashes before opening either outcome key | `SEAL_ORDER_INVALID` |
| **G8 targeted** | zero item, probe, and domain regressions under Section 6.2 | `TARGETED_REGRESSION` |
| **G9 Q11** | measure registered breadth and apply Section 8 exactly once | registered disposition |

G8 is evaluated before assigning any positive Q11 disposition. G9 is still
measured and reported if G8 fails, but no positive advancement label is
available in that branch.

## 8. Locked dispositions

Apply the first matching row:

| Condition | Disposition |
|---|---|
| Any G0-G7 failure | the gate's named integrity stop; no outcome claim |
| G8 fails | `TARGETED_REGRESSION - CHARACTERIZED`; report Q11 descriptively, no promotion |
| G8 passes; T1 >=14/17; T1 > C1; and T1 gains at least one monetary item over C1 | `INTERNAL_DILUTION_RESCUES_Q11 - CHARACTERIZED` |
| G8 passes; T1 > C1; and T1 gains at least one monetary item over C1, but T1 <14/17 | `INTERNAL_DILUTION_CARRIES_SIGNAL - CHARACTERIZED` |
| G8 passes; C1 > C0; and T1 <= C1 | `PACKING_ONLY_GAIN - CHARACTERIZED` |
| G8 passes and none above match | `NO_INTERNAL_DILUTION_SIGNAL - CHARACTERIZED` |

No lower post-result tier may be introduced. `CHARACTERIZED` is the maximum
because the corpus and motivating item are exhausted.

## 9. Preflight

### Part 1 - completed before lock

`NF_006_PART1_EXPLORATION.md` and
`artifacts/part1_exploration.json` at `6035e916` establish the falsifiable
splitter identity, full unit-count and length distributions, name-to-behavior
checks, turn-90 structure, and residual longest-unit state without reading any
query or outcome.

### Part 2 - must pass before capture

| Check | Required executed evidence |
|---|---|
| **PF1 inputs** | byte hashes and counts for database, turn log, E005 anchors, both measurement keys, model, and Part 1 artifact |
| **PF2 identity** | real-trace reproduction of 791 statement identities and all C0/C1/T1 named behaviors |
| **PF3 ordering** | planted test proves key-open functions fail until G7's committed selection seal is verified |
| **PF4 reachability** | 14/17 is reachable at 5,058 chars; zero targeted losses is reachable because C0 is a legal arm; all integrity stops are synthetically fireable |
| **PF5 keys** | statement and parent content hashes remain stable across two processes; no generated ids participate |
| **PF6 anchor** | exact E005 C0 payload/identity reproduction and parent cosine `0.05599035` |
| **PF7 absorbing state** | selector terminates on exhausted or unaffordable remaining pool at all eight prefixes; repeated run cannot add a candidate after termination |
| **PF8 length** | one Q11 plus 21 targeted items can identify this frozen corpus's availability trade, not population or reader performance |
| **PF9 surrogate** | Q11 breadth can pass while targeted evidence regresses or a reader fails; G8 and the no-live boundary remain binding residuals |
| **PF10 live** | availability cannot authorize a live run, adoption, or reader claim |

## 10. Boundaries

This is a registered offline characterization with zero generation calls. It may
identify whether statement relevance causes the internal turn-90 selection miss
under the frozen E005 objective. It cannot establish reader correctness, a
universal statement size, a fresh-corpus confirmation, or a deployable policy.
No 35-turn ablation, 120-turn live run, promotion, or adoption is authorized.
