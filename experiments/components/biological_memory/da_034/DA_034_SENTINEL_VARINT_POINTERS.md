# DA-034 NF Sentinel-Only Varint Pointers

**Status:** `COMPLETE; NO_NF_SENTINEL_VARINT_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-032 audit commit `30418514`
**Standing:** evidence-blind NF-004 structural-capacity study
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can removing the per-reference opcode recover the roughly 100 characters needed
for NF's final three dependencies without changing any evidence identity/order?

DA-032 finds median postpack slack 9 versus required member cost 108. DA-031's
reference text pays an explicit `v` on every pointer. A sentinel absent from all
candidate text can delimit references without that opcode.

## 2. Locked Control

Use all 1,098 NF-004 questions at 16,000 characters. Freeze DA-031's decoded
payload identity/order, direct/baseline/additive traversal and member policy.
Control delivery is 983 and the one-hop ceiling is 986.

## 3. Sentinel Codec

Use DA-031's exact three concatenated self-delimiting base-32 varints unchanged.
Choose the shortest string consisting only of one or more `~` characters that
does not occur anywhere in any candidate member text for the question.

Encode a reference as `{sentinel}{distance}{start}{length}{sentinel}` with no
opcode. Because the sentinel is absent from literal source text and varint
alphabets contain no `~`, parsing is unambiguous. All canonical, backward,
positive and in-bounds rules remain DA-031-identical.

Compare the exact immutable sentinel charge with DA-031. Select sentinel only
when strictly shorter; ties/expansion retain DA-031 bytes and make no new
admission.

## 4. Immutable Allocation

On sentinel-selected rows, encode/decode the complete DA-031 control sequence,
then traverse DA-023 remaining skipped carriers in frozen order, attempting full
carrier then frozen member exactly as DA-031. Admit on exact fit and continue on
overflow. Atomic alternate members are excluded from this primary test.

No evidence, outcome, answer, conversation, fitted feature, similarity,
threshold or sweep enters codec choice or allocation.

## 5. Blind Gates

Require sentinel absence and shortestness; parser boundary/malformed tests;
exact decode; immutable identity/order on 1,098 rows; selected charge <= DA-031;
positive strict savings, pair/member/overflow actions; median savings >=64;
<=16,000; byte-identical replay; zero calls. Stop unopened on any mismatch.

## 6. Outcomes and Disposition

Report exact delivery against DA-031, conversation cells, DA-032 blocker
rescues, costs/positions and ceiling gap.

Report `NF_SENTINEL_VARINT_SIGNAL` for >=2 gains, zero losses and every
conversation nonnegative. Report `WEAK_NF_SENTINEL_VARINT_SIGNAL` for exactly
one gain, zero losses and every conversation nonnegative. Otherwise report
`NO_NF_SENTINEL_VARINT_SIGNAL`. Any DA-031 loss is a causal stop.

Spent availability only; no reader, runtime, transfer or adoption claim. Do not
tune sentinel alphabet, codec, traversal, fallback or budget.
