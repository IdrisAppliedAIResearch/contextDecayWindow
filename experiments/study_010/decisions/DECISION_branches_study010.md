# Decision: Resolve Study 010 Branch Inputs

**Source:** Study 009 amended final report
**Study 009 close commit:** `e533011`
**Study 010 registration commit:** `ead2f66`

## Branch 1: Digest Carry

**Resolved: false.** Neither arm carries the topic digest.

Study 009 did not validate Digest Bars 1-2. More strongly, the pre-run
fact-aware replay failed at the registered `d = 2`, `B_digest = 2,500` setting
and at every calibration tested through `d = 50`, `B_digest = 50,000`. The
registered Study 009 contingency dropped S+D before ablation.

## Branch 2: Arm L Configuration

**Resolved: accepted Study 007 treatment, unchanged.**

Study 009 found LTM value at 120 turns: accepted Study 007 Arm L scored
12.0/13.0 versus pure-STM Arm S at 10.5/13.0. Its mechanism analysis does not
motivate a configuration change, so Study 007 remains the accepted LTM
configuration:

- span dreaming formation;
- `B_ltm = 32,000` exact rendered characters;
- `k_min = 1`;
- similarity-ranked per-topic floor;
- no fill cap;
- episode rendering;
- containment dedup with STM precedence.

## Study 009 Input

The null-test verdict is available and decisive under Study 009 Amendment 001:
LTM retirement at 120 turns is cancelled. Study 010 tests whether that
advantage persists or grows at 1,000 episodes.
