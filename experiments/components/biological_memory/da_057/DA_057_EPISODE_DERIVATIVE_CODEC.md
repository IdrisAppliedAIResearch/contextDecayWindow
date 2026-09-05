# DA-057 Episode-Local Derivative Codec

**Status:** `COMPLETE; NO_EPISODE_DERIVATIVE_CAPACITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-056 result commit `e050aa22`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can oversized assistant evidence be represented as exact derivative context
linked to its immediately preceding user premise, rather than as an independent
large member?

## Blind Codec

Apply the frozen DA-031 self-delimiting varint backward-span algorithm to every
accepted episode in the DA-055 directory. Keep the user member literal. Encode
the assistant member with the user text as its sole prior history member. Use
DA-031's exact prefix selection, four-character match index, longest-match and
source-position tie break, and reference-only-when-shorter rule unchanged.

Render one canonical episode frame containing `User: <literal>` followed by
`Assistant: <encoded>`. Compare it with the exact literal episode frame and
select the shorter; ties choose literal. This shortest-exact choice reads only
source text and rendered cost. It reads no question, answer flag, evidence,
score, similarity, feature, outcome, or model output.

## Gates

Seal all 106,412 episode decisions before residual evidence. Require exact
decode to the original user/assistant pair, canonical varints, no forward or
cross-episode reference, deterministic shortest choice, byte-identical replay,
positive coded and literal selections, and zero model/embedding/cache calls.

## Residual Audit

After sealing, replace only DA-056 overflow materialization with its selected
exact episode frame; all prior payload and retained frames stay immutable.
Report fit under 2,048, gains/losses, retained slots and peak capacity over
DA-056=459. `EPISODE_DERIVATIVE_CAPACITY_SIGNAL` requires >=3 gains, zero losses,
all types nonnegative, exact decode, and cap compliance.

Reader interpretation of coded references, head selection, stopping, runtime,
fresh transfer, and adoption remain untested.

## Result

The blind codec selects coded form for 104,084/106,412 episodes and saves 14.4M
characters corpus-wide, but none of six residual frames fits 2,048. Their
selected costs remain 2,589-3,399 with savings of only 29-286. Availability
stays 459. Premise backreferences close; exact chunk chaining is next.
