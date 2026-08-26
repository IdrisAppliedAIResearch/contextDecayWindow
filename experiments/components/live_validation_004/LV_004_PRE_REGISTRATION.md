# LV-004 — deterministic completion repair and live reader verdict

**Type:** registered instrument repair of a frozen live reader batch  
**Status:** pre-registered; not yet runnable  
**Date:** 2026-08-26  
**Authorization:** completion of the program owner's requested TC-014 live test

## 1. Question and predecessor

Does TC-014 opportunity admission's 32k evidence-delivery change convert into
more correct reader answers than full-budget CC80 on the questions where their
offline complete-evidence outcomes differ?

LV-003 generated and preserved the complete 170-response schedule. Its binding
gate stopped judging because two balanced responses for the same question hit
the 512-token output allowance. The remaining 168 responses stopped naturally.
No blind surface, judgment, arm score or outcome was produced.

LV-004 changes no retrieval, prompt, model, seed, sampling, item, replicate,
judge or endpoint. It completes only the two mechanically identified truncated
prompt/seed records with a 2,048-token allowance. A replacement is admissible
only when its response text begins byte-for-byte with the preserved response.

This is selected LoCoMo development characterization, not an overall benchmark
score, fresh-corpus confirmation, production-adoption gate or tuning study.

## 2. Frozen inputs and population

- LV-004 Part 1 artifact SHA-256:
  `1fa6cb263f0a8650fb18a4aef2e796c040ca5aa42608b63e1996d193b9098755`;
  commit `676e2922`.
- LV-003 answer JSONL SHA-256:
  `e7a9a2343182502d0be1675ba5b797a2115e49b873709cb3614e22a9bd55e784`;
  170 rows, 168 naturally stopped, 2 truncated.
- Frozen prompt artifact SHA-256:
  `c01cf11a5e2750c2ed8c03e90c813af7263de8a7fd2c4b78bacb72aa1207d5d8`.
- TC-014 selection and per-question outcome SHA-256 values remain
  `32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7`
  and `ce73bfcb0b3c9a1d7d94e89023ce7ef7b9fbf928eb44a1669699ec3f37324bb0`.

The population remains all 17 32k availability-discordant questions. The
primary is 16 answerable items: 11 offline opportunity gains, 5 losses;
9 targeted, 5 breadth and 2 other. One category-5 item is refusal-only
secondary. Canonical question-content hashes are the comparison keys.

The only replaceable keys are:

1. `conv-42`, source 79, `FULL_CC80`, replicate 2, seed 5007;
   prompt tokens 8,416 and preserved output tokens 512.
2. `conv-42`, source 79, `OPPORTUNITY`, replicate 3, seed 5008;
   prompt tokens 8,447 and preserved output tokens 512.

No other response may be regenerated or replaced.

## 3. Runtime and repair

The repair reuses Ollama 0.33.0, `qwen-custom:latest` manifest
`3516cd593f43`, Qwen 3.5 27.3B Q6_K, blob `sha256-773f…`, one RTX 5090 at
100% GPU, raw mode, `think:false`, the sealed closed-think suffix,
`num_ctx=65536`, temperature `.6`, top-p `.95`, top-k `20`, min-p `0`, repeat
penalty `1.0`, and the original per-record seed.

Only `num_predict` changes from 512 to 2,048 for the two repair calls. Each
repair is appended, flushed and fsynced before the next call. Originals and
repairs remain separately auditable. The merged answer artifact replaces
exactly the two original records and carries a hash link to each original.

Repair stops without judging unless:

- exactly the two registered keys are present once each;
- both calls stop naturally before 2,048 tokens;
- each repaired response text starts with its original text byte-for-byte;
- model, seed, prompt digest, prompt-token count and schedule identity match;
- all other 168 serialized rows remain byte-identical as canonical JSON values;
- the merged schedule contains 170 unique, complete, non-truncated responses.

No best-of-N, retry after a valid call, answer selection or correctness-aware
repair is permitted. A server error may be recorded but not silently retried.

## 4. Blinding, judging and endpoints

The repaired 170-answer artifact is committed before scoring. A seeded SHA
shuffle hides arm, replicate, context, offline direction and delivery state.
Each of 160 primary answers receives three blind semantic-correctness passes
with the frozen HH-001 binary rubric. Majority of three is the answer verdict;
majority of five answer verdicts is the item-arm verdict. Judges use the same
local model with `num_predict=128`, temperature `.2`, top-p `.9`, top-k `20`
and seeds 9005–9007. Unparseable or truncated judging stops before unblinding.

Normalized gold-string containment is a cross-check only. The category-5 item
is scored only for exact normalized `I don't know` refusal. Report reader
unanimity, judge disagreement, unsupported correct majorities and artifacts.

For 16 primary items report paired semantic-correctness gains, losses, ties,
net and descriptive exact McNemar p for combined, targeted, breadth, other,
offline-gain and offline-loss strata.

## 5. Locked disposition

- **`CONVERTS`:** overall semantic net at least `+3`; targeted and breadth
  nets nonnegative; no endpoint-sign reversal; every validity gate passes.
- **`WEAK_CONVERSION`:** overall semantic net `+1` or `+2`; targeted and
  breadth nets nonnegative; no endpoint-sign reversal; every gate passes.
- **`NO_CONVERSION`:** overall semantic net zero with no validity failure.
- **`REGRESSES`:** overall net negative, or targeted or breadth net negative,
  with no validity failure.
- **`NOT_INTERPRETABLE`:** contamination, repair failure, truncation,
  prompt/runtime drift, incomplete schedule/judging, mapping-order failure, or
  opposite nonzero signs between semantic correctness and containment.

The `+3` bar remains half the answerable offline complete-evidence net of `+6`.
No result automatically authorizes deployment or a parameter sweep.

## 6. Preflight — binding before repair generation

- **PF1:** hash/count this registration, Part 1, LV-003 answers and summary,
  frozen prompts, corpus, TC-014 inputs, runtime/model and GPU.
- **PF2:** reproduce the 170-row distribution, the exact two repair keys, all
  34 payload/prompt identities and the behavioral identity: continuation of
  two truncated deterministic streams, not a new live comparison.
- **PF3:** prove registration and prompt seal precede repair; append+fsync
  precedes the next repair call; merged answers precede blind scoring;
  judgments precede mapping opening. Early gold and extra replacement fail.
- **PF4:** mechanically reach both prefix-pass/fail and truncation pass/fail;
  synthetic rows reach all five dispositions and endpoint-sign reversal. Both
  real offline directions and both repaired arms are nonempty.
- **PF5:** use content-hash plus arm plus replicate keys; reject duplicates,
  incomplete joins, unexpected repair keys or an altered 168-row complement.
- **PF6:** reproduce all 34 TC-014 payload sequences, costs, prompt digests and
  the committed LV-003 answer file by identity and SHA-256.
- **PF7:** rerun one non-repair full prompt twice at `num_predict=2048`, seed
  5005; require byte-identical, nonempty, naturally stopped output and the
  registered model fully on GPU. No feedback state exists between prompts.
- **PF8:** five reader replicates support item-majority and instability only;
  16 enriched items cannot resolve overall accuracy, small effects, transfer
  or adoption. No stateful 120-turn run makes a 35-turn ablation applicable.
- **PF9:** guessed correctness, containment blindness to composition,
  same-model judge bias, availability enrichment and continuation-length
  sensitivity remain residuals. Prefix identity prevents answer replacement
  within the first 512 tokens but does not make the tail causally inert.
- **PF10:** this is the required live reader test; availability is an input.

Binding gates: the carried LV-003 no-memory floor must remain at most 3/16 and
its artifact hash must match; both repairs and every judge must be untruncated;
exactly five answers per item-arm and three judgments per primary answer must
exist. Any failure stops without a directional verdict.
