# Entity-linking / entity-organizer — mechanism probe, full-arc report

**Status:** `EXPLORATORY`. Not a registered study; no pre-registration; no bar registered; **no adoption**; nothing in the shipped read path changed.
**Dates:** 2026-09-23 → 2026-09-24. **Branch:** `feat/bert-memory-store`.
**Generative-inference calls:** zero for every benchmark result (synthetic training and probe scoring only). LitBank/resolver training used local `bert-base-uncased` fine-tunes; BEAM/LoCoMo headroom probes made no model call except the local product Qwen embedder recomputed on a sample.

## Why this probe exists

The program's read path ranks episodes by frozen `CC80` = dense cosine (Qwen
1024-d) + BM25. A candidate formation idea: tag/store entities so that an entity
mention bridges two passages that **neither dense cosine nor lexical overlap**
connects — i.e. follow coreference across a lexical gap ("England" … "her" …
"Great Britain") when rebuilding context. This probe asks two separable
questions and answers them separately.

1. **Can a trained mechanism do non-lexical entity linking at all?** (mechanism validity)
2. **Does that ability open headroom on real long-context memory benchmarks?** (utility on the target task)

The two have **opposite** answers, and collapsing them is the failure mode this
report exists to prevent.

## Question 1 — the mechanism is real (synthetic + real nominal coreference)

- **Track C (synthetic, `COREF_RESOLVER.md`):** a `bert-base` cross-encoder
  resolves an anaphoric alias ("the founder") to the correct entity from the
  bridging sentence, **generalising to entity names never seen in training**:
  held-out-name resolve **1.000** vs random-candidate **0.472**, and the
  **negative control (bridges shuffled off answers) = 0.463 ≈ chance** — the
  metric is context-driven, not a surrogate (AGENTS §3).
- **LitBank real cross-sentence (`litbank_result.json`):** trained on real gold
  coreference (multi-sentence chains), evaluated **document-disjoint**, resolving
  a non-head mention to its chain head among 5 candidate heads (chance **0.20**):

  | seed | all | **zero-overlap** | gold-not-nearest | NEG (context shuffled) |
  |---|---|---|---|---|
  | 7 | .467 | **.490** | .386 | .250 |
  | 11 | .561 | **.569** | .497 | .213 |

  **Zero-overlap** = the target and its gold answer share **no** surface token, so
  no lexical bridge exists; **gold-not-nearest** defeats a proximity/first-mention
  heuristic; **context-shuffled** negative control falls to ~chance, confirming the
  score is context-driven. → **the mechanism links real coreference beyond saliency
  and beyond lexical overlap.**

## Question 2 — no headroom on either real memory benchmark

- **LoCoMo (`ENTITY_LINKING_PREFLIGHT.md`, 2026-09-23).** The "entity as sole
  bridge" cell (a link that neither dense nor lexical reaches) is **.003 on gold
  multi-hop pairs vs .008 on 20,000 random pairs** — at or below base rate. 81% of
  gold multi-hop pairs already share a content word (lexical reaches them).
  `NO_NICHE_ON_LOCOMO`.
- **BEAM (`beam_headroom_result.json`, 2026-09-24).** Zero-API/zero-reader
  preliminary on the external corpus (sealed `source_chat_ids` = exact gold message
  ids, **measurement-only**). On 152 `multi_session_reasoning` questions (gold
  spans 2–8 sessions):
  - Tightened lexical probe, all 152: **entity-only-bridged miss = 2/850 gold
    (0.002)**, and both were `'How'` capitalisation artifacts, not names.
  - Dense baseline (the product `Qwen3-Embedding`, recomputed on a sample), 12
    convs: BM25@10 recall **.456**, dense@10 **.468**, missed-by-both **.418**; of
    those, gold with **no surface link at all** = **2/79**.
  - **Mechanism attribution (inspected every both-miss):** each is a distinct
    **sub-instance an aggregation question sums over** ("saved $50 at Koçtaş",
    "chose Sanja Matsuri over Tokyo Tower", "night bus saved how much") — **not an
    alias needing resolution.** The 42–59% both-miss is a **dense-semantic + 32k
    recall ceiling** (consistent with shipped ~48% CC80 accuracy), not a coreference
    gap. `knowledge_update` is unmeasurable (`source_chat_ids` null).

## Disposition

**The entity-organizer mechanism is validated on nominal coreference (synthetic
+ LitBank), but has ~zero headroom on both real long-context memory benchmarks
(LoCoMo, BEAM).** These are consistent, not contradictory: those benchmarks'
cross-session difficulty is **aggregation + semantic recall**, a different axis
from **coreference resolution**. "An entity organizer helps long-context memory"
therefore has **no demonstrated headroom on any real memory benchmark tested**,
even though the linking capability itself is real and passes every control.

## Three instrument failures caught and fixed (AGENTS §9.2)

Reporting these is the point — each would otherwise have produced a false result:

1. **knowref substring-blanking + whole-chain blanking** leaked the gold surface
   into the context; the initial 0.776 was a leak + saliency surrogate. Anonymised
   + saliency-balanced re-run (`knowref_debias.py`) collapsed to **0.501 = chance**.
2. **LitBank first negative control permuted the gold *label*, not the context** —
   so a model that ignored context scored identically (0.545 = 0.545, useless).
   Corrected to **context-shuffled**, which fires (falls to ~chance).
3. **BEAM first headroom probe counted capitalisation artifacts and generic tokens
   ('How', 'API') as entity bridges**, inflating headroom to 0.41; tightening to
   proper-noun-vs-content-word decomposition dropped it to 0.002, and dense
   inspection showed the residual is aggregation, not coreference.

## What is closed / not closed (§9.1)

- **Closed:** entity-as-sole-bridge formation as a retrieval lever **on LoCoMo and
  BEAM**; knowref as a non-lexical-linking test (it is saliency); universal-alias
  "entity organizer helps memory" as an **adoptable** idea on any benchmark tested.
- **Not closed / do not over-read:** the **capability** is real (LitBank). If a
  downstream task genuinely presents nominal-coreference retrieval that dense +
  BM25 miss, this mechanism is the right tool — but no such task has been shown in
  this program's corpora. `knowledge_update` headroom on BEAM would need manual
  evidence annotation to measure. BEAM was probed at user-message granularity
  (product embeds episode pairs): directional, not byte-identical.

## Artifacts (code + small results only; data/model/vectors are gitignored)

- LoCoMo preflight: `entity_linking_preflight.py`, `pf_entitylink2.json`, `ENTITY_LINKING_PREFLIGHT.md`
- Synthetic: `train_typing.py`, `synthetic_corpus.py`, `coref_resolver.py`, `end_to_end.py`, `*_result.json`
- Real coref: `knowref_coref.py`, `knowref_debias.py`, `litbank_crosssentence.py`, `*_result.json`
- BEAM headroom: `beam_headroom.py`, `beam_headroom2.py`, `beam_dense_headroom.py`, `beam_headroom_result.json`
- Reuse/regenerate: `data/` (knowref/LitBank/MMC parquet from the ungated `coref-data` HF collection) and `resolver_model/` are **not committed** (regenerable; see scripts).

## Next (if this thread is ever resumed)

Not recommended to build for the read path — no benchmark headroom. If a
coreference-heavy retrieval task ever appears, the LitBank trained resolver is the
proven primitive. The BEAM 42–59% both-miss, if pursued, points at **dense recall /
representation capacity**, not entity linking — a different and separately-registered
question.
