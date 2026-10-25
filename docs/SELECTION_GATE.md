# LAND RADAR — 30 → 10 Evidence Gate

## Why a gate exists

LAND RADAR does not narrow Top-30 candidates to Top-10 merely because a cell
has strong historical growth.

Before a Top-10 review can begin, each candidate must have the required
evidence layers.

Default required layers:

- urban history,
- terrain,
- hazard,
- catalyst,
- Sentinel recent-change evidence,
- planning/legal,
- price.

## Run

Codespaces:

```bash
bash TOP10_GATE.sh
```

or:

```bash
python scripts/selection_gate.py --target 10
```

## What the gate does

For every candidate it checks:

- funnel status is not DROP,
- no explicit hard veto exists,
- every required evidence layer is known.

It outputs:

```
eligible_for_top10_review
missing_required_layers
blockers
evidence_coverage_pct
```

## What it does not do

The gate does not:

- calculate an Opportunity Score,
- rank investments,
- automatically choose the best ten,
- ignore a missing planning or price layer because growth looks strong.

If fewer than ten candidates have complete required evidence:

```
selection_ready = false
```

The correct next action is to fill the missing evidence, not weaken the gate.

## Current expected bottleneck

At v0.16, `planning_legal` remains incomplete until the separate e-Plan /
active-zoning channel is verified.

Protected-area screening alone is not sufficient to declare planning/legal
evidence complete.

This is intentional.
