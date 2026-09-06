# Preflight instrumentation note

The first preflight attempt at 4324f641 stopped before writing outputs or reading labels: direct Python equality included a freshly measured `prior.baseline_report.latency_ms`, and tuple/list differences from JSON serialization. The repair normalizes through JSON and removes only that timing field. All remaining trace fields, source identities, rankings and exact rendered prompt bytes remain mandatory equality checks. This is an instrument repair, not a changed fusion or relaxed evidence criterion.

The textual query rule also activates the 32 absence histories: they ask `before` with an anchor, despite having no correct location evidence. Thus there are 160 active queries, 128 answerable before cases plus 32 absence guards; the 32 latest queries remain byte-identical. Absence context changes are reported, and absence answer safety remains untested without a reader.
