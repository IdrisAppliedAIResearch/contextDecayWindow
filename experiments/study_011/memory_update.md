# Study 011 memory update

- **The deployed configuration's LTM tier is inert.** Arm D scored 8.0/13 and
  Arm A (recency only) scored 8.0/13 — identical on all thirteen questions,
  identical Q11 availability at 9/17, identical targeted at 7/21, and
  byte-identical windows at turns 117, 118 and 119. A system with a similarity
  tier was indistinguishable from one without. IC-001's Branch A, live.
- **Relieving the suppression did not help.** Arm C gave the similarity tier
  first claim: 13 K-path episodes against 1, Q11 up to 10/17, targeted up to
  10/21 — the best availability of any arm — and 7.0/13, the worst score. B1
  fired and the correction was not adopted.
- **This is the LV-001 pattern at the arc scale.** Availability is not the
  answer. The bar existed precisely because a delivery gain can accompany an
  answer loss, and it did.
- **The loss is late-probe, not uniform.** C−D = −1.0 from three gains (Q1
  +0.5, Q2 +1.0, Q4 +0.5, all early and middle plants) and three losses (Q6,
  Q7, Q10 at −1.0 each, all late). Turn 118 carries both Q7 and Q10 and holds
  no K candidate at all, so the similarity tier could contribute nothing there
  under any order; what changed is the recency context it displaced elsewhere.
  Consistent with displacement, **not established**.
- **The runtime is not bit-reproducible.** The same 757-byte prompt at turn 1
  produced a 343-character answer in one run and an 80-character answer in
  another, at seed 5005 with one slot and speculative decoding off. The
  mechanism reproduces exactly, but only one turn is testable, because a
  differing answer changes the store. A one-point gap from single runs sits
  inside an unmeasured noise band. The program's standing rule requiring a
  byte-identical seeded prefix rerun is **not satisfiable on this runtime**.
- **A ceiling measured on one store does not forecast another.** §4.1's
  achievability gave 6 of 9 windows, measured on the corrected Tier 6 store.
  Arm C landed on it exactly; Arm B reached 9 of 9, because Arm B builds its
  own store with no recency window from turn 1 and its queries meet different
  candidates. The pre-registration said this before the run, and it was right
  to.
- **Thirteen rubric questions occupy nine retrieval windows.** Q3/Q12 share
  turn 114, Q6/Q9 share 117, Q7/Q10 share 118, and Q13 spans 112–120 with no
  window. Questions sharing a turn share one window exactly and are not
  independent evidence. Four questions — Q7, Q8, Q10, Q13 — can never satisfy
  a K-delivery threshold.
- **"Delivers a K episode" had to be defined before it could be used.** Under
  the reading that counts any delivered episode which was also a K candidate,
  Arm A — whose K tier is disabled — "delivers K" at 4 of 9 windows via
  recency, and G1 fails by construction. Only the K-only reading makes G1
  satisfiable and G2/G3 meaningful.
- **Arm B is not degenerate.** Prediction 8.3 gave ~40% that an arm with no
  recency window fails the ablation outright. It completed 35 turns and then
  121, with no empty response and no verbatim repeat, and scored 7.5/13 —
  half a point below recency-only.
- **Four of six registered predictions are refuted**, including the direction
  of the headline contrast. The registration's own "uncomfortable case" — Arm
  C winning by less than a point — was too optimistic.
