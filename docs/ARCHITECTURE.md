# LAND RADAR architecture

## 1. Research funnel

```
Türkiye / macro scan
        ↓
economic corridor
        ↓
coarse grid (5–10 km)
        ↓
fine grid (1–2 km)
        ↓
micro area (~250 m)
        ↓
parcel due diligence
```

V0.1 starts at the corridor/grid level. Parcel boundaries are intentionally out of scope.

## 2. Three-layer decision model

### Hard filters

A hard veto is not averaged away by a high growth score. Examples:

- critical legal restriction
- severe flood exposure
- severe landslide exposure
- no legal road access

### Transition thesis

Measures whether a place is physically and economically moving toward a new state:

- Urban Pressure
- Development Acceleration
- Catalyst Maturity
- Story Maturity
- Physical Quality

### Investment economics

Only calculated when reliable pricing exists:

- Mispricing
- Waiting Cost / required return
- Exit Demand
- Liquidity
- Data Confidence

## 3. Catalyst state machine

Future implementation should represent each catalyst with a stage instead of a binary flag:

0. no evidence / rumor
1. official strategy or intent
2. plan / approval
3. budget / tender
4. construction started
5. completed
6. measurable economic effect

Every stage change must carry source and date evidence.

## 4. Evidence schema

Every material claim should be able to retain:

- source
- claim
- observed date
- published date
- effective date
- URL/reference
- confidence

This is required for honest backtests.

## 5. Point-in-time backtest

When testing what LAND RADAR would have selected in 2015, the engine must not use information observed, published or effective after the cutoff. Avoiding future leakage is a core product requirement.

## 6. Pricing discipline

No price dataset → no Mispricing Score.

The price layer should ultimately distinguish:

- listing price
- realized transaction price, where legally/technically obtainable
- official assessed/rate data
- comparable median
- listing age
- price revisions
- nominal change
- real change
- relative change versus local housing/land benchmarks

## 7. AI boundary

LLMs may summarize evidence, create bull/bear narratives and explain model outputs. They must not invent catalysts, legal status, price observations or satellite changes.

**Data engine computes; AI explains.**
