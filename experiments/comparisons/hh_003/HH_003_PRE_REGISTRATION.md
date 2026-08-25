# HH-003 Pre-Registration - deployed episodic-chat on the Mem0 LoCoMo harness

**Status:** `REGISTERED - written before implementation and before any paid call`
**Date:** August 24, 2026
**Predecessor:** HH-002, which ran a frozen NF-004 pair-ranking transcription
rather than the subsequently adopted public `episodic-chat` read path

## 1. Question

What do the two shipped `episodic-chat` configurations score when inserted at
the memory seam of the paper-era Mem0 LoCoMo harness reproduced by HH-002?

This is a deployment validation, not a new retrieval design. HH-003 changes
only the memory layer. It preserves HH-002's corpus, 1,540 scored questions,
answer prompt, judge prompt, dated answerer/judge model, deterministic metrics,
item keys, and Batch API transport.

## 2. Fixed implementation under test

The implementation is the installable `episodic-chat` package at repository
tree `ae3058f072a9c5b8ce59b130066db11a977e7ab1`, version `0.2.0`.

| Arm | Public configuration | Purpose |
|---|---|---|
| `A_EPISODIC` | `EpisodicConfig()` | Shipped default; ASPECT off |
| `A_EPISODIC_ASPECT` | `EpisodicConfig(aspect_enabled=True)` | Shipped optional ASPECT path |

All other config fields remain at their public defaults. In particular:

- `recency_window_n=32`;
- `retrieval_budget_chars=32000`;
- CC80 uses dense/BM25 weights `0.8/0.2`, BM25 `k1=1.2`, `b=0.75`;
- ASPECT uses `aspect_share=0.5` and `en_core_web_sm`;
- the pinned embedder is Qwen3-Embedding-0.6B Q8_0, SHA-256
  `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`,
  one text per call.

The 32,000 characters are a **long-term retrieval allowance**, not a total
context ceiling. The latest 32 complete episodes are rendered additively
outside it. No result may describe these arms as having a 32k total context.

## 3. Adapter boundary

For each LoCoMo conversation, a fresh `EpisodeStore` is built in source order.
Each adjacent user/assistant exchange becomes one episode through the public
`append()` API. Message content retains HH-002's harness timestamp convention:
`{timestamp} | {speaker}: {text}`. The store's own `User:` and `Assistant:`
labels remain untouched. No summary, QA answer, evidence annotation, category,
or rubric artifact enters formation or retrieval.

For each scored question, the adapter calls public `EpisodeStore.context()`
with the question text. The returned payload is inserted unchanged into the
vendored HH-002 RAG answer prompt. The two arms differ only in
`aspect_enabled`; they use separate stores with identical source messages.

The adapter records the full `ContextReport`, payload SHA-256, payload length,
retrieval payload length, episode counts, latency, and stable delivered source
identities in addition to HH-002's prediction and judgement fields.

## 4. Harness and population

- Corpus: `C:\Users\muzaf\Downloads\locomo10.json`, 2,805,274 bytes,
  SHA-256 `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Population: all 10 conversations; 1,986 questions total; the same 1,540
  non-category-5 questions scored by HH-002 and the published harness.
- Upstream harness: `mem0ai/mem0` commit `7b3abd06`, `evaluation/`.
- Answerer and judge: `gpt-4o-mini-2024-07-18`, temperature 0.0.
- Answer and judgement transport: OpenAI Batch API. Local embedding calls are
  deterministic and are not sent to OpenAI.
- Vendor prompt SHA-256 values remain HH-002's locked values:
  `744495b77f2955d437017fd33a0b7156ef41426b7ae8277e5efb92382f234b78`,
  `0c6b92630ba4c22fd29e718d095abb2d6ffba10c04d00962e94bca4a65b23249`,
  and `44fb3d8f7a1f37b2430772cf90518a32172e4056b7a0dec085402763fd179b9f`.

The API key is read only from `OPENAI_API_KEY`. It is never written to a run
header, artifact, source file, shell history, or command-line argument.

## 5. Controls and comparison

HH-002's sealed rows are reused, not regenerated. Reuse avoids spending money
to obtain new stochastic answers from unchanged controls and makes the change
from the old custom arm to the deployed library explicit.

| Row | Prediction SHA-256 | Judgement SHA-256 |
|---|---|---|
| HH-002 `A_CDW` | `37601e42b9f24fb6a6d01d78911f2b33a7a0554b568fff1151d3964353ae5628` | `367210a4b6aa37c763db23abd46a33810b6953bdb92be291146f8b8277d9d3cc` |
| HH-002 `A_RAG` | `bc49bb20a6172dcfa68e3ef825487c776674af0f95e19cf9509d4dcaea68af` | `dd3ff262f3a1b27fc22a445c2f578676974c547a2eca6df1120f5cbe9a24c374` |
| HH-002 `A_FULL` | `a6f82d0ed63eedb3aa1c84472c7ac978e5db6e5c8d5323cdf23ecbc712a150c9` | `467521c8e972d3728fac93b772ab453b3708f4d26607ecba16e1062e6ee6649a` |

The Mem0-authored published rows remain attributed inherited references; no
per-item test is possible against rows whose answers were not published.

## 6. Endpoints and reporting

Primary endpoint: HH-002 `llm_score`, the mean binary CORRECT verdict over
1,540 items from the vendored Mem0 judge prompt.

Secondary answer endpoints: deterministic F1 and exact match. Operational
metrics include context characters, retrieval characters, recent/semantic/
ASPECT episode counts, truncation, dropped episodes, search latency, generation
tokens, completion tokens, malformed answers, failures, and category scores.

Report both new arms regardless of ordering. Report paired item-level
discordances and two-sided exact binomial sign tests for:

1. `A_EPISODIC_ASPECT` versus `A_EPISODIC`;
2. each new arm versus HH-002 `A_CDW`;
3. each new arm versus HH-002 `A_RAG` and `A_FULL`.

These tests characterize measured differences. HH-003 registers no directional
success bar, no automatic adoption decision, and no tuning after results. The
primary endpoint and deterministic F1 must both be shown; judge score alone
cannot certify answer quality.

## 7. Gates and run order

1. `G0 PREFLIGHT`: all checks in section 8 pass and are committed.
2. `G1 IMPLEMENTATION`: adapter fidelity, leakage, budget, config isolation,
   stable identity, and resume tests pass; implementation is committed clean.
3. `G2 REPLAY`: the unchanged HH-002 scoring code reproduces all reused row
   digests and summary values by item identity before any new answer submission.
4. `G3 PREFIX`: both arms produce byte-identical contexts and reports on a
   repeated committed prefix, and ASPECT differs from default on at least one
   prefix item. An inert treatment is an instrument failure.
5. `G4 PAID PILOT`: one committed conversation and a fixed question prefix are
   generated and judged only to verify API access, response shape, resume, and
   cost accounting. Pilot answers are excluded from mechanism design and are
   reused in the full run by stable item key.
6. `G5 FULL RUN`: build and seal all 3,080 answers before submitting either
   arm's judgements. Open scores only after both judgement populations are
   complete.

Any failed gate stops the later stages. No partial score is interpreted as an
arm result. Batch retries may resend only absent stable item keys; completed
answers are never regenerated.

## 8. Preflight

### Part 1 - executed exploration

Executed on August 24, 2026 against committed LoCoMo development traces using
the installed package, with zero new embedding or generative calls.

Behavioral identity: the public read path always adds the latest 32 episodes,
then spends up to 32,000 further characters on CC80; enabling ASPECT protects a
50% static facet-saturation route and returns unused protected slack.

The package reproduced 4,355/4,355 frozen CC80/ASPECT order, selection, and
payload groups with zero mismatches. The activated public default reproduced
871/871 final payloads, with zero retrieval-budget breaches and zero duplicate
deliveries. All 871 final payloads exceeded 32k because recency is additive.

At 32k ASPECT selected 80-126 long-term episodes (median 100); 37-54 were
ASPECT admissions (median 46). It stopped because no complete candidate fit on
842/871 questions and because no positive marginal remained on 29/871. Across
60,465 admission steps at 16k and 32k, facet coverage was monotone and no
admission repeated. This mechanism has no feedback from one query to the next:
`context()` is read-only, so there is no cross-query absorbing state. Both
degenerate ASPECT stopping states occurred on real traces.

Executed artifacts:
`experiments/components/episodic_chat/artifacts/cc007/preflight.json` and
`experiments/components/episodic_chat/artifacts/cc007/activation.json`.

### Part 2 - checklist

**PF1 Inputs exist.** Corpus hash and count are fixed in section 4. The package
tree, three prompt hashes, six reused control hashes, 871-question exploration,
1,365 candidates, and zero cache misses were read and verified above.

**PF2 Mechanism identity.** The 4,355 exact group replay and 871 activated
payload replay verify CC80, ASPECT, recency, retrieval allowance, protected
share, slack return, and public default state against their names.

**PF3 Gate ordering.** The runner must encode the section 7 state machine and
write a run precondition before submissions. Tests must prove paid submission
raises unless G0-G3 artifacts exist and match the current script/package SHA.

**PF4 Thresholds achievable.** There is no outcome threshold. G3's non-inertness
is reachable: committed exploration records ASPECT selections and both stop
states on all 871 questions. Completion denominators are exactly 1,540 per arm.

**PF5 Stable keys.** Items key on `sha256(sample_id + NUL + source_index + NUL +
question + NUL + gold_answer)`. Episode comparison keys derive from source
conversation identity and source turn indices, never SQLite UUIDs or paths.

**PF6 Reproduction anchor.** G2 requires byte hashes and item-level summaries
for the six HH-002 control files in section 5 before paid submission. Package
replay is already exact on 4,355 groups and 871 final payloads.

**PF7 Absorbing-state proof.** Public `context()` is read-only and one query's
selection cannot affect another. The full 871-question real trace had monotone
ASPECT admissions, zero repeats, and both finite stop states. The runner must
also assert store bytes are unchanged across all queries.

**PF8 Ablation adequacy.** The committed 871-question exploration is longer
than the 35-turn minimum and spans four conversations. It detects inert arms,
budget breaches, constant selection, repeated admission, and query-time store
mutation. It cannot detect live reader use, API model drift, six-conversation
transfer, or high-concurrency service behavior; G4-G5 cover the first two, and
the full ten-conversation run covers transfer. Batch calls are independent, so
this study makes no interactive concurrency claim.

**PF9 Surrogate audit.** Exact replay can pass while retrieval is useless;
budget compliance can pass while total prompts exceed 32k; selected evidence
can pass while the reader ignores it; judge score can pass on lenient grading;
reused controls can differ because API time changed. Residuals are accepted and
reported. Live answers plus deterministic F1 are required, operational metrics
are not treated as quality, and cross-date contrasts are labelled as such.

**PF10 Live evaluation.** Availability is not a verdict. G5 runs both memory
configurations through the dated HH-002 answerer and judge over all 1,540 scored
questions. No offline delivery result substitutes for those answers.

## 9. Limits

LoCoMo is spent and this is not confirmatory evidence. The two new arms share a
current API run, while reused controls were generated earlier; cross-date
differences confound memory with vendor service time despite the dated model
name. ASPECT-on is an optional shipped configuration, not the public default.
This study tests one benchmark, one 32k retrieval allowance, one answerer/judge,
and no interactive conversation. It cannot establish general superiority,
latency at production concurrency, or a result for Mem0's current product.
