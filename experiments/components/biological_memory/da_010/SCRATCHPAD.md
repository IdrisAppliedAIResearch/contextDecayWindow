# DA-010 Scratchpad

## Inherited Evidence

- DA-008 speaker dictionaries: 935->961, +26/0, median usable slack 520.
- DA-009 role patterns: 961->966, incremental 7/2 (p=.180), +31/0 direct.
- One-hop full-pair oracle is 986; 20 reachable gains remain.
- DA-004 rank stays frozen. Its advantage over controls is not independently
  differentiated, so this branch tests payload cost only.

## Branch Rule

If no turn arm exceeds 966 without conversation regression, return to exact
repeated-structure compression or a fresh transfer test. Do not tune lexical
member choice or DA-004 thresholds on NF-004. If a turn arm carries signal,
separate increased admissions from correct-member selection before proceeding.

## Result

- Blind payload gate passes: member 0/1 selected 15,088/11,012; 2,373 ties;
  134 edges have best-turn fit without pair fit.
- Full/best/atomic/fallback complete = 966/962/970/970. Atomic and fallback each
  add 4/0 over full (p=.125) and +35/0 over direct.
- Best-turn globally is unsafe: 6 gains/10 losses versus full. Pair protection
  is necessary before lexical localization.
- Atomic and fallback have identical complete sets despite differing linked
  sequences on 922/1,098 questions. Carry forward the narrower overflow fallback.
- Zero gains require both members of the same linked pair. Oracle 986 leaves 16.
- Next lead: characterize the 16 residual reachable misses and whether their
  ranked carrier is blocked by payload size, prior fallback consumption, or
  multi-evidence conjunction. Do not tune thresholds.
