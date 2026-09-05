# BEAM-001 Implementation Document - deployed CC80 and static ASPECT versus parent opportunity ASPECT

**Document type:** Prospective benchmark-onboarding and Part 1 implementation design  
**Status:** `DRAFT - DESIGN ONLY - NOTHING IMPLEMENTED OR RUN`  
**Date:** August 27, 2026  
**Predecessors:** CC-007, HH-003, TC-013, TC-014, LV-009  
**Corpus:** BEAM, arXiv:2510.27246, official repository
`mohammadtavakoli78/BEAM`

## 0. Decision in plain language

Onboard BEAM as a new, hash-pinned conversational-memory corpus and use it to
compare three paths: the shipped CC80 default, the shipped optional global
static-ASPECT mechanism, and one candidate change that replaces static ASPECT
with TC-014's CC80-parent fan-out plus exact opportunity admission.

All three arms retain the deployed additive latest-32 continuity tier and the
same 32,000-character long-term allowance, CC80 ranking, embedder, episode
formation, deduplication, packing and rendering. The two ASPECT arms differ
only in the selector inside the protected half. The CC80 arm is the unchanged
public default and uses the whole long-term allowance without an ASPECT split.

This document authorizes no scored answer run. Its first deliverable is a
label-blind three-arm exploration on BEAM question text. Ideal responses,
rubrics, evidence annotations, generated answers and judge outcomes remain
inaccessible. The exploration may support a later standalone pre-registration;
it cannot itself establish that any arm answers questions better.

## 1. The exact unanswered question

HH-003 scored the shipped optional configuration at 1,205/1,540 on LoCoMo:

```python
EpisodicConfig(aspect_enabled=True)
```

The shipping configuration adds the latest 32 complete episodes outside the
32,000-character long-term allowance, then allocates that allowance between
CC80 and one global static ASPECT walk. TC-014 is different from static ASPECT:
CC80 admissions become independent one-hop ASPECT parents, and a proposed
child is retained only when its raw ASPECT value covers the CC80 value it would
displace. LV-009 used TC-014 contexts but removed deployed recency and compared
renderers, not retrieval architectures.

The missing causal contrast is therefore:

> Under the same deployed continuity tier, long-term allowance, formation,
> ranking, packing, rendering, reader and judge, does replacing global static
> ASPECT with CC80-parent opportunity ASPECT improve answer quality?

The shipped CC80 default is a required guardrail. A candidate that beats static
ASPECT while losing to ordinary CC80 has not improved the deployed library.
HH-003's static-ASPECT gain over default was only 14/1,540, with 46 paired gains,
32 losses and two-sided `p=0.140538`; TC-011/TC-012 also retained CC80 as the
offline fallback. A later live registration must therefore keep T1 versus C0
as primary and require T1 versus A0 to clear a pre-registered non-regression
guardrail.

BEAM-001 is the onboarding and exploration work needed before that contrast can
be registered.

## 2. Why BEAM

The official BEAM release provides 100 long, chronological user-assistant
conversations and 2,000 human-validated probing questions over ten memory
abilities. The normal release contains 90 conversations at nominal 100K, 500K
and 1M-token scales; ten additional 10M-token conversations are distributed
separately. The question families are abstention, contradiction resolution,
event ordering, information extraction, instruction following, knowledge
update, multi-session reasoning, preference following, summarization and
temporal reasoning.

Official sources:

- paper: `https://arxiv.org/abs/2510.27246`;
- code and repository copy: `https://github.com/mohammadtavakoli78/BEAM`;
- normal-scale dataset: `https://huggingface.co/datasets/Mohammadta/BEAM`;
- 10M dataset: `https://huggingface.co/datasets/Mohammadta/BEAM-10M`.

The Hugging Face dataset is CC BY-SA 4.0; the repository code is MIT. The
normal release currently advertises 90 rows and approximately 106 MB. These
facts are discovery notes, not input locks. Onboarding must pin an immutable
dataset revision and hash every consumed source file before any mechanism run.

BEAM has not previously been used in this repository. That makes it a fresh
population for this program, but public availability is not equivalent to a
sealed private holdout. The report must describe it as a new public corpus, not
an unread benchmark.

## 3. Scope and single new component

### 3.1 In scope

1. Acquire and hash-pin the official 100K, 500K and 1M splits.
2. Build a deterministic BEAM-to-`EpisodeStore` adapter from chronological chat
   messages only.
3. Create physically separate question-only and outcome-only surfaces.
4. Reproduce the deployed CC80-default and static-ASPECT controls from the
   pinned HH-003 package tree in a separate worktree.
5. Implement a study-private CC80-parent opportunity selector by porting the
   frozen TC-013/TC-014 behavior without changing its parameters.
6. Run label-blind three-arm context construction on all mechanically valid
   normal-scale questions.
7. Record full mechanism, cost, latency and selected-identity distributions.
8. Decide from predeclared viability gates whether a live pre-registration can
   be written.

### 3.2 Out of scope

- No reader answers, judge calls, official BEAM score or adoption decision.
- No 10M run in Part 1. The separately distributed 10M split remains untouched
  until a later registration explicitly assigns it a role.
- No renderer experiment, community grouping or question repetition.
- No recency ablation, budget sweep, ASPECT-share sweep, parser replacement,
  embedder replacement, query expansion, reranker or parameter tuning.
- No public `episodic-chat` API or default change.
- No use of conversation plans, narratives, user profiles, ideal responses,
  rubrics, question difficulty, generated evidence labels or answer keys by
  formation, retrieval, gating or scheduling code.

The only new component is the long-term protected-half selector. Corpus
onboarding is measurement infrastructure, not another treatment.

## 4. Corpus onboarding boundary

### 4.1 Acquisition and immutable source lock

The acquisition command must request an explicit Hugging Face revision rather
than `main`. Record:

- repository and dataset revision identifiers;
- downloaded filenames, byte sizes and SHA-256 values;
- split names and row counts;
- license files and dataset-card digest;
- downloader version and exact command; and
- a manifest digest over the ordered file list.

The raw dataset is retained read-only under an external-data location. Large
source files are not silently rewritten or normalized in place. Generated
canonical views are content-addressed derivatives with their own manifests.

### 4.2 Trusted one-way split

BEAM stores questions beside ideal responses and rubrics. A trusted corpus
preparation command is the only module allowed to read the complete source. It
emits two disjoint surfaces:

1. **Mechanism surface:** conversation id, scale, ordered chat messages,
   question category, exact question text, stable question key and source
   hashes.
2. **Outcome surface:** stable question key plus every official ideal response,
   rubric and scoring field needed by a future measurement process.

Part 1 imports only the mechanism surface. The outcome surface is sealed and
must not be importable from corpus, adapter, selector, exploration or context
rendering modules. A planted forbidden-field test must fail before real data is
processed.

The trusted splitter reports field presence and counts without printing values.
It must not repair, paraphrase, deduplicate or discard questions. Any missing or
ambiguous scoring field is recorded by key for later registration decisions,
not patched during onboarding.

### 4.3 Stable identities

Generated BEAM ids, local paths and timestamps cannot be comparison keys.
Define:

- `conversation_key = SHA256(domain || split || canonical ordered chat
  messages)`;
- `episode_key = SHA256(domain || conversation_key || canonical ordered
  message bytes || occurrence ordinal)`; and
- `question_key = SHA256(domain || conversation_key || category || exact
  question bytes || occurrence ordinal)`.

Canonicalization is UTF-8 byte serialization of parsed structured values with
sorted object keys and preserved list order. It does not normalize natural
language. Duplicate text occurrences remain distinct through their ordinal.

### 4.4 Chat adapter

Do not assume BEAM's `chat` field alternates cleanly because its public schema
contains batches and nested message structures. Part 1 first records the real
shape across every normal-scale row:

- batch, session and message counts;
- observed roles and role-transition frequencies;
- empty and non-string content;
- consecutive same-role messages;
- leading assistant or trailing unmatched user messages;
- timestamp availability and monotonicity; and
- exact flattened character and token distributions.

Only after that characterization may the adapter rule be frozen. The intended
mapping is one complete user/assistant exchange per episode, appended in source
order through the public `EpisodeStore.append()` API. If the corpus contains
role patterns that cannot be mapped without merging, dropping or inventing
content, onboarding stops and the draft is revised before mechanism output.

Conversation plans, profiles and narratives are metadata about how the
synthetic conversation was produced. They never become messages or retrieval
candidates.

## 5. Frozen common architecture

All three arms receive byte-identical episodes and queries. All use:

- the pinned `episodic-chat` formation and rendering behavior;
- `recency_window_n=32` as additive continuity outside retrieval allowance;
- `retrieval_budget_chars=32000` as the long-term allowance;
- CC80 dense/BM25 weights `0.8/0.2`, BM25 `k1=1.2`, `b=0.75`;
- Qwen3-Embedding-0.6B Q8_0 with source SHA-256
  `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`;
- solo embedding calls;
- exact serialized character accounting, skip-on-overflow packing and
  admission-resolved deduplication; and
- the public compact episode renderer.

C0 and T1 additionally share `aspect_share=0.5`, `en_core_web_sm` 3.8.0,
the six frozen facet families, and unused protected slack returned to unchanged
CC80 order. A0 does not instantiate an ASPECT selector or protected half.

Recent episode ids are excluded from the entire long-term candidate path in
all three arms. The final payload contains each episode at most once.

## 6. Arms

### A0 `DEPLOYED_CC80_DEFAULT`

Run the public package at the exact HH-003 source tree
`ae3058f072a9c5b8ce59b130066db11a977e7ab1` with:

```python
EpisodicConfig()
```

Behavioral claim to verify: after additive recency exclusion, rank the full
remaining store by frozen CC80 and skip-on-overflow pack that order under the
entire 32,000-character long-term allowance. No ASPECT parsing, proposal,
protected allocation or slack return occurs.

### C0 `DEPLOYED_STATIC_ASPECT`

Run the public package at the exact HH-003 source tree
`ae3058f072a9c5b8ce59b130066db11a977e7ab1` with:

```python
EpisodicConfig(aspect_enabled=True)
```

Both deployed controls run from the dedicated clean worktree. Their package
source, import graph, configuration JSON and installed distribution digest are
recorded before context construction. Neither is recreated by setting the
candidate strategy to a control value.

Behavioral claim to verify: after additive recency exclusion, the long-term
allowance protects half for one global CC80-weighted facet-saturation walk,
then returns unused protected slack to CC80.

### T1 `PARENT_OPPORTUNITY_ASPECT`

Use the same frozen library formation, ranking, packer and renderer. Replace
only the protected ASPECT proposal/admission rule with the exact carried
TC-013/TC-014 behavior:

1. Pack unchanged CC80 under the 16,000-character semantic half. The admitted
   identities, in CC80 order, are unique parents.
2. For every parent exactly once, seed covered facets from that parent alone.
3. Among candidates that individually fit the protected half, excluding all
   parents and all children proposed earlier, propose the candidate with the
   greatest positive frozen ASPECT marginal per exact additive character.
   Ties use CC80 rank and then stable conversation/content order.
4. Visit proposed parent-child edges in parent order. Counterfactually allocate
   the current retained children plus the proposed child under the unchanged
   50/50 allocator.
5. Reject a child that is not admitted by that allocation. Otherwise compute
   the exact CC80 identities selected without the child but displaced when it
   is present. Retain the child only when its raw ASPECT edge value is at least
   the summed frozen CC80 value of those displaced identities.
6. Merge unchanged CC80 order with retained children, pack under the same total
   32,000-character allowance and return unused protected capacity only to
   unchanged CC80 order.

There is no parent-bound cosine multiplier, global assignment, utility-first
packing, recursive child, second child attempt, capacity retry or tuned
coefficient. A child never becomes a parent.

T1 lives in study-private analysis code. It is not a public config field and
cannot be imported by the installed distribution. A later positive live result
would authorize a separate package-port verification, not silently convert
this prototype into deployed code.

## 7. Required reproduction anchors

Before BEAM output is accepted:

1. A0 and C0 reproduce the committed HH-003 default and static-ASPECT context
   identities and payload SHA-256 values for all available 1,540 queries, or
   the exact committed anchor population if an artifact uses a different count.
2. The study-private common-path adapter, when pointed at CC80-only or static
   ASPECT, reproduces A0 and C0 byte-for-byte but is not used to generate either
   deployed control's results.
3. T1 reproduces all 871 TC-014 development `opportunity` selected identity
   sequences and payload digests before additive recency is composed.
4. The composition layer reproduces CC-007's committed additive-recency final
   payload anchors for both the public default and static selector.
5. Reopening a frozen BEAM store reproduces every stored episode embedding and
   every context payload digest.

Counts alone do not satisfy any anchor. A failure stops before BEAM three-arm
summaries.

## 8. Part 1 three-arm exploration

### 8.1 Population

Subject to successful onboarding, run every question from the 90 normal-scale
conversations through A0, C0 and T1. Expected discovery counts are 20 100K, 35
500K and 35 1M conversations with approximately 1,800 questions; observed
counts replace these notes in the committed Part 1 report.

The exploration reads exact question text but no ideal response, rubric,
difficulty, evidence location or prior system result. It makes no generative
model calls.

### 8.2 What to record per question-arm

- stable conversation, episode and question keys;
- source split and question category;
- source/package/config/script hashes;
- complete CC80 order and scores;
- recent ids, semantic parents, proposed children, retained children,
  parent-for-child mapping and returned semantic ids, with asserted empty
  ASPECT fields for A0;
- every applicable ASPECT marginal, exact cost, displaced CC80 set and
  opportunity accept/reject reason;
- selected and dropped ids in order;
- exact retrieval payload and final payload SHA-256;
- retrieval and final characters, episode counts and budget state;
- facet-family counts and stop reason;
- embedding, parser, ranking, selection, packing and total wall time; and
- process count, worker count, CPU/GPU utilization and peak memory.

Payload text itself is a sealed artifact, not printed into logs.

### 8.3 Required distributions and contrasts

Report min, p05, p25, median, p75, p95, max and full histograms where discrete,
stratified by BEAM scale and question family:

- episodes and characters per conversation;
- recent, semantic, ASPECT, returned and total delivered counts;
- parent, proposed, retained and rejected-child counts;
- no-positive-child, no-fitting-child, rejected-capacity and rejected-value
  states;
- selected-set intersection, Jaccard, additions and removals for A0/C0, C0/T1
  and A0/T1;
- exact payload-character difference;
- CC80 ranks of arm-only episodes;
- facet coverage and per-family representation;
- context-construction latency and throughput; and
- traces on which each pair is byte-identical.

Also report each mechanism's behavior on the longest store, longest episode,
largest question, largest candidate pool and largest arm disagreement selected
without outcomes.

### 8.4 Degenerate and absorbing states

Demonstrate on real BEAM traces:

- fewer than 32 episodes and exactly 32 episodes;
- no long-term candidate after recency exclusion;
- one semantic parent and many semantic parents;
- no positive child, no fitting child and child rejected by capacity;
- child admitted but rejected by opportunity value;
- all proposed children retained;
- protected slack returned and no slack returned;
- A0/C0, C0/T1 and A0/T1 identical selections and materially different
  selections where each state exists; and
- exact termination after one finite attempt per parent.

Neither selector has cross-query feedback because `context()` is read-only.
Prove this by running a shuffled question order and reproducing every
question-arm payload digest. Within-query state still requires complete traces
showing exclusions only grow and no child or parent re-enters.

### 8.5 Exploration viability gates

- **G-SCHEMA:** every admitted conversation maps to strict, lossless
  user/assistant episodes; otherwise stop as `CORPUS_ADAPTER_NOT_IDENTIFIED`.
- **G-SEPARATION:** planted outcome-field access fails and the exploration
  import graph cannot reach the outcome surface; otherwise stop as
  `OUTCOME_LEAKAGE`.
- **G-ANCHOR:** all control and treatment reproduction anchors pass by ordered
  identity and payload digest; otherwise stop as `MECHANISM_NOT_REPRODUCED`.
- **G-BASELINE:** A0 uses the public default configuration, has no ASPECT trace,
  and spends no characters through protected allocation; otherwise stop as
  `BASELINE_NOT_DEPLOYED_DEFAULT`.
- **G-TREATMENT:** T1 changes at least one real final selected set and both
  identical and changed traces exist; otherwise stop as `TREATMENT_INERT_OR_DEGENERATE`.
- **G-BUDGET:** every long-term payload is within 32,000 characters, recent
  continuity remains additive, and no identity is duplicated; otherwise stop
  as `COMPOSITION_INVALID`.
- **G-RUNTIME:** the full normal-scale exploration completes deterministically
  within measured local resource limits without reducing corpus, candidates or
  registered behavior; otherwise stop as `INSTRUMENT_NOT_SCALABLE`.

These gates establish only that a three-arm live test is mechanically
possible. They do not prefer an arm.

## 9. Preflight

### Part 1 - required deliverable

Commit `BEAM_001_PART1_EXPLORATION.md` plus machine-readable corpus, mechanism,
distribution, trace and resource artifacts answering Sections 4-8. Part 1 may
change the later test design before registration. It cannot tune T1, inspect
outcomes or generate answers.

### Part 2 - checklist to answer after Part 1

- **PF1 Inputs:** name the immutable BEAM revisions, file hashes, licenses,
  source counts, canonical views, package trees, parser, embedder and every
  reproduction artifact.
- **PF2 Mechanism identity:** state one falsifiable behavioral sentence for
  BEAM adaptation, deployed recency, CC80, global static ASPECT, parent fan-out,
  opportunity admission, slack return, packing and rendering, each verified on
  committed real traces.
- **PF3 Gate ordering:** prove source lock precedes canonicalization; outcome
  separation precedes imports; anchors precede BEAM summaries; Part 1 precedes
  registration; registration precedes any reader implementation; complete
  answers precede blind scoring; and scoring commits precede arm mapping.
- **PF4 Reachability:** after Part 1 and before registration, size practical,
  statistical, scale-transfer and regression branches for primary C0/T1 and
  guardrail A0/T1 comparisons from the observed question population and
  plausible discordance without opening outcomes. Demonstrate every
  disposition synthetically in both directions.
- **PF5 Stable keys:** verify content-hash identities survive path moves,
  rebuilds, shuffled processing and duplicate text occurrences.
- **PF6 Reproduction:** satisfy every ordered-identity and payload-digest anchor
  in Section 7 before new summaries.
- **PF7 Feedback:** prove read-only cross-query independence and finite
  within-query termination on every normal-scale trace; include the longest
  intended trace.
- **PF8 Adequacy:** state what the observed population and scale strata can
  detect. A normal-scale run cannot establish 10M behavior, real-user transfer,
  reader generality or latency under production concurrency.
- **PF9 Surrogates:** more retained children, broader facets, higher overlap,
  faster retrieval, fewer characters or more official nuggets available can
  all pass while answer correctness falls. No exploration metric authorizes
  adoption.
- **PF10 Live requirement:** only a separately pre-registered, complete paired
  reader and blind-scoring run can decide whether T1 improves static ASPECT
  while remaining non-inferior to the deployed CC80 default. Beating C0 while
  failing the A0 guardrail is not an improvement disposition.

No checklist item passes by assertion. Each must cite a committed artifact and
hash.

## 10. Proposed implementation layout

```text
experiments/comparisons/beam_001/
  BEAM_001_IMPLEMENTATION.md
  BEAM_001_PART1_EXPLORATION.md
  BEAM_001_PRE_REGISTRATION.md           # later, standalone commit only
  artifacts/
    corpus/source_manifest.json
    corpus/mechanism_surface.jsonl.gz
    corpus/outcome_surface.sealed.jsonl.gz
    corpus/schema_report.json
    anchors/reproduction.json
    exploration/contexts.jsonl.gz
    exploration/traces.jsonl.gz
    exploration/summary.json
    exploration/runtime.json
src/analysis/
  beam001_corpus.py                      # trusted split command and hashes
  beam001_adapter.py                     # mechanism-surface chat adapter
  beam001_parent_opportunity.py          # study-private T1
  beam001_exploration.py                 # label-blind three-arm runner
tests/
  test_beam001_corpus.py
  test_beam001_adapter.py
  test_beam001_parent_opportunity.py
  test_beam001_exploration.py
```

The trusted splitter and outcome reader must be separate modules. Exploration
code may import the mechanism reader but not the trusted splitter's outcome
functions. Static source and import-graph checks enforce this boundary.

## 11. Runtime and hardware plan

Corpus preparation, spaCy parsing, embedding verification and independent
conversation/query shards must use all safely available CPU/GPU capacity.
Measure utilization during a small label-blind prefix; increase deterministic
worker count until CPU, GPU, memory bandwidth or storage is the measured
bottleneck. Record the selected worker count and why higher concurrency is
unsafe or slower.

Do not duplicate solo embedding calls merely to fill the GPU. Build each
episode and question vector once under the pinned call shape, content-address
it, and share the read-only vector cache between arms. Independent context
construction may then shard by conversation and question while preserving
deterministic per-key output.

Every JSONL row is appended, flushed and fsynced. Resume keys are content
hashes. A resumed run must reproduce the uninterrupted output digest after
canonical sorting. Long processes run detached from the agent session and have
PID, command, logs, progress counters and failure sentinels recorded under the
runtime artifact directory.

## 12. Execution and commit order

1. Review and commit this design alone.
2. Acquire BEAM at an immutable revision and commit only its manifest, license
   record and hashes, not an interpreted score.
3. Implement the trusted split, mechanism surface and schema audit; commit.
4. Implement A0/C0 reproduction and T1 study-private port; commit tests before
   running new BEAM mechanism output.
5. Run and commit all Section 7 anchors.
6. Run the label-blind normal-scale three-arm exploration with outcomes
   inaccessible; commit raw traces and summaries.
7. Write and commit `BEAM_001_PART1_EXPLORATION.md`.
8. Decide whether the viable mechanism and population justify a live design.
9. If authorized, write a standalone pre-registration that fixes reader,
   answer prompt, official-rubric treatment, judge, seeds, schedule, primary
   C0/T1 endpoint, required A0/T1 non-regression guardrail, two-sided
   interpretation, works bar, signal bar, scale guardrails, length handling,
   runtime, `recency_window_n=32` in all three arms and the claim boundary.
10. Commit that registration with no implementation files before any answer
    runner is written or called.

No answer generation is started by this document.

## 13. Stop conditions and interpretation

An adapter or reproduction failure is an instrument failure: it means BEAM-001
did not compare the named mechanisms. Treatment inertia means the proposed
contrast has no tested population on this corpus. Budget or duplication failure
means the candidate did not preserve the deployed composition contract.

None of those outcomes proves either deployed path is better. Conversely, an
exploration showing broader coverage or different selected episodes does not
prove parent opportunity is better. The question remains open until a valid
live paired result exists. A later result where T1 beats C0 but fails its
pre-registered A0 non-regression guardrail cannot receive an improvement or
package-port disposition.

Even a later positive BEAM result would be bounded to this synthetic public
corpus, the locked reader and judge, and the tested normal scales. It would make
the candidate eligible for separate package-port verification. It would not by
itself change the public default, establish 10M behavior or claim real-user
deployment fitness.
