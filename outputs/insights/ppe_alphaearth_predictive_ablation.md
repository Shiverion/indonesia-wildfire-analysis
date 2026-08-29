# Prior-year AlphaEarth predictive ablation

This is an out-of-time prediction robustness test, not a causal test.

| Model | Conditional log loss | Top-1 recall | Mean reciprocal rank |
|---|---:|---:|---:|
| explicit | 1.4671 | 0.368 | 0.605 |
| embedding only | 1.2708 | 0.458 | 0.672 |
| combined | 1.2664 | 0.467 | 0.677 |

Combined-minus-explicit improvement (positive is better): **0.2006** (matched-set bootstrap 95% interval 0.1712 to 0.2310).

The embedding always comes from the calendar year before the fire opportunity. Same-year and post-fire features were rejected by the automated leakage gate.

This comparison cannot identify deliberate burning, plantation expansion, government performance, or any other causal mechanism.
