# Study 010 Amendment 001: Executable Endurance Protocol

**Authorized by:** study author
**Authorization:** documented amendments are permitted to put Studies 009 and
010 into working order
**Applies before:** script lock, calibration, implementation, and live runs
**Supersedes:** `decisions/DECISION_prelock_stop_study010.md`

## Repaired Preconditions

Study 009 now supplies the branch input that the draft lacked: Arm L scored
12.0/13.0 versus Arm S at 10.5/13.0; LTM has value at 120 turns; digest carry
is false; and the accepted Study 007 treatment remains Arm L. The earlier
pre-lock stop remains as the audit record of the contradiction at `f2debf8`.

## Architecture-Aware Parity

The draft's cross-arm byte-identical prefix requirement is replaced by:

1. same decoded script bytes and turn order;
2. same model, quantization, seed, sampling, response ceiling, context
   capacity, embedding model, and single-slot runtime;
3. same N, K, topic assignment, pinned rules, and observability components;
4. within-arm deterministic prefix reproduction across fresh lifecycles;
5. expected prompt differences exactly where L's accepted LTM tier differs
   from S's structural absence of that tier.

Cross-arm response identity is not an integrity property.

## Runtime Feasibility

The study remains a live 1,000-turn, two-arm comparison. Non-probe turns ask
for concise answers; probe turns retain rubric-appropriate answers. The
2,048-token safety ceiling is unchanged.

The bounded N/K and 32,000-character LTM budgets make context depend on
selected context rather than all stored episodes. The carried 50,000-token
capacity remains binding if offline replay and rehearsal project a peak below
25,000 tokens. Otherwise capacity is raised before GO and recorded.

## Checkpoint and Probe Guards

Every 100 turns, runners write an atomic checkpoint with completed turn,
script hash, database backup, continuation identifiers, accumulated rubric
responses, and integrity hashes. G4 compares interrupted/resumed and
uninterrupted deterministic fixture runs.

Interim probes are turns 250-252, 500-502, and 750-752. Terminal probes are
987-1000. Probe episodes remain stored in both arms but are excluded as
span-dream emission sources.

## Blinded Agent Rater

The unavailable human dependency is replaced before scoring by a blinded
agent rater. Anonymous probe-response files and a hash-derived sealed mapping
are committed first. Primary and strict scores plus rationales are committed
before mapping unseal or full-run mechanism-log inspection.

## Bars

The registered bars and Bar 1 thresholds are unchanged. Digest G3 is not
applicable because digest carry is false. This amendment does not replace live
inference with replay or reduce the 1,000-turn count.

## Lock Hash Correction

Before calibration, the lock was corrected from raw working-tree bytes to
UTF-8 decoded, LF-normalized SHA-256. This is the cross-platform rule already
used by the study runners. No script, rubric, or plant-key content changed.
