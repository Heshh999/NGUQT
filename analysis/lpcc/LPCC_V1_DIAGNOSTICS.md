# LPCC-V1 — DIAGNOSTICS (predeclared; never candidates)

Stressed-cost EV (1.74 pt RT), from `LPCC_RUN_OUTPUT.txt`:

| test | n | EV | reading |
|---|---|---|---|
| PRIMARY | 127 | −2.563 | the frozen rule |
| D1 no-regime ablation | 223 | −2.221 | regime gate made it worse |
| D2 no-displacement ablation | 1,005 | −2.704 | β>0 alone loses |
| D3 unconditional baseline | 1,689 | −1.722 | window continuation loses unconditionally |
| D4 direction reversal | 127 | −2.159 | both directions lose (cost sink) |
| D5 regime-label permutation | 10,000 perms | null −2.204 | p 0.563 — gate ≈ noise |
| D6 regime shift −10 / −20 | 118 / 127 | +4.25 / +0.84 | shifted noise beats the real gate |
| D6 regime shift +10 / +20 | 125 / 117 | −0.21 / −3.25 | non-tradable falsifications |
| D7 matched random-day control | 83 | −0.258 | event days no better than matched days |
| D8 randomized-anchor placebo | 200 draws | null −3.166 | p 0.423 — anchor adds nothing |

Influence: drop-most-influential −1.78; drop-best-trade −3.22 — the
negative result is not one bad print. Every seed recorded (20260829–31).
All ten diagnostics point the same way: neither gate carries signal in
this window; the strategy's losses are structural (flat conditional
drift minus costs), not an unlucky draw.
