# DMR-001B Memory Update

DMR-001B passes G1-G5 with disposition `ADAPTIVE_FORMATION_TRANSFERS_OFFLINE`,
ceiling CHARACTERIZED. It does not unblock DMR-002.

Replacing DMR-001's fixed drift threshold with a percentile of the
conversation's own recent drift fixes the failure that stopped DMR-001. Every
cell of the registered percentile grid holds the cross-corpus fire-rate swing
between 1.42x and 1.65x, where the fixed rule swung 9x to infinite. The size
cap, set to 128 as a never-should-fire guard, never bound once across 3,724
episodes.

Two honest qualifications. The 1,000-turn family got worse, .733 to .583 under
identical accounting; the gain is on the worst family, .419 to .487, and on cap
independence. And a degenerate input is reachable that no registered bar
detects: on a stream with no drift variance, `drift >= the 97.5th percentile of
drift` is true as soon as the history warms, so the rule fires whenever
min_event_size is met. The test suite found it, the preflight did not, because
the preflight runs on real data.

Two independent reasons this is not confirmatory: there is no sealed holdout,
both corpora having been read by DMR-001; and DEVIATION_001 records that the
component was written before the pre-registration and committed with it, so PF3
reports FAILED rather than being redefined.

The generalizable lesson is the measurement, not the mechanism: cross-corpus
fire-rate swing is a better health signal than boundary agreement. It needs no
annotations, gets stronger as corpora are added, and tests the property that
actually failed.
