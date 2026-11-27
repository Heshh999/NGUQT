# MROF_YT_WAVE30_CLOCKS_REGISTRATION.md — B several times a day: three changes to B

**Status: FROZEN on 2026-11-27, before any of the rules below was
computed on any data, and before any ES or RTY bar, or any NQ bar after
2026-06-11, was read by anything.** What had been seen beforehand is
listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

---

## 0. Where this comes from, and what was already seen

The operator asked, on 2026-11-27, for a strategy that trades several
times a day, as fast as a retail account can go, and left the ideas to
this file.

Three things are known that decide where to look.

- **The cost of a trade is fixed and the distance price travels grows
  with the square root of time.** A forecast has to explain a share of
  the move of about the cost over 0.8 times the usual move of the
  holding time. Hold four times longer and the share needed halves.
- **Below about half an hour prices tend to give back; from a few hours
  on they tend to go on** (Safari and Schmidhuber, "Trends and Reversion
  in Financial Markets on Time Scales from Minutes to Decades", on 14
  years of futures tick data; read here in summaries only). A fast trade
  has to be a fade, and a fade pays the spread every time.
- **A fast signal that cannot pay its own costs can still time the
  trades of a slow rule** (Zarattini and Pagani, "Improving Performance
  with Fast Alphas", February 2026, on five-minute bars of SPY from 2007
  to 2026: after several five-minute bars one way the next gives some
  back; traded alone it loses after costs; used only to time the fills
  of an intraday trend rule of B's kind, it raised the net result).
  Their page could not be opened from here: the number of bars they use
  and how they move a fill were not read. §2's BT is this file's own
  rule, fixed without them.

So this file does not look for a new fast rule. It takes the one rule
that already decides several times a day, B, and fixes three changes to
it before the data that can judge them is read: the same rule on other
clocks, the same rule on a faster clock, and the same rule with its
fills timed by the fast give-back.

**Seen beforehand, on the ten years of NQ (2016-01 to 2026-06-11):**
everything in wave twenty-four's and wave twenty-six's reports,
including B's result on its own clock (decisions on the half hour), and
that D, which decides every minute, earned as much as B before costs
and next to nothing after them.

**Not seen:** B on any other clock, B's fills at any other minute, or
the five-minute give-back of §3, on any bar of any market; any ES or
RTY bar; any NQ bar after 2026-06-11.

## 1. Common to all

Wave twenty-four's bars, trading days, front contract, P(m), VWAP, the
daily chain and B; wave twenty-five's markets, costs, halves, the
reader's refusals and the later-months window, all unchanged. B's
bounds, its volatility s and its sizing, leverage = min(2 % / s, 4), are
B's own in every change below; a change alters only what it names.

**c(m)** = P(m) − P(m − 5 minutes), the five-minute change that ends at
clock time m.

## 2. Three changes to B

B decides at 10:00, 10:30, …, 15:30 and is flat at P(16:00).

**BS — the same rule on two other clocks.** Not a change of the rule: a
check that B does not hang on the minute it looks at.
**B+10** decides at 10:10, 10:40, …, 15:40; **B+20** at 10:20, 10:50, …,
15:50. Twelve times each, as B.

**BF — a faster clock.** B's rule at every ten minutes: 10:00, 10:10, …,
15:50 (36 times).

**BT — timed fills.** B on its own clock, with the same decisions. When
B changes its position at a time m, the order is a buy (the position it
wants is above the one it has) or a sell. **When c(m), c(m − 5) and
c(m − 10) are all in the order's direction** (all above 0 for a buy, all
below 0 for a sell), **the order is filled five minutes later, at
P(m + 5); otherwise at P(m).** Between m and m + 5 the old position is
held. The flat at 16:00 is never moved. The number of orders and their
costs are B's.

## 3. Reported, never judged

- **The fast give-back itself.** At every five-minute mark m from 09:45
  to 15:50 where c(m), c(m − 5) and c(m − 10) have one sign: the next
  change, c(m + 5), taken against that sign, in points and in basis
  points of P(m): how often it occurs, its mean, and what a trade on it
  alone would keep after a round trip. The same for two and for four
  changes in a row.
- **How often each rule trades:** its position changes a day and what
  they cost.
- **The three clocks together:** each session's result is the mean of
  B's, B+10's and B+20's (a clock without a trade counts 0); its mean
  and its standard deviation beside B's.
- **Beside BF:** every 15 minutes; every 5 minutes. **Beside BT:** two
  changes in a row; four; a wait of 10 minutes.

## 4. The bar

**A session's result** x is a rule's net basis points of that session
in B's sizing, 0 on a session without a trade, over the sessions on
which B has its bounds and its volatility.

**BS.** B+10 and B+20 are each judged by wave twenty-four's bar on each
of NQ (the ten years: a screen), ES and RTY.

| verdict | when |
| --- | --- |
| ROBUST | both pass on NQ, and both pass on each of ES and RTY on which B itself passes |
| FRAGILE | neither passes on NQ |
| MIXED | anything else |

ROBUST counts for B. FRAGILE counts against it: B's pass then rests on
its clock, and no later file raises B's size on the strength of the NQ
result alone.

**BF and BT.** D = the change's x minus B's x, session by session. A
change is **BETTER THAN B** when all of these hold:

- it passes wave twenty-four's bar on each of NQ, ES and RTY;
- the mean of D is above 0 on ES and above 0 on RTY; and
- over ES and RTY together (a session's D is the average of the two
  markets that have it; weeks are ISO weeks) the mean of D is above 0
  with a **weekly t of 2.5 or more**.

Otherwise it is **NOT BETTER**: B stays as it is, and no variant of the
change is tried on these bars. In NQ's later months (2026-07-01 to
2026-11-13) a change must not be COLLAPSED (wave twenty-five's
verdicts).

Two changes are judged. With that bar, when neither changes anything, a
false pass is expected in about one such study in eighty.

**What goes on.** A change that is better than B takes B's place in
every later step, **but only if B itself passes wave twenty-five**. If
both are better, each goes on alone; putting them together is a later
file.

## 5. Reads

- NQ's ten years (already read), ES and RTY (wave twenty-five's 2a
  exports), read by this wave's own command, each **once**. The operator
  may make them in the same sitting as waves twenty-five and twenty-six.
- NQ's later months, 2026-07-01 to 2026-11-13: B+10, B+20, BF and BT
  read **once** by this wave, recorded before any result is shown.
- Sessions from 2026-11-16 are never read.

## Explicitly NOT registered

- other clocks, other numbers of changes or other waits as judged
  rules; BT on BF; any change to B's bounds, its VWAP condition or its
  sizing
- A on other opening ranges; a fast rule traded alone
- markets other than NQ, ES and RTY
- order flow: the recordings are not opened
- sizes on a prop account: a later file
- live, paper or simulated order placement

## Expected beforehand (written 2026-11-27, before anything was computed)

After three five-minute changes one way the next gives back a little:
on NQ a fraction of a point on average, less than the 0.50-point round
trip, so a trade on it alone loses. **BS:** ROBUST, about two chances in
three; FRAGILE about one in ten. **BF:** more orders and more cost for
about the same moves; better than B, about one chance in eight. **BT:**
better than B, about one chance in five; the published gain is on SPY,
on the bars it was built on, and B's fills are few. The most likely
outcome: B does not hang on its clock, and neither change is worth
making.
