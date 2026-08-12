# DMR-001 Memory Update

DMR-001 stopped at G3 with disposition `DEGENERATE_FORMATION`. The online drift
rule is not a valid event substrate on this evidence, so DMR-002 through
DMR-006 are blocked.

The failure has a precise shape. On the 2,000-episode sealed holdout, 52 of 74
events closed because `max_event_size` bound: a forced fraction of 0.703
against a registered bar of 0.35 that PF4 had verified reachable at 0.005 on
development. The drift predicate is not wrong, it is under-triggered: all 20 of
its holdout boundaries matched an annotation within tolerance, precision 1.000,
while none of the 52 forced boundaries matched anything. The locked threshold
of 0.70 sits above the holdout's 95th drift percentile (median 0.362, maximum
0.799) yet fires on 18.5% of eligible development episodes at precision 0.233.

The generalizable lesson is that **an absolute drift threshold has no
transferable scale across conversations**, and a size cap registered as a
safety bound silently becomes the primary partitioner when the threshold
under-fires. A count-shaped guard rail replaced the mechanism it was meant to
protect, which is the same class of failure the program has repeatedly hit with
count-based budgets.

G1, G2, and PF1-PF10 all pass. The locked component and the independently
written Part 1 implementation agree on every decision across 1,724 episodes
with zero mismatches.

Two defects are recorded rather than repaired. PF4 verified reachability for
the singleton and forced-fraction bars but not for the largest-event-share bar,
which is unreachable by construction for any session shorter than four times
`max_event_size`; that check also failed, and the disposition does not depend
on it. Separately, the study found that the 1,000-turn endurance corpus holds
only 156 distinct episodes across 1,000 turns, which qualifies DX-002's
saturation reading without changing any published number.
