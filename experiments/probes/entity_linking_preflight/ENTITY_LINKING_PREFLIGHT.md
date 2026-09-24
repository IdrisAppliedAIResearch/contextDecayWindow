# Entity-linking formation preflight — report

**Status:** `EXPLORATORY`; descriptive feasibility diagnostic; NOT a registered study
**Disposition:** `NO_NICHE_ON_LOCOMO` (instrument-valid null)
**Date:** 2026-09-23
**Substrate:** LoCoMo (`locomo10.json`, SHA-256 `79FA87E9…698FF4`) — development corpus, SPENT
**Store:** `experiments/comparisons/hh_003/artifacts/run/A_EPISODIC/conv-NN.db` (10 convs; committed episode embeddings, 1024×float32)
**Model calls:** zero (blob cosine + lexical/heuristic-entity features only; no embedding, no LLM)
**Script:** `entity_linking_preflight.py` (SHA-256 `A8D7BCD2…E69D`); **result:** `pf_entitylink2.json` (SHA-256 `3468CA55…FC1B`)

## Question

A proposed write-time organizer would tag each episode with entity labels so that
multi-hop questions could be answered by following a **cross-lexical entity link**
between two evidence turns that neither dense cosine nor lexical overlap reaches.
The preflight asks only whether **that job exists** on this corpus. If the two hops
of a multi-hop question are already reachable by dense or lexical, an entity label
adds nothing, and no fine-tune is warranted. Answering this costs no model calls:
cosine comes straight from the committed episode blobs.

## Method

Gold evidence **pairs** for multi-hop questions (LoCoMo category 3 with ≥2 evidence
`dia_id`s), mapped to store episodes by **content join** (the diarized turn text is a
substring of one episode's rendered text; ties broken to the nearest expected turn).
Join gate: `map_rate ≥ 0.90` required per conversation to be used. Three bridges
between a pair are computed, all **speaker-subtracted and DF-filtered** (a
term/entity appearing in >25% of a conversation's episodes is boilerplate and bridges
nothing — BM25's IDF logic):

- **dense** — partner is within cosine rank ≤ 5 of the source episode (greedy hop);
- **lexical** — pair shares ≥1 discriminative content token (what BM25 can bridge);
- **entity** — pair shares ≥1 discriminative non-speaker named entity (heuristic
  proper-noun spans; an NER package is not installed, so aliases/pronominals are
  under-linked — this is a **floor**, not a ceiling).

Controls: category 1 (single-hop, ≥2 evidence) as a structural control, and 20,000
random episode pairs as the base-rate population. The decisive statistic is
enrichment of the entity bridge on gold versus random, and specifically the **WIN**
cell — an entity bridge on a pair that **neither dense nor lexical reaches**.

## Result

Join gate passed on all 10 conversations (`map_rate` 0.995–1.000). 47 category-3
multi-evidence items → 328 pairs; category-1 control 276 items → 1,339 pairs; 20,000
random pairs.

| Population | pairs | cos med | rank med | dense≤5 | lexical | entity | **WIN** (entity only) | entity ∧ ¬dense |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CAT3 multi-hop | 328 | .622 | 67 | .098 | **.808** | .113 | **.003** | .082 |
| CAT1 control | 1,339 | .646 | 33 | .188 | .870 | .188 | .008 | .129 |
| NULL random | 20,000 | .557 | — | .017 | .614 | .083 | .008 | .079 |

1. **Multi-hop hops are not cross-lexical here.** 81% of gold category-3 pairs
   already share a discriminative content token (vs 61% random) — lexical retrieval
   reaches them. Only ~1.5% of gold pairs are cross-lexical by token-Jaccard < .05.
2. **Entity overlap is barely enriched** on gold over random: .113 vs .083 (×1.36).
3. **The niche is empty and not enriched.** The entity bridge on a pair that neither
   dense nor lexical reaches is **.003 on gold vs .008 on random** — gold at or below
   base rate. The single category-3 "hit" is a heuristic artifact (`Hey Sam`, a
   greeting, across conv-49 t13↔t179).
4. **Only survivor:** dense cannot *hop* between the two gold turns directly (median
   rank 67; dense≤5 fires on 9.8%), but that gap is covered by lexical, and both gold
   hops are individually question-retrievable, so no bridge is required for them.

## Interpretation

The specific thesis — *multi-hop hinges on a cross-lexical entity identity that
dense and lexical both miss* — is **false on LoCoMo as measured.** Multi-hop gold
turns are topically/lexically co-similar; their shared bridge is a rare content word
that BM25 already finds, not an entity surface alias. An entity-linking formation
signal would have ~nothing to add on top of the existing dense + lexical route here.

This is consistent with the surrounding graveyard: `TC-009` syntactic-span and
dependency-graph probes (`NO_POSITIVE_SIGNAL`), and `NF-003` fine-ranking (−37) —
structured-linguistic formation signals keep losing to dense + lexical on this
corpus. `DA-014` already places the reachable multi-hop ceiling in reversible
representation/packing **capacity**, not in missing links.

## What is closed, and what is not (§9.1)

**Closed:** write-time **cross-lexical entity-linking formation as a multi-hop
vehicle, on LoCoMo.** A supervised entity BERT is not built, because the job it would
perform is ~absent here.

**Not closed — do not over-read this null:**

- **Alias/coref under-detection.** The entity bridge uses a heuristic proper-noun
  matcher (no NER installed); it under-links aliases (`Mel` ≠ `Melanie`) and ignores
  pronominals/descriptions, so `entity` is a floor. A better entity resolver would
  raise entity-sharing — but on **both** gold and random pairs, and the WIN cell is
  entity ∧ ¬lexical (81% of gold pairs are already lexical), so aliasing is unlikely
  to open a gold-only niche. It cannot be excluded, only bounded.
- **Corpus choice.** LoCoMo is short person/dialogue turns with heavy topical
  repetition. "Dead on LoCoMo" is **not** "dead everywhere." A corpus with genuine
  long-range cross-lexical entity chains (e.g. a multi-session entity-tracking set)
  could carry the signal this one structurally lacks.
- **Sample size of the numerator.** The WIN cell is 1 pair (descriptive, not
  statistical). The `lexical=.808` and entity-enrichment figures are robust enough to
  say the niche is ~0 here.

## Instrument note (§9.2)

This is a **mechanism-relevant null, not an instrument failure.** The instrument
functioned: the content join mapped ≥99.5% of turns; controls (category-1) and a
20,000-pair random base-rate population were computed; the enrichment test was
applied; the degenerate first-pass entity signal (overlap = 1.0 everywhere because
speaker labels appear in every episode) was caught and fixed by speaker-subtraction
and DF-filtering. The mechanism's **precondition** — the existence of an unbridged
cross-lexical entity gap — was tested and found absent on this corpus.

The instrument that would test the surviving residual, if the thesis is to be revived
off this corpus: a **supervised coreference/alias resolver** (entity-level, not
proper-noun spans) run as the same WIN-vs-random enrichment test on a corpus that
contains cross-lexical entity chains. Nothing here authorizes building that for
LoCoMo.

## Integrity and boundary

Zero embedding calls, zero LLM calls, zero generative inference; all cosine from
committed episode blobs. Gold used for evaluation only (measurement, not mechanism).
LoCoMo is a spent development corpus: results are **descriptive**, no bar was
registered before the run (§9.3/§9.4 — no disposition is being rescued), and no
formation, reader, ranking or adoption claim is made. The vehicle is stopped on this
corpus; no fine-tune is warranted.
