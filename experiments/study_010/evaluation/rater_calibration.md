# Study 010 Rater Calibration

Score these synthetic cases before opening either anonymous response file.
Proceed to real scoring only if all three scores match the answer key at the
bottom.

## C1 - Reasoning-only `NO_ANSWER`

**Type:** targeted

**Expected items:** Alpha; Beta; Gamma; Delta; Epsilon

**Model output:**

```text
<think>
The response should probably mention Alpha, Beta, Gamma, Delta, and Epsilon.
I should organize those five items clearly.
</think>
```

## C2 - Targeted completeness

**Type:** targeted

**Expected items:** Alpha; Beta; Gamma; Delta; Epsilon

**Model output:**

```text
Alpha, Beta, Gamma, and Delta.
```

## C3 - Breadth boundary

**Type:** breadth

**Expected paired anchors:** Alpha + 1; Beta + 2; Gamma + 3; Delta + 4; Epsilon + 5

**Model output:**

```text
Alpha: 1; Beta: 2; Gamma: 3; Delta: 4.
```

## Answer Key

- C1: `0.0` because content inside a reasoning block is not scoreable and no
  final answer exists.
- C2: `0.5` because four of five targeted items are present.
- C3: `1.0` because four of five paired anchors is exactly 80%.
