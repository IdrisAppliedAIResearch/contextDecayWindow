# Decision: Restore the Pure-STM Null Baseline

**Study:** 009
**Status:** EXECUTED under Amendment 001
**Registration anchor:** `37fff74`

## Finding

The program has not retained a clean STM-versus-LTM control. Study 004 is the
only study that compared pure STM with LTM, and pure STM won 11.0 to 7.0.
Studies 005 through 008 compared new LTM policies with earlier LTM policies.
Those controls measured iteration against a surrogate baseline, not whether
the LTM tier was useful at the registered 120-turn scale.

At this scale, distilled LTM is selected from the same raw episodic store that
STM's K retrieval searches. The preserved Study 002 result also shows that K
can surface middle-domain episodes at turn 115. LTM can therefore duplicate or
displace directly retrievable content without exercising its intended
store-growth and decay advantage.

## Decision

Study 009 restores pure STM as Arm S and compares it directly with the accepted
Study 007 LTM treatment, Arm L.

- If S is at least L on Q1-Q13, LTM is retired from 120-turn studies. Its
  remaining scale hypothesis transfers to Study 010.
- If S trails L by at least 1.0, retirement is cancelled and the delivered-fact
  mechanism is analyzed.
- If S trails by less than 1.0, the result is treated as judgment-call variance
  and LTM is retired at this scale with the margin disclosed.

Arm S is a separate composition. Its import closure contains N + K retrieval,
topic assignment, pinned rules, tagged STM blocks, observability, embeddings,
and inference. It does not import LTM, dreaming, promotion, or digest modules.

## Digest Rationale

Breadth probes ask for enumeration across canonical topics. Similarity
retrieval instead favors text near the query embedding, which has repeatedly
selected topical overviews rather than the required facts. The topic digest is
an always-on structural index: density-ranked, verbatim spans grouped by topic,
with exact serialized-cost accounting and no query classifier.

The proposed values are accepted for Gate 1 calibration:

- `d = 2`
- `B_digest = 2,500` characters
- placement after `<pinned_rules>` and before `<recent_context>`
- one-span-per-topic floor, with word-boundary truncation rather than omission

Gate 1 may lock the smallest sufficient registered values. If no tested setting
reaches fact-aware coverage for all four domains, S+D is dropped without
changing the criteria.

## Rejected Alternatives

- Fifth LTM retrieval iteration: it would continue optimizing an architecture
  before establishing that the tier beats pure STM.
- A full 2x2 with L+D: it doubles the scoring load for an interaction that only
  matters if L survives the null test.

## Rater Constraint

The original human-rater constraint was superseded by author-authorized
Amendment 001 before the full run and scoring. A blinded Codex agent score was
committed before the mapping or mechanism logs were opened.

## Outcome

Arm L scored 12.0/13.0 on Q1-Q13 and Arm S scored 10.5/13.0. S trails by 1.5,
meeting the registered evidence threshold. LTM retirement is cancelled,
Prediction P1 is refuted, and the Study 007 accepted treatment carries to
Study 010. The digest failed G1 and does not carry.
