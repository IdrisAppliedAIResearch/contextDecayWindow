# Amendment TC009-DEPGRAPH-001 — subject-overlap exploration count

**Date:** 2026-08-23  
**Applies to:** `TC_009_DEPENDENCY_GRAPH_PROBE.md`  
**Timing:** after implementation, during PF2; before any evidence-label join or
outcome inspection

## Trigger and evidence

The design's label-blind exploration states that 871/871 questions have at
least one candidate with exact grammatical-subject-lemma overlap. The frozen
implementation's full Preflight replay measured 870/871.

The sole zero-overlap blind case is key
`1dbe34f513c5bb7ae016c7416388fe6389f38187b062f27497851021ab8ab507`
(`conv-47`, source index 45). Its content lemmas are `bar`, `beer`, `kind`,
`mcgee`, and `serve`; none intersects the conversation's 191 parsed subject
lemmas. This was found from the sealed blind manifest and graph map. No evidence
identity, answer, population label, or outcome was read.

The failed Preflight otherwise reproduced 871/871 accepted dense selected-id
and payload digests, converged on 1,365 standard and 204,409 personalized real
graphs, and reported zero embedding-vector reads, embedding calls, or LLM calls.

## Change

PF2's expected count for questions with any exact subject-lemma-overlap
candidate changes from 871 to 870. The zero-overlap question remains in every
arm and receives the registered zero subject score where applicable.

## Rationale

This corrects a label-blind exploration count so the check tests the frozen
mechanism that was actually specified. It does not add a route, fallback,
parameter, or eligible observation, and it makes no outcome criterion easier.
The mismatch cannot be silently reconciled because the locked design is the
integrity anchor.

## Exclusions

No algorithm, parser configuration, graph definition, arm, budget, tie break,
population, endpoint, success clause, or claim boundary changes. In particular,
`A_SUBJECT_OVERLAP` and `A_SUBJECT_PPR` do not receive a lexical or dense
fallback.

## Authorization

The user authorized the lightweight syntactic-dependency and graph-theory
probes end to end. This amendment is the minimum pre-outcome correction needed
to execute that authorized diagnostic without altering its hypothesis.
