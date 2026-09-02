# DA-064 Exact Occurrence-Coordinate Stream

**Status:** `COMPLETE; NO_OCCURRENCE_COORDINATE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-063 result commit `96789cfd`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can retaining exact posting occurrence coordinates replace session scanning with
direct episode jumps while preserving required-evidence reachability?

## Blind Stream

Begin with DA-062 `represented_episode_ids` in sealed order. Then tokenize the
query with DA-061's lowercase `[A-Za-z0-9]+` rule and preserve adjacent bigrams
in query order. For each bigram, append every episode containing that exact
adjacency in session and episode source order. Deduplicate episodes by first
appearance. Do not bridge episode boundaries.

Each stream item contains its DA-055 session head, episode order, episode id,
and two member coordinates. Expose one episode and one <=2,048-char DA-056
member frame at a time. A new item replaces the current item; the immutable
DA-038 payload and retained frames cannot change. No score, rerank, threshold,
fit, cap, fallback, or outcome-dependent stopping is permitted.

Seal all 465 streams before opening episode-level answer markers. Require
locked hashes, exact coordinate resolution, prefix identity, deterministic
replay, positive matched and unmatched bigrams, first-appearance deduplication,
zero protected-payload mutation, leakage-clean source, and zero model,
embedding, or cache calls.

After sealing, report complete/any required-episode reachability, first/last
required position, and episodes examined through completion. `OCCURRENCE_COORDINATE_SIGNAL`
requires complete reachability >=.90 and p50 last required position <=32.
Otherwise report `NO_OCCURRENCE_COORDINATE_SIGNAL`.

Reachability is not delivery. Reader recognition, stopping, overflow chunk
reconstruction, runtime, fresh transfer, and adoption remain untested.

## Result

Complete required-episode reachability is 382/465 (.822), below .90; any is
440/465. Among complete rows, last required position is p50 18.5/p90 71 and
additional episodes beyond the immutable prefix are p50 1/p90 49.9. Exact
coordinates reduce scanning when they hit but do not preserve enough evidence.
The next structural probe is fixed-radius local expansion around occurrences.
