# DA-043 Dependency Dereference Burden Audit

**Status:** `COMPLETE; SHALLOW_SINGLETON_DEREFERENCE`
**Date:** August 30, 2026
**Parent:** DA-042 result commit `4873abd5`
**Standing:** spent evidence-aware causal accounting only
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

What traversal depth and transient payload burden would be required to turn
DA-042's complete graph addressability into actual source-member access for the
18 residual dependency sets?

DA-042 proves every residual is somewhere behind the control-plane head, but
does not show whether sequential dereference is shallow, whether conjunctions
require multiple nodes, or whether fetched nodes are themselves too large.

## 2. Locked Inputs

Use DA-042's sealed blind envelopes and DA-039's exact residual identities.
Reproduce 18/18 resolver reachability. Do not alter the frontier, order, prompt,
head, payload or budget.

## 3. Measurements

For each residual, resolve every remaining identity to its exact frontier
ordinal and source member. Record:

- number of required frontier nodes;
- first and last required ordinal, one-based;
- sequential nodes visited through the last requirement;
- raw source text characters and role-rendered characters per requirement;
- whether each single fetched node is <=256, <=512, <=1,024 and <=2,048 chars.

Report ordinal and payload distributions, depth bands `1`, `2-8`, `9-32`,
`33-128`, `>128`, and conjunction count. Do not fit a policy or threshold.

## 4. Gates and Boundary

Require exact hashes and joins, 18-item cardinality, unique identity-to-node
resolution, complete required coverage, byte-identical replay and zero calls.

Diagnostic only. A successor may add deterministic paging or structural skip
links in the control plane, but may not use evidence labels, scores or prompt
substitution. Reader/tool use and delivery remain untested.
