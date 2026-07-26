# Study 008 — Gate and Bar Surrogate Audit

**Task:** S8-T-004
**Pre-registration:** `experiments/study_008/pre_registration.md`
**Status:** LOCKED before Gate 1

The standing question is: **Can this check pass while the property it claims to
certify is false?**

## Gate 1 — Corrected re-derivation

**Certified property:** whether Study 007's episode-rendered similarity policy
can deliver at least one complete rubric-critical fact from every domain under
the swept `B_ltm` and `k_min`.

**Residual false-pass path:** a required string can occur in a semantically
unrelated passage. This is limited by multi-term rows and verbatim source
extraction but is not impossible.

**Disposition:** accepted. The harness records matched fact IDs and source
turns, not only a Boolean, so every hit remains auditable. This gate certifies
delivery, not comprehension or answer use.

## Gate 2 — Four-arm replay

### Arm A byte fidelity

**Certified property:** the replay harness reconstructs Study 007's actual
probe selection and rendering.

**Residual false-pass path:** two wrong internal paths could theoretically
produce identical final bytes.

**Disposition:** accepted. Final delivered bytes are the relevant interface;
candidate IDs, phases, source turns, and content hashes are also recorded to
make compensating errors visible.

### Fact-aware four-domain proceed condition

**Certified property:** at least one planned arm can deliver a complete locked
fact from every domain at both probes from the preserved store.

**Residual false-pass path:** replay may pass while the live store diverges.

**Disposition:** accepted only as a spend gate. Per-arm replay blocks are
committed as predictions and live byte fidelity is checked before bar
interpretation. A divergence voids interpretation until diagnosed.

### `c_fill` calibration

**Certified property:** the smallest cap prevents a single topic from taking all
fill selections while remaining jointly compatible with Gate 3.

**Residual false-pass path:** a cap can prevent total capture but still produce
an unhelpful allocation or bind differently on live data.

**Disposition:** accepted. Full per-topic allocations and cap-binding events are
recorded; fact-aware coverage and Gate 3 are separate required checks.

## Gate 3 — Targeted fixture

### Majority of delivered characters

**Certified property:** a targeted query retains a majority of delivered LTM
characters from its queried domain.

**Residual false-pass path:** those characters may be irrelevant overview text.

**Disposition:** fixed by requiring the arm's top-ranked own-domain item in
addition to the majority measure. This still certifies delivery economics, not
answer correctness.

### Top own-domain item present

**Certified property:** the policy does not eject its own best candidate.

**Residual false-pass path:** the ranking surrogate itself can choose a poor
item.

**Disposition:** accepted and reported separately for similarity and density
arms. P5 directly audits density picks against known fact locations offline.

### Character-cost bound with packing slack

**Certified property:** diversity's targeted-domain cost does not exceed
other-domain floor spend plus less than one admissible record of bin-packing
slack.

**Residual false-pass path:** the bound can pass while a small but decisive fact
is displaced.

**Disposition:** accepted. The bound certifies resource cost only; rubric
non-regression remains Bar 2.

## Bar 0 — Arm A reproduction

**Certified property:** the baseline is anchored to accepted Study 007 behavior.

**Residual false-pass path:** probe blocks and scores can reproduce while
earlier hidden state differs.

**Disposition:** reduced by full launcher guards, prefix hashes, run headers,
and candidate/log comparisons. Exact probe bytes and score reproduction are the
binding interface.

## Bar 1 — Breadth recovery

**Certified property:** an arm both receives complete facts from all four
domains and recalls broadly enough to meet the locked Q11/Q14 thresholds.

**Residual false-pass path:** the model can answer from prior knowledge even
when it ignores the delivered facts.

**Disposition:** reduced by the 17-item in-block/in-answer matrix and invention
tracking. The bar establishes paired evidence in one script and seed, not
population-level causality.

**Attribution clause:** factorial contrasts can identify the observed paired
main effects and interaction, but with `n = 1` they cannot establish a
statistically general effect. Reports must use that limited language.

## Bar 2 — Targeted recall

**Certified property:** no arm has a material targeted regression relative to
Arm A and both factor contrasts are quantified.

**Residual false-pass path:** losses of 0.5 or less can accumulate, and the
pre-registered Q5 loss can mask a qualitatively important trade.

**Disposition:** accepted as the explicit tolerance. Every per-question and
per-category value is reported, with Q5 isolated and strict-score sensitivity
shown.

## Bar 3 — Formation non-regression

**Certified property:** every arm forms at least one complete fact in all four
domains with offset-verbatim fidelity, no non-content records, and no inference
calls during formation.

**Residual false-pass path:** many individual facts may remain unformed even
when all four domains count as formed.

**Disposition:** accepted because this bar certifies domain-level formation
non-regression, not complete fact formation. The full fact inventory and the six
known unformed plants are reported as observational limits.

## Audit verdict

No gate or bar relies on topic presence as a surrogate for fact delivery. The
remaining gaps are either paired with an independent check or explicitly bound
to the narrower property the check can actually certify.
