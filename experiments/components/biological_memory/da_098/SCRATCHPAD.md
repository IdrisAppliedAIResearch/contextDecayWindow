# DA-098 Scratchpad

- Freeze DA-035 as the complete 16k architecture prefix.
- Reproduce NF-004 pair controls at 935/1024 before accepting treatment.
- At 32k, append absent members in frozen pair rank and source-member order.
- Preserve exact sentinel codec, skip-on-overflow and immutable prefix.
- Zero model/embedder calls and zero cache misses.

## Pre-Run Reconstruction Correction

- The first blind attempt stopped on the ARCH_16 charge gate before writing an
  artifact. The reconstruction helper saw completed DA-035 actions as its base
  and then appended them a second time.
- Explicitly substitute `da031_control` into the helper, then append DA-035
  actions once. Protocol, order, budget, bars and population are unchanged.
