# Amendment 006: Tier 5 Comparison Scope

**Date:** 2026-07-28  
**Status:** Binding before Tier 5 implementation or registered execution  
**Applies to:** T5.4 only  
**Supersedes:** The "same 48 holdout queries" sentence in Amendment 005 only

## Trigger

Amendment 005 requires invalid topic/rule axes to be reported
`NOT_EVALUABLE`, while its T5.4 section also says every evaluable partition arm
is compared over the same 48 holdout queries. These requirements conflict when
an axis is valid on one primary corpus and invalid on the other. Filling the
invalid corpus with base recency, dropping the arm, or imputing results would
silently approximate an invalid axis, which the locked protocol forbids.

This conflict was identified before Tier 5 mechanism code or registered
execution.

## Change

The base recency arm is compared with each fixed graph depth over all 48
holdout queries from both primary corpora.

Each orthogonal-axis mitigation arm is compared only on corpus-query cells
where every axis required by that arm is valid. The graph comparator is
restricted to those exact same corpus-query cells. With the validated source
state, the topic, pinned-rule, and combined arms are therefore compared on the
24 `c121_l` holdout queries; their `c1000_l` cells remain
`NOT_EVALUABLE` and are neither replaced nor imputed.

Every comparison records its corpus IDs and query count. The three-axis
dominance rule from Amendment 005 is unchanged.

## Rationale

This preserves matched comparisons without pretending a known-invalid
mechanism ran. It is stricter than substituting base recency on Study 010 and
keeps the negative axis-validation result visible.

## Exclusions

No metric, threshold, query, graph comparator, partition policy, or validity
gate changes. This amendment does not permit cross-corpus pooling with missing
cells.

## Authorization

The repository owner authorized end-to-end execution and amendments on
2026-07-28. This contradiction repair is committed before Tier 5
implementation or results.
