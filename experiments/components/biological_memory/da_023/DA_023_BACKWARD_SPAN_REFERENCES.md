# DA-023 Immutable Backward Span References

**Status:** `POST-OUTCOME CROSS-CORPUS EXPLORATION PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-022 result commit `deb07136`
**Standing:** evidence-blind structural-capacity study on spent NF-004 and LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can declaration-free exact references to spans in earlier context members add
capacity without displacement where phrase dictionaries saturate?

DA-021/022 prove the immutable-pack mechanism is safe but show direct/admitted
phrase coding transfers weakly to already phrase-coded LongMem. DA-023 changes
only the reversible representation. Strongest control payloads remain immutable;
recovered capacity may append skipped carriers only.

## 2. Locked Controls and Populations

- NF-004: all 1,098 primary questions; DA-010 at 970, direct 935, ceiling 986.
- LongMemEval: all 465 questions; DA-016 at 188, direct 164, ceiling 250.
- Exact baseline actions and frozen skip members come from DA-019 artifact SHA
  `b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f`.

No DA-019/020 substitutions or DA-021 additions enter the control.

## 3. Frozen Backreference Codec

Encode member texts in context order. A reference may copy only a contiguous
exact substring from a **previously decoded member**, never from the current or
future member. Its literal syntax is:

`PREFIX r MEMBER_INDEX , START , LENGTH PREFIX`

with no spaces. `PREFIX` is the shortest repetition of `~` for which
`PREFIX + "r"` occurs in none of the question's direct, baseline or eligible
skipped member texts. Indices are zero-based decimal. There is no dictionary or
declaration.

At each source position, select the longest match in any prior member. Ties use
lowest member index then lowest start. Emit a reference only when its rendered
code is strictly shorter than the copied substring; otherwise emit the next
literal character. Coalesce adjacent literals. The four-character lookup index
is an implementation acceleration only: every possible reference code exceeds
four characters, so no beneficial match can be excluded.

Decode references against already decoded members and require exact member-byte
identity. No nested or self references are allowed.

## 4. Immutable Additive Allocation

1. Reconstruct every strongest baseline payload in original order.
2. Backreference-code the full immutable baseline. If it is not strictly smaller
   than the committed control rendering, retain that control renderer exactly.
3. Preserve all baseline payload identities, members and order.
4. Traverse only baseline `SKIP` actions in original order. Attempt pair then
   frozen singleton, using the chosen renderer and exact dynamic role cost.
5. Added members may reference only prior decoded members. Add their decoded
   text to history only on admission. Continue after overflow.

No baseline payload can be removed, altered, reordered or rematerialized. The
16k budget, links, order, member choice and skip behavior remain fixed. No
answer, evidence, outcome, category, fitted label, threshold or sweep enters.

## 5. Mechanical and Outcome Gates

Before evidence access commit all prefixes, reference segments, decode hashes,
renderer choices, baseline savings, additive actions and exact costs. Require
on both corpora: median recovered baseline capacity >=64 characters, positive
backreference use, positive added pairs/turns, remaining skips, zero expansion,
exact baseline decode, <=16k charge and byte-identical replay. Otherwise stop
unopened as `NO_BACKREFERENCE_CAPACITY_SIGNAL`.

After a pass, measure exact complete evidence delivery. Any control loss is a
causal-accounting stop. Report `BACKREFERENCE_DELIVERY_SIGNAL` only if treatment
gains at least five items over control on each corpus, loses zero and every
conversation/question-type cell is nonnegative. Otherwise report
`NO_BACKREFERENCE_DELIVERY_SIGNAL`. Corpus-specific movement is descriptive.

## 6. Preflight

- **PF1 Inputs:** seal DA-010/016/019 controls and all source populations.
- **PF2 Identity:** test prefix collision, longest/tie selection, literal
  coalescing, nonbeneficial fallback, prior-only references, exact decode,
  control fallback, dynamic pair/singleton coding and rejected-payload history.
- **PF3 Ordering:** commit protocol, then blind artifact before evidence.
- **PF4 Reachability:** require every mechanical condition in Section 5.
- **PF5 Keys:** preserve corpus, question, member, reference, baseline action,
  skip, neighbor, cost and decode keys.
- **PF6 Reproduction:** require exact baseline identities/actions and direct
  immutability; reject any source or control drift.
- **PF7 Determinism:** require byte-identical blind and opened replay.
- **PF8 Length:** process all 1,563 questions and every baseline skip.
- **PF9 Surrogate audit:** machine decode and availability are not reader use.
- **PF10 Live boundary:** no reader, latency, fresh-validation or adoption claim.

Stop on collision, invalid reference, decode mismatch, expansion, baseline
change, undercharge, fresh call, nondeterminism or unexplained outcome. Do not
tune syntax, match objective, source scope, fallback, order or payload choice.

