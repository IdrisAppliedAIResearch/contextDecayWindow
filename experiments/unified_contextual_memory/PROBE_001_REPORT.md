# What the small aggregate gain hides

Post-result diagnosis authorized by the user; plan68b67758, exact replay5b7b03d0, raw diagnostic artifacts a1e8d8a2. No new embeddings, answers or judgments; no scores changed. All566 primary C1 selections reproduce exactly and finite-queue assertions pass.

## Earlier chronology findings and this comparison

The chronology-only probe held selected evidence fixed and improved5/12→8/12 before answers, with no losses. The later uncapped-plus-anchor E run reached106/128 before and32/32 latest, with all required evidence delivered; it still had22 complete-evidence reader errors. Removing post-review records then yielded126/128 before across two sequential diagnostic batches. That final improvement tested an explicit, correctly identified temporal boundary as well as reducing later competing evidence. It was not a chronology-only result. Sources: [chronology](../probes/temporal_da_fusion/CHRONOLOGY_REPORT.md), [full E](../probes/temporal_da_fusion/FULL_E_REPORT.md), [prefix](../probes/temporal_da_fusion/PREFIX_106_REPORT.md).

LoCoMo C0 and C1 already share chronology. C0 is67.84%; C1 is70.49% on the566 scored subset. These questions include list completion, indirect references and natural date interpretation without the synthetic review-anchor instrument. Absolute performance across the corpora is not a controlled test of chronology. Median full-population prompt size increased7,554.5→13,820.5 tokens; the modest marginal gain does justify questioning the additions' value.

## The continuation rule is restrictive

There are49 annotated-incomplete C1 questions. The frozen source mapping identifies56 missing pair carriers across46 of them. Four questions contain a malformed or absent evidence ID (`D10:19`, `D9:1 D4:4 D4:6`, `D:11:26`, or `D`); three have no missing carrier to diagnose. The old availability counts remain unchanged; this is a measurement limitation, not a label repair.

Of those56 missing carriers, **52 have an eligible reference/support edge from the final selected frontier, but its multiplied activation is below.48**. Four have no qualifying edge from that frontier. Both independent and contextual query scores miss their respective seed thresholds. Products on the52 eligible edges range.2894–.4617, median.3635. These are local blocking conditions under the frozen policy, not a run of an alternative rule or proof those annotations are necessary.

The arithmetic imposes a strong additional requirement: a seed at.55 needs a first edge >=.873; a seed at.60 needs >=.80; a seed at.70 needs >=.686. The independently calibrated reference threshold is only.528. Thus a connection can be strong enough under its own calibration but still unable to continue. Direct cosine.48 and a product of different cosine relationships do not share a demonstrated calibration scale.

Example: for “What kind of writing does Tim do?”, the missing forum record has direct.4477/contextual.4650. A selected reference sentence about a fantasy literature forum connects at.6595, but parent.7001×edge.6595=.4617, below the floor. The answer lists articles and a novel, omitting the forum activity. Another missing record naming The Witcher3 has a qualifying connection.6518×parent.7018=.4574. These are relevant-looking misses, but not a blanket case for admitting every qualifying edge.

An opposing example: the best eligible cue for the missing cakes record is merely “John: Hey Maria, that's awesome!” Similarity passing a threshold does not establish a meaningful antecedent relationship. The first unlimited-link version's near-full-corpus closure remains a real failure and cannot be ignored.

## Most added records come from contextual seeding

Across566 questions, the treatment adds26,851 record admissions beyond direct retrieval. Of these22,674 (84.4%) are contextual seeds beyond direct retrieval;4,177 enter only through traversal. These are query-record admissions, not unique corpus records or causal effect attribution. Traversal adds something on421/566 questions but its median exclusive addition is3 records; median contextual seeds82 and total selected128, versus median direct71.5. The implementation mostly broadens initial semantic access; the continuation mechanism has a smaller role in delivered additions.

## Reader and scorer failures both appear

All27 gains and12 losses are preserved with question/gold/answers in `artifacts/probe001/answer_changes.jsonl.gz`. Direct source retention is exact, so losses do not arise from removing a C0-selected record. Examples consistent with failed enumeration in the larger context:

- Tim's fantasy movies: C0 gives Star Wars, Lord of the Rings and Harry Potter; C1 gives only Star Wars.
- Where Maria made friends: C0 gives the shelter, gym and church; C1 gives only the shelter.
- Dave's creativity: C0 gives immersing himself in something he loves; C1 abstains.

These are observed answer changes, not established attention mechanisms or a measured noise-free effect of input size. One seed per unique prompt does not characterize reader variance.

There are also concrete judge problems in both directions. Boot camp: “Last month (relative to4 May,2023)” is accepted, while “Last month (relative to May4,2023)” is rejected with an internally inconsistent rationale. Another loss rejects an answer containing all requested school levels and four years because it additionally says “Local league.” Conversely, a gain credits one meal, “Grilled chicken and veggie stir-fry,” against a six-item reference list; other enumeration answers are rejected for omissions. The scoring specification does not define a task-specific list-completeness rule. These concerns warrant a separate additive, bidirectional scoring audit before treating a15-answer margin as precise. The current locked results are not rescored here, and the audit cannot be limited to favorable corrections.

## Implication for the next discussion

Chronology remains a plausible presentation foundation, with the earlier controlled support intact. The current additions show broad contextual seeding, a restrictive uncalibrated product floor, generic reference cues, mixed enumeration behavior and noisy scoring. The +2.65pp headline alone conceals these distinctions.

Before another long reader run, the useful next work is to define consistent list/date scoring and inspect the52 blocked carriers alongside irrelevant qualifying links. A continuation rule should be assessed on that tradeoff, rather than merely lowering the floor until annotations are recovered. No alternative threshold, policy, new inference or adoption is selected by this diagnostic.
