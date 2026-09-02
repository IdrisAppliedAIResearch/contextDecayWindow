# DA-031 Scratchpad

## 2026-08-30 - Registration

- Fixed self-delimiting base-32 varints remove coordinate separators and encode
  three relative coordinates with disjoint continuation/terminal alphabets.
- Exact strict fallback to each row's DA-028 codec; decoded identities/order are
  immutable. Only varint savings fund frozen-order additions.
- Primary excludes DA-030 atomic completion to isolate representation.
- Strong bar NF >=2/0 and Long >=5/0; partial >=2/0 in either.
- Zero model, embedding and cache calls.

## 2026-08-30 - Result

- Blind gate: varint selected on NF 1,098/1,098 and LongMem 463/465; two
  LongMem rows retain DA-028. Median strict savings are 1,066/889 chars.
- NF delivery 977 -> 983, +6/0, p=.03125. Gains are all five DA-029 prior
  compact-consumption residuals plus the one multi-carrier conjunction.
- LongMem delivery 208 -> 211, +3/0, p=.25: one initial-size, one prior-
  consumption and one wrong-member residual.
- Every group is nonnegative. The joint strong bar fails because LongMem is
  below +5; registered disposition is `PARTIAL_VARINT_RELATIVE_SIGNAL`.
- NF now sits 3 below its 986 one-hop ceiling. The incremental result identifies
  coordinate overhead as causal for the prior-consumption band.

