# DA-003 Amendment 001 - Univariate AUC Direction

**Date:** August 29, 2026
**Timing:** after blind edge seal `df20aca3`; before evidence import
**Reason:** Section 3.3 requires directions fixed before outcomes but does not
enumerate them.

Report raw AUC with larger feature values as the positive direction for every
feature and both endpoints. Do not invert, maximize, or relabel AUC after the
join. Interpretation may state that values below .5 carry signal in the
opposite direction, but ranking and per-conversation consistency must retain
the raw orientation.

No feature, endpoint, model, population, or bar changes.
