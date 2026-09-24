# Trading Signal Center — Signal-First Specification

## Product mode

- The application is a research and signal engine.
- It does not place live BUY/SELL orders.
- The user decides independently whether to execute a signal in their own broker or exchange.
- `liveExecution=false` remains unchanged.
- Model score is a confidence/ranking score, not a guaranteed probability of profit.

## Signal gate

A trade opportunity is shown only when the model score is at least **95/100**.

The engine evaluates both directions:
- LONG
- SHORT

Signals below 95 are shown as **NO TRADE**.

## Per-trade risk

Every signal uses a hard adverse-move stop of **5% from entry**.

- LONG: stop = entry × 0.95
- SHORT: stop = entry × 1.05

This is a model stop level. Real execution can exceed it because of gaps, slippage, liquidity, latency or exchange conditions.

## Profit target

Target range: **5% to 10%** from entry.

Within the 95–100 score band the target scales from 5% toward 10%.

- LONG target is above entry.
- SHORT target is below entry.

## Portfolio loss reference

The product may track a **10% monthly portfolio loss threshold** as a risk warning / lockout rule in simulated or future regulated execution modes.

The 5% rule is per individual trade, not a daily account loss rule.

## Signal explanation

Each signal exposes:
- symbol
- direction
- model score
- entry
- 5% stop
- 5–10% target
- risk/reward
- long score vs short score
- price vs SMA50
- 20-day momentum
- recent volume ratio
- RSI
- timestamp / market-data context

## Plans

### Demo — €0/month
- limited watchlist
- manual scans
- paper/research workflow

### Starter — €10.01/month
- larger watchlist
- scheduled scans
- more scan history and usage

### Pro — €30/month
- largest watchlist
- scheduled scans
- higher usage and history limits
- exports

Pricing does not imply or guarantee investment performance.

## Next implementation block

1. Real-time event/news ingestion from permitted data sources.
2. Event classification: earnings, guidance, filings, regulatory, macro, exchange notices and material company announcements.
3. Separate event score from technical score.
4. Signal release only after required technical + event/data-quality gates pass.
5. Forward-test ledger measuring whether 95+ signals actually hit target before stop.
6. Read-only portfolio import can be added only with a clear regulatory perimeter review before commercial personalized recommendations.
