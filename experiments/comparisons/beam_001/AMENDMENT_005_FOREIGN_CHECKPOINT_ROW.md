# BEAM-001 Amendment 005 - remove a foreign synthetic checkpoint row

**Date:** 2026-08-28  
**Timing:** After all normal-scale context arms completed, before finalization,
shuffled replay, outcome access, registration, or any generation call

## 1. Trigger

The eight-shard exploration completed every expected mechanism key but stopped
at finalization with `5401/5400` unique question-arm keys. A key-set audit
against the still-sealed mechanism surface found:

- 1,800 expected and 1,801 observed question keys;
- no missing expected question key;
- no unexpected arm name; and
- one foreign key, literal `q1`, appearing twice as identical synthetic A0
  rows in the base checkpoint.

The foreign rows have only `arm`, `question_key` and `value` fields. They are
not BEAM context records and do not match any canonical mechanism question.
Their duplicate identity explains one extra unique checkpoint key.

## 2. Frozen repair

Before resuming finalization, a dedicated repair command will:

1. derive the allowed question-key set from the sealed mechanism surface;
2. require exactly 1,800 allowed question keys and the three frozen arm names;
3. scan every base and shard checkpoint as JSONL;
4. reject malformed nonterminal rows and conflicting expected duplicates;
5. atomically remove only rows whose question key is outside the allowed set
   or whose arm is outside the frozen arm set;
6. require that the retained unique key set is exactly the 5,400 Cartesian
   question-arm population; and
7. write a repair artifact containing file hashes, removed row digests and
   counts, but no payload text.

For this observed trigger the command must remove exactly two physical rows,
one unique key, and zero expected rows. Any other result stops.

## 3. Unchanged boundaries

All computed BEAM contexts, payload digests, rankings, embeddings, parameters,
arms, selection behavior and gates remain unchanged. Outcomes remain sealed.
The repair makes zero embedding, generation or judge calls. Finalization and
the complete shuffled replay still run from the retained 5,400 records.
