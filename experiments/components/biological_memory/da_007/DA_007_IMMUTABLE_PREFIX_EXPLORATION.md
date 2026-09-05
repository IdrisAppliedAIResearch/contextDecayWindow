# DA-007 Immutable Direct-Prefix Reserve Exploration

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 29, 2026
**Parent:** DA-006 stop commit `6e33510c`
**Standing:** descriptive representation diagnostic on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can compact temporal links repay prospectively reserved capacity when the
protected direct core is an immutable prefix of the actual 16k direct
selection?

DA-006 replayed the packer at a smaller budget and allowed skip-on-overflow to
reroute the core. DA-007 removes that ambiguity: it may only drop a suffix from
the already selected direct sequence. No new direct identity can enter.

This spent-corpus exploration cannot select a reserve, renderer, gate, reader,
production policy, or adoption decision.

## 2. Fixed Construction

Use DA-006's committed blind rows plus DA-002's sealed candidate character
costs, and the same eight arms: `PAIR` and `TURN` at reserves
`{256,512,1024,2048}`. Use no corpus, cache, embedder, or model in the blind
stage.

For each edge and reserve `R`:

1. start with DA-006's verified `DIRECT_16K` selected pair sequence;
2. repeatedly remove the final selected pair until retained characters are at
   most `16,000 - R`;
3. retain the remaining sequence byte-for-byte and in order;
4. render the already frozen DA-006 pair or selected-turn payload only when it
   fits `R` and its parent pair is absent from the retained prefix;
5. do not return unused reserve to the core.

Every core identity must be a prefix identity of `DIRECT_16K`. Every treatment
must remain within 16,000 characters.

## 3. Fixed Analysis

Seal all decisions before importing evidence. Reproduce 935/1,098 direct
complete items and the DA-004 edge population.

For every arm report complete edge actions, link-carried gains, suffix-caused
losses, net, admissions, conversation cells, character distributions, and
retained DA-004 neighbor/downstream benefits. Require every gain's missing
direct evidence to be in the linked dialogue payload and every loss's removed
evidence to be in the dropped suffix.

Compare `TURN` and `PAIR` at each reserve by exact complete-item discordance.
Report all arms without interpolation, slack return, multiple links, tuning, or
winner selection.

An arm is `PROTECTED_CAPACITY_SIGNAL` descriptively only if gains exceed losses,
all six conversations have nonnegative net, and causal accounting is exact.
Otherwise report `NO_PROTECTED_CAPACITY_SIGNAL`. This is not an adoption bar.

## 4. Preflight Part 1 - Exploration

**Behavioral identity.** Reservation drops only the tail of the selected direct
sequence. It cannot alter the identity or order of the retained core. New
evidence can enter only through the linked payload.

**Name-to-behavior.** Tests must establish suffix-only removal, maximal retained
prefix under the core budget, exact reserve fit, no slack return, already-core
rejection, unchanged DA-006 payload identity, total budget, and direct digest.

**Distribution.** Before labels report admissions, dropped suffix counts and
characters, unused reserve, pair/turn fit disagreement, and all conversations.

The primary surrogate risk is that a direct tail identity can carry evidence
despite being last in the selected sequence. Compact fit does not certify that
the reservation is worthwhile.

## 5. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify the DA-006 blind and DA-002 provenance SHAs, 26,100
  edges, eight arms, 1,104 questions, and six conversations.
- **PF2 Identity:** pass every behavior and degenerate test in Section 4.
- **PF3 Ordering:** commit protocol before implementation and blind artifact
  before evidence access.
- **PF4 Reachability:** require admissions, suffix removals, and pair-rejected/
  turn-admitted edges.
- **PF5 Keys:** preserve all question, seed, neighbor, pair, and dialogue keys.
- **PF6 Reproduction:** require direct digests and 935 complete after join.
- **PF7 Absorbing state:** not applicable; require byte-identical replay.
- **PF8 Length:** use every DA-006 edge and primary edge; no fresh transfer.
- **PF9 Surrogate audit:** suffix position is not evidence absence; availability
  is not reader use.
- **PF10 Live boundary:** selection requires fresh data and a locked multi-edge
  policy, reader, and adoption criteria.

## 6. Stops and Outputs

Stop on hash mismatch, non-prefix core, budget overflow, payload drift,
nondeterminism, direct-total mismatch, or causal-accounting failure. Commit
blind rows, result, and report; add no arm or interpretation after labels open.
