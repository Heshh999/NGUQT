# V4 analysis code

`lib.py`  — loading, validity filters, split definition, winsorisation.
`lib2.py` — the estimator: pooled mean as the point estimate, day-block
bootstrap for the standard error.

Two corrections were forced during the analysis and both are encoded here:

1. **Degenerate ATR.** `net_240m / tfAtr` exploded where tfAtr fell below one
   tick. 142 rows of 181,259 (0.078%) carried a y-sum of -17,546 against a
   dataset total of -16,199 — they more than accounted for the entire mean.
   All were thin overnight holiday bars. `MINATR = 1.0` point.

2. **The point estimator.** Mean-of-daily-means put the 60m estimate at
   +7.12 pt while the pooled mean was -0.36 pt, and produced a combined figure
   above BOTH of its own subgroups. That is possible when single-side days are
   extreme and both-side days are not, and it makes the statistic unusable as
   "what a trade earns". The point estimate is now the pooled mean; day
   clustering is used only for the standard error, where the dependence lives.
