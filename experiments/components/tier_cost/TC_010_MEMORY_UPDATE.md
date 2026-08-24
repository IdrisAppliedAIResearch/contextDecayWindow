# TC-010 Research Memory Update

TC-010 is complete at `REGISTERED-OFFLINE` with `NO_SPLIT_SELECTED`. The user
explicitly locked query-wise normalized 80/20 dense/BM25 (`CC80`) as relevance
and the TC-007 50/50 character allocator. Spread was minimum maximum pair
cosine inside the top `ceil(25%)` of CC80; literal reverse CC80 was the negative
control. No pool/share sweep was allowed.

At 16k, full CC80/qualified/prior-A3/global-bottom combined is
771/752/757/706, targeted 666/653/653/623 and breadth 17/13/14/8. Qualified
versus CC80 is 12 gains/31 losses; breadth 0/4 and all four conversations
negative. At 32k the order is 819/818/818/771 combined, 689/688/686/666
targeted and 24/24/27/17 breadth. Qualified has zero gains and one loss versus
CC80, with identical breadth evidence.

Mechanism interpretation explains both budgets. At 16k qualified and CC80 sets
differ by median 32 identities; spread adds a median 16 outside CC80, producing
five breadth identities gained and eight lost. At 32k sets are identical on
765/871 questions; the qualified pool is wholly inside full CC80 on 841/871,
so the route reorders information CC80 already fits. Pool exhaustion returns a
median 23 candidates to semantic retrieval.

Literal global bottom is a valid negative control: qualified beats it 46/0 and
47/0 combined at 16k/32k. Least query relevance is not breadth. Least
redundancy inside a fixed relevant pool is safer but not sufficient: it either
displaces higher-value evidence under tight capacity or becomes inert under
loose capacity. Full CC80 is the frozen fallback. Availability only; no reader,
deployment, pool tuning or share tuning is authorized.
The final repository suite is 2,248 passed.
