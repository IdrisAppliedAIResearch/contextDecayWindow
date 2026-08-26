# LV-005 — blind-judge stop

**Status:** stopped before unblinding; no outcome  
**Date:** 2026-08-26

The registered blind judge run stopped after preserving 136 valid judgments.
The next scheduled response, for blind id
`246c60b934c6ef5407667603029949b115fe9fdced33e7de67f3b15d0e5fd996`,
judge pass 1 and seed 9006, naturally stopped but contained only a `REASON:`
line. It omitted the required verdict and was therefore unparseable. That raw
failed response was displayed by the exception but was not appended because
the registered code parses before persistence.

The preserved file contains 45 blind ids with three judgments each and one id
with its pass-0 judgment only: 136 rows, no duplicate schedule keys. Its
SHA-256 is
`775fc2e2f0e86da9568f7f78bb775da5e9a881e09329357e775a0e088774ad1b`.
The blind surface remains sealed at
`97aaf2def7ff3f5c843fba4c98fd0afed3921ccbe44a43d44319f7c7b2c45205`.

The arm mapping and arm-level results were not opened. LV-005's registration
requires every judgment to be parseable, so LV-005 has no result and cannot be
resumed or analyzed under its existing protocol. Any repair requires a new
registered continuation that preserves this stop.
