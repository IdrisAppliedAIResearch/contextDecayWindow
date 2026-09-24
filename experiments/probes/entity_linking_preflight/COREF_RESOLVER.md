# Track C — Trained entity resolver (minimal honest mechanism)

**Status:** EXPLORATORY. Not a study; no pre-registration; no adoption; LoCoMo not used.
**Date:** 2026-09-24. **Branch:** feat/bert-memory-store.

## Claim under test (narrow)
A BERT cross-encoder fine-tuned on planted synthetic role chains can resolve an
anaphoric alias ("the founder", "the CEO") to the correct named entity using only
the bridging context, and it generalises to entity **names never seen in training**.
This is a real trained mechanism, not the lookup oracle used in Track B.

## Task (schema learning, name generalisation)
- context: one bridging sentence, e.g. "Elena founded the company in 2004."
- pair A = context, pair B = `"the founder is Elena."` (BERT sequence pair)
- label 1 iff the named candidate is the entity the bridge makes the queried role.
- distractor = an entity the bridge ties to a *different* role.
- resolve: score gold + distractor, argmax == gold?

Trained on TRAIN names; evaluated on disjoint TEST names (closed 6-role schema:
founder/CEO/organizer/chair/captain/designer).

## Result (`resolver_result.json`, seed 42, 1500 train / 400 test docs, 3 ep)
| measure | value |
|---|---|
| held-out-name resolve accuracy | **1.000** |
| random-candidate baseline | 0.472 |
| **negative control** (bridges shuffled off answers) | **0.463 ≈ chance** |
| lexical (name-in-alias) shortcut | 0.000 |
| train loss | 0.70 → 0.003 |

The negative control collapsing to chance shows the metric is **not a surrogate**:
accuracy depends on the bridge actually supporting the answer (AGENTS.md §3).
Lexical shortcut 0.000 shows linking is not a substring match.

## Instrument failure found and fixed (§9.2 discipline)
Two earlier runs stuck at loss 0.696 with *train* resolve < 0.5 fit nothing, even
overfitting 120 docs. Cause: `pair_text` returns a tuple and it was passed to
`tokenizer(texts)` as single texts — a malformed shape the fast tokenizer treats as
pre-tokenized. Fix: `encode()` splits `(A,B)` into two lists → `tok(A,B)`. This was
an instrument bug, not a mechanism result.

## What this does NOT claim
- Aliases are a **closed 6-role template schema**; open-world appositional aliases
  ("Apple, the iPhone maker, …") are untested.
- Perfect accuracy partly means the task is **easy**: it demonstrates *learned*
  role→entity linking + name generalisation, **not** real-world coreference.
- Trained/evaluated on our synthetic template. Domain generalisation untested.

## Artifacts
- `coref_resolver.py`, `resolver_result.json`, `resolver_model/`
- Track A `train_typing.py` (test F1 0.854); Track B `synthetic_corpus.py` /
  `synthetic_corpus.json` (dense miss 1.000, lexical bridge 0.083 → ~92% headroom).

## Next
Wire this trained resolver into Track B in place of the gold oracle to measure
headroom recovered (needs the project venv for the pinned embedder). Real-data
test needs OntoNotes (gated: `ontonotes/ontology_coref`, `ontonotes/conll2012`)
behind a user `HF_TOKEN`.
