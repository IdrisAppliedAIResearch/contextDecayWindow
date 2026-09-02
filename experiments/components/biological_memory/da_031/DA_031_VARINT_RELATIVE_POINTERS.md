# DA-031 Self-Delimiting Varint Relative Pointers

**Status:** `COMPLETE; PARTIAL_VARINT_RELATIVE_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-030 result commit `7d09b919`
**Standing:** evidence-blind structural-capacity study on spent NF-004 and LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can a self-delimiting exact pointer code preserve enough capacity through the
full strongest-order sequence to recover dependencies that base-36 pointers
still reach too late?

DA-028 saves median 591/556 characters but NF remains dominated descriptively
by arrival consumption. DA-030 confirms alternate members fit earlier but not
after the protected suffix. The next safe lever is coordinate overhead.

## 2. Locked Control

Use all 1,098 NF and 465 LongMem questions at 16,000 characters. Freeze every
DA-028 decoded identity/order, direct/baseline/additive traversal and member
policy. Control delivery is 977/208; ceilings are 986/250.

The control codec is each row's exact DA-028 selection. The treatment candidate
is the fixed varint relative codec below. Select treatment only when its exact
immutable charge is strictly lower; ties/expansion retain DA-028 bytes.

## 3. Varint Codec

Encode positive backward distance, nonnegative start and positive length as
three concatenated unsigned little-endian base-32 varints. Each character
carries a five-bit digit. Terminal digits use
`ABCDEFGHIJKLMNOPQRSTUVWXYZ234567`; continuation digits use the disjoint
alphabet `abcdefghijklmnopqrstuvwxyz0189-_` at matching indices. A parser reads
until a terminal character and repeats exactly three times.

Reference text is `{prefix}v{distance}{start}{length}{prefix}`. Prefix selection
extends DA-028's collision rule until `prefix+r`, `prefix+q` and `prefix+v` are
absent from all candidate text. Integers are canonical: no redundant high zero
group. Distance must be `[1, history_size]`; length is positive and the decoded
absolute source span must be in bounds.

Greedy matching remains longest span, then lowest absolute member/start. Emit a
reference only when its complete textual code is shorter than the literal.

## 4. Immutable Allocation

1. Encode and byte-decode the complete DA-028 payload sequence with varints.
2. Select varint only on strict exact savings; otherwise retain DA-028 and make
   no new admission.
3. On varint rows, traverse DA-023 remaining skipped carriers in their frozen
   order, attempting full carrier then frozen member exactly as DA-028.
4. Admit only on exact fit and continue after overflow. Do not include DA-030
   alternate-member completion in this primary representation test.

No evidence, answer, outcome, question/type, similarity, fitted feature or
sweep enters codec selection or allocation.

## 5. Blind Gates

Require exhaustive varint boundary/canonical/malformed/forward/out-of-bounds
tests; exact decode; immutable identity/order on all 1,563 rows; selected charge
<= DA-028 question-wise; positive fallback rows if any exist; positive strict
savings and pair/member/overflow actions in both corpora; median selected
savings >=64; <=16,000 final; byte-identical replay; zero calls.

The fallback-row requirement is conditional: absence of fallback is permitted
only if varint is strictly shorter on every row. Stop unopened on mutation,
expansion, undercharge, nondeterminism or incomplete population.

## 6. Outcomes and Disposition

Report exact delivery against DA-028, groups, codec cells, DA-029 blocker
rescues, decisive costs/positions and ceiling gap.

Report `VARINT_RELATIVE_DELIVERY_SIGNAL` if NF gains >=2 and LongMem gains >=5,
both lose zero and every group is nonnegative. Report
`PARTIAL_VARINT_RELATIVE_SIGNAL` if either corpus gains >=2 with zero losses and
all groups nonnegative. Otherwise report `NO_VARINT_RELATIVE_DELIVERY_SIGNAL`.
Any DA-028 loss is a causal stop.

Spent availability is not reader use. No runtime, transfer or adoption claim.
Do not tune alphabets, radix, endianness, traversal, fallback or budget.
