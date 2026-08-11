# SAL-001 - Independent Surprisal-Proximity Diagnostic

**Type:** Pre-registered external-corpus diagnostic
**Date:** August 11, 2026
**Branch:** `study/sal-001-surprisal-proximity`
**Status:** PRE-REGISTERED - NO LABEL JOIN OR OUTCOME ANALYSIS
**Authorization:** Program author approved the biological-memory research arc end to end on August 11, 2026
**Grounding:** `HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md` P1-P4 and F2
**Outcome ceiling:** `CHARACTERIZED`; no retrieval component, ablation, live run, or adoption

## 1. Decision this study owns

The reference architecture's weakest joint is its replacement for biological
reward: mean token surprisal on incoming user text. P2 then makes the stronger
claim that an **independent** salient event confers value on temporally adjacent
episodes without reading their content. F2 says to test this formation premise
before implementing the architecture.

SAL-001 asks:

> After removing token length, lexical rarity, and conversational-position
> effects, are exchanges needed by a later question adjacent to independently
> surprising user input more often than other exchanges in the same session?

The target exchange's own user and assistant text never contributes to its
predictor. This prevents a rare evidence phrase from certifying its own value.
Adjacency means the immediately preceding or following user/assistant exchange
inside one source session. Adjacent LongMemEval sessions are not neighbors:
their assembly as a retrieval haystack does not establish a continuous event
sequence.

This study implements no tag, capture, accessibility, graph, replay, retrieval,
packing, generation, or answer scoring. It changes no shipped subsystem.

## 2. Immutable inputs and population

Execution refuses any hash, byte-count, schema, or count mismatch.

| Input | Identity |
|---|---|
| LongMemEval V1 cleaned | `longmemeval_s_cleaned.json`, 277,383,467 bytes, SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`, upstream commit `98d7416c24c778c2fee6e6f3006e7a073259d48f` |
| EC-001 adaptation record | committed repository file; exact SHA-256 recorded by Preflight |
| EC-001 Tier 2 subset registration | committed repository file; exact SHA-256 recorded by Preflight |
| Biological-memory reference | committed root file; exact SHA-256 recorded by Preflight |
| Surprisal model | `Qwen3.6-27B-UD-Q6_K_XL.gguf`, 26,015,429,760 bytes, SHA-256 `f3b4a622e06e8ade06ec5c0eb9b40ed7c9bd707b5fada46c0215f4ab4a6bc32b`, snapshot `5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace` |
| Runtime | `llama-cpp-python==0.3.25`; exact package, CUDA, driver, GPU, and GGUF metadata recorded at run time |

The population is a deterministic holdout from the six answerable LongMemEval
strata: `single-session-user`, `single-session-assistant`,
`single-session-preference`, `temporal-reasoning`, `knowledge-update`, and
`multi-session`. For each stratum, sort by
`SHA256("5005\0" + stratum + "\0" + question_id)` and select ranks 21-30.
Ranks 1-20 were EC-001's registered Tier 2 subset. Abstention items are absent
because they have no evidence location. The 60 selected IDs, in the stratum
order above and rank order within stratum, have newline-list SHA-256
`fc592afdb7c37dbb34223335e526bd3dabf14c36728d546bdacb2fda09610c36`.
No item may be replaced.

An eligible source session must be named by `answer_session_ids`, contain at
least one `has_answer` marker, and consist entirely of strict adjacent
`user, assistant` pairs. An eligible target exchange must have at least one
immediate exchange neighbor. Sessions without a marker, irregular sessions,
and one-exchange sessions are reported and excluded, never repaired.

Exploration found 95 named evidence sessions: one has no marker and one is
irregular. The fixed eligible population is 93 sessions, 545 exchanges, 98
marked evidence exchanges, 447 unmarked exchanges, 97 marked exchanges with a
neighbor, and 92 sessions with both an analyzable positive and negative. Any
different executed count stops before scoring.

## 3. Separation and ordering

Three processes have disjoint permissions.

1. **Seal.** A measurement-only sealer may read `answer_session_ids` and
   `has_answer`. It writes a scorer manifest containing only stable content
   hashes, source order, roles, and text, plus a separate sealed label file.
   It omits questions, answers, question dates, question types, evidence flags,
   and raw benchmark identifiers from the scorer manifest.
2. **Score.** The surprisal scorer may read only the scorer manifest, GGUF, and
   runtime configuration. It cannot import the sealer or analyzer and cannot
   open the dataset, sealed labels, questions, answers, or prior outcomes.
3. **Analyze.** The analyzer may join committed scorer output to sealed labels
   by session-content SHA-256 and zero-based exchange index only after the
   complete label-blind score artifact and passing PF1-PF10 artifact are
   committed ancestors.

Planted forbidden files and runtime open sentinels must fail loudly. Git
ancestry, source grep, and AST import traversal enforce the order. Merely
hiding label fields in one Python object does not satisfy this separation.

## 4. Fixed surprisal scorer

All settings below are authoritative and are not swept.

```text
MODEL = Qwen3.6-27B-UD-Q6_K_XL.gguf at the SHA in Section 2
SEED = 5005
N_CTX = 6144
N_BATCH = 256
N_UBATCH = 256
N_GPU_LAYERS = -1
FLASH_ATTN = true
LOGITS_ALL = true
PARALLEL = 1
SPECULATIVE_DECODING = none
CHAT_TEMPLATE = exact tokenizer.chat_template stored in the GGUF
SYSTEM_MESSAGE = none
ADD_GENERATION_PROMPT = false
TOKENIZATION = add_bos=false, special=true
SCORED_TEXT = rendered user-content tokens only
EVENT_SCORE = arithmetic mean negative log probability over those tokens
```

Each session is rendered independently in source order. No preceding or
following session is context. For each user turn, its scored token interval is
the changed interval between the full rendering and an otherwise identical
rendering with only that user's content replaced by the empty string. The
unchanged prefix and suffix must be unique, non-overlapping, and reconstruct
the full token sequence. Role markers, newlines, end markers, assistant text,
and the target exchange's own text are not scored as its neighbor signal.

For scored token at sequence index `j`, the probability is the softmax of
logits row `j-1`; compute log-softmax with a float64 log-sum-exp over the GGUF's
complete vocabulary. Empty or ambiguous spans stop. Every eligible session
must fit `N_CTX`; truncation is prohibited. The explored maximum is 5,499
tokens against 6,144.

The behavioral identity is:

> The scorer returns deterministic mean teacher-forced negative log
> probability for each rendered user-content span conditioned on earlier
> messages in the same session; it does not measure embedding novelty,
> generation uncertainty, evidence content, or answer relevance.

## 5. Label-blind adjustment and independent-neighbor signal

Compute model-token document frequency over the 545 user-content spans in the
scorer manifest. For token `v` and `N=545` spans:

```text
idf(v) = log((1 + N) / (1 + df(v))) + 1
```

Before opening labels, fit one ordinary least-squares model over all events:

```text
mean_nll ~ 1
         + log1p(content_token_count)
         + mean_content_token_idf
         + normalized_exchange_position
         + log1p(preceding_rendered_token_count)
```

`normalized_exchange_position` is `i / (session_exchange_count - 1)` for
zero-based exchange `i`. The event's adjusted salience is its OLS residual.
Record coefficients, rank, condition number, residual-feature correlations,
raw and adjusted distributions, and every event value before labels open.
Rank deficiency or non-finite output stops.

For target exchange `i`:

```text
prior(i) = adjusted_salience(i - 1), when i > 0
next(i)  = adjusted_salience(i + 1), when i + 1 < session length
symmetric_neighbor(i) = mean of the available prior(i), next(i)
```

The mean, rather than maximum or sum, prevents interior exchanges from
receiving a mechanical advantage merely because they have two neighbors.
`prior`, `next`, and `symmetric_neighbor` never use exchange `i`.

## 6. Outcomes and fixed inference

Within each eligible session, compare every marked target with every unmarked
target that has the required predictor. A comparison scores 1 when the marked
target has the larger predictor, 0.5 on equality, and 0 otherwise. Average
comparisons within session, then macro-average sessions. This is the
within-session AUC. Sessions, not exchange pairs, are the replication unit.

The primary value is adjusted symmetric-neighbor AUC. Also report raw-NLL
symmetric AUC, adjusted prior-only AUC, adjusted next-only AUC, each stratum's
adjusted symmetric AUC, and all session-level values.

The primary one-sided null is computed with 100,000 Monte Carlo permutations,
seed 5005. Within every session, permute labels while preserving its exchange
count and marked count; predictors and the label-blind OLS fit remain fixed.
Use `(1 + exceedances) / 100001`. Report a 10,000-resample session-cluster
bootstrap 95% interval with seed 5005 for description only; it is not a gate.

An AUC of 0.60 means that a randomly paired evidence exchange has the stronger
independent-neighbor signal 60% of the time within its own source session. It
is the minimum practical effect; statistical significance alone cannot pass.

## 7. Preflight

### Part 1 - completed exploration to reproduce

The committed companion exploration record binds the following observations:

- The exact Qwen scorer gave mean NLL 4.6384821217893855 for a repeated
  predictable sentence and 11.088347410991723 for a random access phrase.
  The predictable score repeated exactly in a fresh reset.
- The 60-history selection has the exact counts in Section 2. The 93 eligible
  sessions contain 286,152 rendered tokens; median 3,306, 95th percentile
  4,306, maximum 5,499, and none exceed `N_CTX`.
- All 545 eligible user turns are non-empty. Evidence exchanges have 49 prior,
  91 next, and 43 two-sided neighbor observations. Directional bars are
  therefore computable but have unequal precision.
- The scorer is stateless across sessions after reset. It has no feedback or
  absorbing state. Constant output remains a possible empirical failure and
  is tested from the complete score distribution.

After implementation, Part 1 must reproduce these corpus identities, execute
the scorer on the complete label-free manifest, and repeat the first three
content-hash-sorted sessions in a fresh process with byte-identical canonical
score rows. Findings cannot change Sections 2, 4, 5, 6, or 8; a mismatch stops.

### Part 2 - PF1-PF10

| Check | Required executed evidence before labels open |
|---|---|
| PF1 inputs | Recompute every Section 2 hash, byte count, schema, selection identity, population count, model metadata, and maximum token length |
| PF2 identity | Execute token-span reconstruction, row indexing, log-softmax, session reset, adjustment, and neighbor exclusion on synthetic and real label-free traces; verify the Section 4 identity |
| PF3 ordering | Git ancestry and runtime sentinels prove registration, authorization, sealer, label-blind scores, and PF1-PF10 precede label-file opening and analysis |
| PF4 reachability | Synthetic fixtures must produce every disposition; AUC 0, 0.5, 0.60, and 1.0; both directional bars; six-stratum pass/fail; permutation `p <= 0.01`; no executed outcome may be used |
| PF5 stable keys | Dataset SHA, session-content SHA-256, exchange index, rendered-content SHA-256, and token-sequence SHA-256 only; no paths, timestamps, or generated IDs |
| PF6 reproduction | Reproduce EC-001's registered ranks 1-20 selection identity before deriving ranks 21-30; reproduce the exact synthetic NLL anchor and fresh-process prefix digest |
| PF7 absorbing state | Prove scorer reset and complete score identity on repeated real sessions; no output feeds a later input; report constant-score and zero-variance checks |
| PF8 adequacy | State that 60 histories and 92 AUC sessions test local one-exchange adjacency only; they cannot test longer tag windows, retrieval, 35-turn integration, endurance, or live answers |
| PF9 surrogate | Execute the Section 9 audit and record corpus construction, marker incompleteness, false-negative controls, surprisal/reward mismatch, and model-specificity residuals |
| PF10 live requirement | State that SAL-001 is diagnostic, not delivery evidence; any later accessibility component requires its own offline gates, 35-turn ablation, and live decision |

Every check cites a committed artifact. A prose assertion or checked box fails.

## 8. Binding gates and dispositions

Stop at the first failed gate. All AUCs below use the macro session definition.

| Gate | Binding bar | Failure disposition |
|---|---|---|
| G1 integrity | Part 1 and PF1-PF10 pass; label separation, selection, population, scorer, adjustment, determinism, and hashes are exact | `INTEGRITY_STOP` |
| G2 independent proximity | Adjusted symmetric-neighbor AUC is at least 0.60 and one-sided permutation `p <= 0.01` | `NO_INDEPENDENT_PROXIMITY` |
| G3 not a raw confound | Raw symmetric-neighbor AUC is at least 0.55 and adjusted AUC is no more than 0.02 below raw AUC | `LENGTH_RARITY_OR_POSITION_CONFOUND` |
| G4 temporal symmetry | Adjusted prior-only AUC and next-only AUC are each at least 0.55, and their absolute difference is at most 0.10 | `ASYMMETRIC_TEXT_SIGNAL` |
| G5 breadth | At least five of six stratum AUCs exceed 0.50 and none is below 0.45 | `NON_GENERAL_SIGNAL` |

If G1-G5 pass, disposition is `SALIENCE_PROXY_SUPPORTED_OFFLINE`. This permits
only a new pre-registration for one minimal accessibility-separation component
with fixed retrieval identities. It does not authorize that implementation in
this branch.

If any of G2-G5 fails, the surprisal-driven P1-P4 tag/capture path in
HYPOTHETICAL-001 is killed for this program. Do not tune a threshold, widen the
neighbor window, change the aggregator, substitute explicit importance cues,
or return to the c121 corpus. The orthogonal P5/P9 supersession study remains
permitted because it does not depend on F2.

All thresholds are mechanically reachable: within-session AUC spans [0, 1],
synthetic strictly ordered predictors reach each point-effect bar, 100,000
permutations resolve `p <= 0.01`, both directions have positive observations,
and all six strata have eligible sessions. PF4 must demonstrate this before
the label join.

## 9. Surrogate audit and limitations

| Observed pass | Property that can remain false | Control or residual |
|---|---|---|
| High token NLL | Biological reward prediction error | Accepted grounding gap; this is the proxy under test |
| Adjacent signal | Target content caused or captured salience | Target exchange is excluded, but causal capture is not observed |
| Marker predicts later need | Every relevant exchange is labeled | Named-session and turn-marker incompleteness can create false-negative controls |
| Within-session AUC | Natural conversation ecology | LongMemEval is curated and partly synthetic; external replication remains residual |
| Adjustment passes | All lexical and structural confounds are gone | Only the four registered observable covariates are removed |
| Symmetry passes | A longer symmetric tag window works | Only immediate prior/next exchanges are tested |
| Six strata pass | General conversational relevance prior | One benchmark and one model remain |
| Statistical bar passes | Effect is useful in a 32k retriever | Practical AUC floor helps; a later fixed-identity study is still required |
| F2 passes | P1-P4 architecture works | Tags, capture gain, accessibility, replay, and consolidation remain untested |

The benchmark's evidence sessions were selected for later questions; SAL-001
does not claim that every unmarked exchange is useless. Label noise biases the
within-session contrast in an unknown direction. Full event and session rows,
not only aggregate AUC, are required so this limitation remains inspectable.

## 10. Runtime, artifacts, and exclusions

Set `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and
`NUMEXPR_NUM_THREADS=1`. Record command, process ID, package lock, model and
template hashes, CUDA and driver versions, GPU, peak RSS/VRAM, elapsed time,
token throughput, source commit, script SHA after scoring, and explicit UTF-8.
Artifacts are canonical UTF-8/LF JSON or JSONL, refuse overwrite, and contain
no generated timestamps in comparison digests.

Required artifacts are the selection manifest, seal report, label-free scorer
manifest, sealed labels, scorer output, Part 1 report and repeat digest,
PF1-PF10 report, analyzer output, gate report, and study report. Scorer outputs
contain hashes, indices, token counts, features, NLL, and residuals but no
benchmark labels or answer text. The label join produces complete session rows
and every aggregate needed to recompute the result.

No generation occurs. No answer is scored. No embedding, retrieval, packing,
32k block, memory state, ablation, or live inference is run. A failed gate is a
completed negative result, not an invitation to amend the mechanism.

