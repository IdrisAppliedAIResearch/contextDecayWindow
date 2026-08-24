# TC-009 syntactic-span retrieval probe

**Type:** descriptive feasibility diagnostic; not TC-010  
**Status:** design lock before implementation  
**Date:** 2026-08-23  
**Parent:** TC-009 and its safe-substitution probe

## 1. Question and claim boundary

Test whether ranking whole adjacent-turn pairs by their most query-similar noun
phrase or subject-bearing sentence provides positive 32k evidence-delivery
feedback over whole-pair cosine.

This does **not** test recovering nouns or subjects from the existing pooled
1,024-dimensional vectors. That is not identifiable because the stored vector
has no token axis. It tests a two-stage candidate signal: a fixed dependency
parser exposes spans from raw text, then the carried embedding model scores
those spans. A positive result would justify designing a new study; it would
not select or ship this route. A negative result closes only these two frozen
span definitions on used LoCoMo development data.

## 2. Label-blind exploration

Executed before this lock on the committed TC-009 blind manifest with spaCy
3.8.14 and installed `en_core_web_sm`, NER/lemmatizer/textcat disabled:

- 1,365 adjacent-turn pairs;
- 20,145 noun-chunk occurrences, 4,935 unique; median 14 and maximum 42 per
  pair; one pair has none;
- 5,516 subject-bearing sentence occurrences, 5,385 unique; median 4 and
  maximum 11 per pair; 38 pairs have none;
- 10,320 unique texts across both arms.

Thus both nonempty and fallback states exist. The parser is a trained,
non-generative component and its calls must be reported separately.

## 3. Frozen arms

All arms rank the same complete pair candidates and pack the same serialized
pair elements with TC-009's full-budget dense packer at exactly 32,000
characters. Only the ranking score changes.

- `A_DENSE`: accepted TC-009 whole-pair cosine, replayed by identity.
- `A_NOUN_MAX`: spaCy `Doc.noun_chunks`; candidate score is the maximum cosine
  between the query and a nonempty stripped noun-chunk text. If none exists,
  use whole-pair cosine.
- `A_SUBJECT_SENTENCE_MAX`: candidate spans are stripped sentences containing
  at least one token whose dependency is `nsubj`, `nsubjpass`, or `csubj`;
  candidate score is maximum query cosine across them. If none exists, use
  whole-pair cosine.

Cosines use normalized committed Qwen3-Embedding-0.6B-Q8 vectors. Ties use
`(session_order, pair_order, candidate_identity)`. There is no span packing,
coefficient, score fusion, threshold, parser alternative, lexical fallback,
arm combination or parameter sweep.

## 4. Population and endpoints

Run all 871 unique LoCoMo development questions. Formal descriptive reads use
the 868 eligible questions and the frozen `targeted` (704) and `breadth` (44)
populations. For each treatment versus dense, report paired:

- combined, targeted and breadth complete-evidence gains/losses;
- breadth required-identity gains/losses and net identities;
- all four conversation-level combined complete nets;
- evidence-candidate dense and treatment ranks; and
- parser fallback and selected-span distributions.

## 5. Frozen positive-feedback rule

A treatment is `DESCRIPTIVE_POSITIVE_SIGNAL` only if all hold:

1. combined complete-evidence gains exceed losses;
2. targeted complete-evidence gains are at least losses;
3. breadth required-identity net is positive;
4. breadth complete-evidence gains are at least losses; and
5. every conversation's combined complete net is nonnegative, with at least
   two conversations positive.

If neither arm passes, disposition is `NO_POSITIVE_SIGNAL`. If one or both
pass, name them under `DESCRIPTIVE_POSITIVE_SIGNAL`. No p-value, optimization,
architecture selection or reader authorization follows.

## 6. Preflight — before label join

Part 1 must re-run and record the extraction distributions in §2, parser/model
package identities, unique span-text hash and fallback examples before any
evidence import.

- **PF1:** hash/count corpus, blind manifest, accepted TC-009 selections,
  parser package/model, embedding model, captured span cache and labels.
- **PF2:** planted traces prove noun chunks and subject-bearing sentences match
  their names; the selector scores spans but packs complete pairs.
- **PF3:** span extraction/vector capture and selection bytes close before the
  evidence module or per-question labels can import; planted early access fails.
- **PF4:** synthetic paired rows demonstrate every rule clause and both
  dispositions reachable.
- **PF5:** question content hashes and pair content identities only.
- **PF6:** `A_DENSE` reproduces all 871 accepted TC-009 32k selected-id and
  payload digests.
- **PF7:** not applicable; no feedback state.
- **PF8:** four conversations can expose reversal but not new-corpus transfer.
- **PF9:** parser accuracy, max-over-many-span bias and evidence availability
  can all pass without reader value; report span counts and fallback rates.
- **PF10:** availability only; reader work requires separate registration.

Capture may call the embedding model once per unique span text through fixed
batched execution. The outcome phase must use the sealed read-only cache with
zero cache misses, embedding calls and LLM/generative calls. Report parser
documents separately. Fixed seed is unnecessary because parser and embeddings
must replay byte-identically; use one thread and explicit UTF-8.

## 7. Execution order

1. Commit this design alone.
2. Implement extractor, cache capture, replay, measurement and tests.
3. Commit captured span/vector artifacts and passing PF1-PF10 before labels.
4. Run the frozen outcome, report, update memory/README/AGENTS if material, and
   open a stacked diagnostic PR. Do not create TC-010 or reader answers.
