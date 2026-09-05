# DA-015 Reversible Phrase-Dictionary Rendering

**Status:** `POST-OUTCOME MECHANICAL TRANSFER PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-014 result commit `da54d67a`
**Standing:** evidence-blind lossless representation test on two spent corpora
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can an explicit, reversible phrase dictionary recover the roughly 100-225
additional characters implicated by DA-014 without changing or dropping any
direct episode?

This tests representation capacity only. It does not assume that a reader will
use dictionary-coded text correctly.

## 2. Locked Populations

Run the same codec without corpus-specific settings on:

- NF-004 LoCoMo: all 1,104 sealed holdout question contexts from DA-009's exact
  role-pattern direct selections at 16k.
- DA-013 LongMemEval: all 465 exact direct contexts from its committed blind
  direct seal at 16k.

Direct identities, order, members and role-pattern rendering remain immutable.
No answer, evidence, question type, outcome, link action or reader signal enters
phrase selection.

## 3. Fixed Codec

Operate only on member text fields after DA-009 role-pattern coding. Candidate
phrases are exact substrings spanning 2-6 consecutive ASCII alphanumeric word
tokens, including their original intervening characters, with length at most 80
characters. A phrase must have at least two nonoverlapping literal occurrences
in the current context.

Use the shortest prefix consisting of one or more `~` characters for which no
literal member contains `<prefix>p`. Dictionary code `i` is
`<prefix>p<i><prefix>`. Codes are never searched for phrases or replaced again.

At each step, evaluate every eligible original phrase against current literal
segments. Exact net savings are removed literal characters minus code characters
minus the new declaration cost. A declaration is
`@<code>=<JSON-escaped phrase>`; declarations are newline-separated and charged
exactly. Choose the largest strictly positive net savings, then longer phrase,
then lexicographically smaller phrase. Replace all nonoverlapping literal
occurrences left-to-right. Repeat until no candidate has positive net savings.

Decoding replaces structured code segments with their dictionary phrase and
must reproduce every original member string exactly. The role dictionary,
default role pattern, pair/member boundaries and direct identities are carried
unchanged. Any expanding row retains the DA-009 rendering with no dictionary.

## 4. Fixed Endpoints

For each corpus report rows, identities, dictionaries, declaration characters,
replacement counts, incremental savings, total savings versus original direct,
compressed characters and slack.

Primary mechanical bar: median incremental savings over DA-009 is at least 100
characters in **each** corpus, zero rows expand, every row decodes exactly, and
both full builds replay byte-identically. Report `TRANSFERABLE_CAPACITY_SIGNAL`
only if all conditions pass; otherwise `NO_TRANSFERABLE_CAPACITY_SIGNAL`.

Secondary DA-014 accounting, opened only after the blind codec artifact is
committed: report how many of the 49 initial-size misses would have enough added
slack for their cheapest evidence-complete payload. This is an oracle capacity
count, not delivery or authorization.

## 5. Preflight Part 1 - Exploration

**Behavioral identity.** The codec changes only member text serialization and
adds an explicit dictionary. Direct identities, order and decoded content are
exact.

**Name-to-behavior.** Tests must establish prefix collision avoidance, exact
candidate spans, nonoverlap, declaration charging, deterministic tie rules,
literal-only replacement, inverse decoding, fallback on expansion and unchanged
role structure.

**Distribution.** Before evidence access report phrase/replacement/savings
distributions separately for both corpora, including zero-dictionary rows and
the longest dictionary. No DA-014 class or target identity enters Part 1.

Risks are undercharging declarations, ambiguous codes, hidden content changes,
optimizing one spent corpus, and treating losslessness as reader usability.

## 6. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify NF-004 dataset/DA-009 artifact and DA-013 direct artifact
  hashes; require 1,104 and 465 rows.
- **PF2 Identity:** pass every codec behavior in Section 5.
- **PF3 Ordering:** commit protocol before codec implementation; commit blind
  two-corpus outputs before joining DA-014 traces.
- **PF4 Reachability:** require selected phrases, multiple dictionary entries,
  overlapping candidates, prefix collision handling and zero-dictionary rows in
  tests; corpus reachability may differ.
- **PF5 Keys:** preserve corpus, question, direct identity, pair and member keys.
- **PF6 Reproduction:** reproduce DA-009 and DA-013 direct chars/identities.
- **PF7 Absorbing state:** require deterministic byte-identical builds.
- **PF8 Length:** process all 1,569 contexts.
- **PF9 Surrogate audit:** exact decoding is not evidence that a model decodes
  or uses the content.
- **PF10 Live boundary:** reader validation, adoption and production syntax need
  separate registration.

Stop on input drift, identity/order change, decode mismatch, undercharge,
nondeterminism or any expansion. Commit blind result, then optional DA-014 oracle
capacity accounting, report, scratchpad and digest. Do not tune phrase bounds,
syntax or bars after running.

