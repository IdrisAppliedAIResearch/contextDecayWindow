# DA-051 Grouped Dependency Residual Audit

**Status:** `COMPLETE; DISTRIBUTED_DEPENDENCY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-050 result commit `5bfd696e`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Do the residual multi-member misses require multiple dependency nodes, or are
their members co-located in one episode that the current atomic frame splits?

## Audit

Reproduce DA-050=332 exactly. For each remaining miss, map missing evidence
members to episode and session identities. Report exclusive topology:

- `ONE_MEMBER`: one missing member;
- `ONE_EPISODE_MULTI_MEMBER`: multiple members, one episode;
- `ONE_SESSION_MULTI_EPISODE`: multiple episodes, one session;
- `MULTI_SESSION`: required episodes span sessions.

For `ONE_EPISODE_MULTI_MEMBER`, render the exact episode as one canonical
DA-044-style frame (`User` then `Assistant`) and report fit under 2,048 chars.
For all classes report member, episode, and session counts by question type.

This is evidence-aware residual anatomy only. It changes no stream, order,
capacity, threshold, or outcome and makes zero model, embedding, or cache calls.

## Result

The 133 residuals split into 55 one-member, 2 one-episode multi-member, 6
one-session multi-episode, and 70 multi-session. Both grouped one-episode frames
overflow 2,048 chars, so grouping is closed. Distributed cases require 2/3/4/5
episodes in 47/18/8/3 questions. The next capacity primitive is a protected
retained set of at most five exact frames.
