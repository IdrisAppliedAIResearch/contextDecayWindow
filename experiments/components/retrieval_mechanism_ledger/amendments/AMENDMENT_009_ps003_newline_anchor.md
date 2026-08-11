# Amendment 009 - PS-003 Carried Newline Anchor

**Date:** August 11, 2026
**Study:** PS-003 ambiguous natural-language cue resolution
**Trigger:** Blocking full-suite verification after the ordered result
**Status:** AUTHORIZED

## Trigger and evidence

PS-003 registered the working-tree raw SHA-256 of PS-001's first-process
`exploration.json` as
`A78922CA25F0CA5027F695B2A12E8059EE83597366F1B87ECF7B7EF6C5FFDC1D`.
That is the primary Windows checkout's CRLF representation.

PS-001's own locked preflight requires the content-identical LF representation,
SHA-256
`B1645ECB4991ED7B3BD84729779CCAEB7306B39A035DFC196E901F54E52B154D`.
The complete-suite attempt could not satisfy both assertions simultaneously:
`1507/1509` tests passed, with PS-001 rejecting CRLF and PS-003 rejecting LF.

This is the same historical newline split documented in PS-002 closeout. Both
files parse to the same JSON payload and carry the same PS-001 mechanism digest
`0D45DDD45980DBF3989A543136BAD52D4F743F650F3C0AF76E370F049B6C80CC`.

## Change

PS-003 verification may accept either of the two raw byte hashes above for the
one carried PS-001 exploration file. After parsing, it must still require the
exact committed PS-001 mechanism digest. The observed raw representation and
hash must be retained in preflight output.

All other PS-003 anchors remain single-valued and unchanged.

## Rationale

One checkout cannot expose LF and CRLF bytes at the same path simultaneously.
Binding both known raw representations plus the invariant parsed mechanism
identity preserves content integrity while allowing PS-001 and PS-003 verifiers
to run in the same mixed-representation test environment.

This repairs an infrastructure contradiction. It does not make any mechanism,
eligibility rule, relevance bar, gate, or disposition easier after the result.

## Exclusions

This amendment does not authorize editing either retained artifact, normalizing
other inputs, changing PS-001/PS-002/PS-003 code behavior, rerunning selection,
opening additional labels, changing G1-G5, measuring stress tests, generating
answers, scoring, live evaluation, promotion, or adoption.

## Authorization

The author explicitly authorized the implementation agent to make and own
necessary revisions while implementing PS-003 end to end. This correction is
restricted to the blocking representation contradiction and preserves every
registered scientific criterion and observed result.
