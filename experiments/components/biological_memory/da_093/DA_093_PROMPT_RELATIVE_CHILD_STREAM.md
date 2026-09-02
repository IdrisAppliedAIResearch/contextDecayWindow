# DA-093 Prompt-Relative Exact Child Stream

**Status:** `COMPLETE; PROMPT_RELATIVE_CHILD_CAPACITY_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-091 result commit `2ee1d1ce`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can child nodes be streamed more compactly by exact backward references into the
immutable DA-078 prompt history, without changing payload identity or order?

## Frozen Population

Use the 3,499 DA-091 packet-stream rows: 2,701 `CHILD_PACKET_STREAM` and 798
`TYPED_EDGE_CHILD_PACKET_STREAM`. Reconstruct each question's exact DA-078
member history and sentinel. DA-078 and every noneligible DA-091 row remain
unchanged.

## Exact Encoding

Use DA-078's globally shortest sentinel-pointer language. Build its immutable
4-gram source index once per question, then compute the same deterministic
minimum-character parse independently for each child. References may point only
into DA-078 history, never another frontier child.

Serialize the encoded child canonically and split it into fixed 1,800-character
packets with a delimiter absent from the encoded stream. Reassemble before
decoding. Select encoded packets only when their cumulative charge is strictly
below DA-091 literal packets and peak charge does not increase; otherwise retain
DA-091 exactly. Ties retain literal.

## Gates And Disposition

Require exact source-byte decode, no expansion, unchanged target/order/edge,
3,499 exact joins, unchanged noneligible rows, zero DA-078 mutation,
byte-identical replay and zero calls.

Report `PROMPT_RELATIVE_CHILD_CAPACITY_SIGNAL` if at least 20% of eligible rows
select exact references and selected rows save at least 10% cumulative charge at
median. Otherwise report `NO_PROMPT_RELATIVE_CHILD_CAPACITY_SIGNAL`.

This is reversible representation capacity only. Reader decoding, retention,
stopping, delivery, runtime, fresh transfer and adoption remain untested.

## Result

All 3,499 eligible child streams selected the prompt-relative exact form. The
cumulative savings fraction is p10 13.73%, p50 22.50% and p90 35.05%, clearing
both registered bars. Selected streams use p50 two frames, p50 1,895 cumulative
characters and p50 1,816 peak characters.

Every encoded stream reassembled and decoded to the exact source child. All
4,556 noneligible DA-091 rows stayed fixed, DA-078 had zero mutations and replay
was byte-identical. There were zero model, embedding and cache calls.

This demonstrates that immutable prompt history is also a compression base for
linked evidence. It adds per-question exposure capacity without displacement,
but the reader burden depends on how many prior spans each child references.
