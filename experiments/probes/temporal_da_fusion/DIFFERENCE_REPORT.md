# Why the fusion rescues and loses evidence

Exploratory follow-up, September 6, 2026. Plan **86a1d7c9**, implementation **8ca6c353**, exact-replay gate and blind ablations **daeeb2fc**. Existing exposed data, zero reader/embedding calls. Prior fusion result unchanged. No confirmatory or reader-success disposition.

**The rescues follow a good semantic seed forward to a later location statement. The losses are already high-ranked direct evidence pushed back by indiscriminate neighbor priority. Forward direction helps, but does not identify safe admissions.**

## Difference in the records

All six rescued sources are next-turn neighbors of semantic seeds at ranks 4–11. All six parents are selected. Five transitions change the location; Meadow-840 repeats warehouse at the next source turn. This matters: recovering a registered source id is not always adding a new answer value. The primary measure remains exact required source delivery; no earlier scores change.

| Case | Earlier statement → required next statement | Seed rank | Required direct rank | Position after link traversal |
|---|---|---:|---:|---:|
| Meadow-840 | warehouse → warehouse | 10 | 52 | 28 |
| Harbor-553 | annex → laboratory | 8 | 65 | 23 |
| Orchard-584 | studio → office | 11 | 41 | 28 |
| Harbor-967 | hangar → workshop | 8 | 44 | 22 |
| Riverside-978 | workshop → annex | 10 | 43 | 26 |
| Riverside-324 | office → annex | 4 | 64 | 12 |

The seven lost required sources had direct ranks **20–30**, median26. Their positions after traversal are **41–53**, median45. They were not low-ranked irrelevant tail material. Every lost source is also an effective location update before the anchor, just like the rescued sources. One lost source, Meadow-784, even has a forward link from turn48; its parent is too late in the expanded order to be delivered.

Traversal positions above are the DA permutation before the protected temporal prefix is prepended and duplicate/recent sources removed. They are not final packed ranks. Full source identities and actual selections are retained in the artifacts. No unique one-to-one causal exchange between a particular admitted neighbor and a lost source is claimed; packing depends on the whole ordered set.

## Do the available signals distinguish useful additions?

Across all128 before queries, the fusion adds1457 source occurrences: six registered required carriers and1451 other records. The latter are not necessarily useless or wrong; they simply are not required by the exact-source key. It removes1458 occurrences, seven required and1451 others.

| Feature | Six required additions | Other1451 additions |
|---|---:|---:|
| Median direct rank | 48 | 50 |
| Median CC80 score | .9023 | .9043 |
| Median cosine | .6851 | .6803 |
| Before anchor | 6/6 | 1413/1451 |
| Forward-linked | 6/6 | 726/1451 |

The scores overlap; none supplies an evident safe relevance cutoff. Before-anchor status admits almost all other additions too. Forward direction contains all six rescues but also hundreds of other admissions. This is descriptive evidence against these simple distinctions being sufficient, not a proof that no classifier or relational signal exists.

All13 gained/lost carriers lie10–12 turns before their anchors. Other additions have median distance40 turns before the anchor. That apparent temporal separation is not a deployable threshold: the generator deliberately makes the decisive update precede a run of intervening notes. Fitting that interval would exploit the exposed benchmark structure, the same problem the user raised about tuned character budgets.

## Structural checks beyond the13 cases

Three changes were fixed before this measurement. They modify only which links receive early priority, preserving the direct stream, temporal block, renderer and budget.

| Retrieval variant | Complete evidence /128 | Gains vs C1 | Losses vs C1 |
|---|---:|---:|---:|
| C1 baseline | 109 | — | — |
| Original bidirectional fusion | 108 | 6 | 7 |
| Forward links only | 110 | 7 | 6 |
| Backward links only | 99 | 0 | 10 |
| Only promote linked children before anchor | 108 | 6 | 7 |

Forward-only retains all six original rescues, repairs one original loss, and gains one additional question. On the115 questions outside the original discordances it gives one gain/no losses,102→103 complete; on the13 original discordances it gives six gains/six losses versus C1. This remainder was already exposed, so it is not a held-out test.

Backward-only retains none of the original rescues and adds three losses on the115-question remainder. Restricting child promotion to before the anchor reproduces the original availability pairs on all128 questions; this does not prove its selected contexts are identical or that future material can never hurt readers. The original semantic fallback still permits later records.

All variants preserve latest contexts exactly (32/32), while all32 absence contexts change. No inference was run, so absence safety and answer correctness are unknown. Forward-only's net+1 is not an established reader benefit or a selection recommendation.

## Recommendation

**Keep C1 as the working baseline and do not advance unconditional neighbor promotion to a reader run.** In this draft it exchanges high-ranked direct evidence for nearby material without deciding which material is necessary. Backward-only traversal has no demonstrated rescue here; continuing to tune symmetric neighborhood expansion on this corpus is not justified by these results.

Retain forward links as a candidate-generation idea. The substantive next design question is whether the successor changes, confirms or qualifies the same state referred to by the seed and query. The observed examples motivate that relationship; adjacency and cosine do not certify it. A design that recognizes such relationships would need to distinguish effective changes from proposals/future changes, and would need paraphrased or naturalistic examples before claiming generality. Merely parsing this generator's repeated sentence would not establish a general memory mechanism.

This probe has tested the cheap structural explanations and identified their limit. The actionable engineering decision is to preserve direct evidence until a link has an independently defensible admission reason. That is a design requirement, not an already validated new allocator. No new cutoff, budget sweep, state parser or automatic reader experiment was introduced.

## Verification and artifacts

`difference.py extract` reproduced all192 original baseline and fusion context digests and all192 unrestricted DA orders before generating ablations. Forward/backward/scope and two-session fixtures, full permutation checks, protected-prefix checks and serialized32k limits pass. Failed-gate fixture rejects measurement; gain/loss/empty-required fixtures pass. Hashes and full label-free outputs were committed at daeeb2fc before `difference.py measure` read labels. There is no persistent feedback; all140 records per history are traversed.

- `difference_artifacts/gate.json`: input hashes, runtime,192-case replay and structural checks.
- `difference_artifacts/blind.json`: ablation selections and outcome-free record features.
- `difference_artifacts/features_labeled.json`: added/removed records with source first sentences, scores, anchor distances and link parents.
- `difference_artifacts/outcomes.json`: every variant/question availability comparison.
- `difference_artifacts/result.json`: distributions and original-discordance/remainder comparisons.

Preflight interprets PF1–PF10 as specified in DIFFERENCE_PLAN.md: bounded full-history replay; no efficacy bars; stable frozen identities; exact reproduction; gated measurement; explicit surrogate and live-reader limits. The adapter calls only source-level traversal/packing; labels enter the separate measurement function. No source-selection policy consumes measurement features or outcomes.
