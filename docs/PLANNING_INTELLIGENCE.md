# LAND RADAR — Planning Intelligence

## Goal

Planning evidence must answer:

> Is there a dated, authoritative and spatially relevant plan record for this candidate?

LAND RADAR does not infer zoning from proximity, urban growth or map color.

## Official e-Plan entry points

Current public e-Plan service:

```
https://e-plan.gov.tr/
```

Public modules include:

```
https://e-plan.gov.tr/e-plan/html/acikPlanlar.html?filter=aski
https://e-plan.gov.tr/e-plan/html/imarDurumu.html
```

These pages are official public interfaces.

LAND RADAR v0.17 does not scrape undocumented browser-internal APIs behind those pages.

## Plan lifecycle

The registry supports:

```
PROPOSAL
SUBMITTED
APPROVED
ON_SUSPENSION
OBJECTION_REVIEW
FINALIZED
CANCELLED
```

The lifecycle follows the planning process represented in official e-Plan documentation.

## planning_known rule

A candidate receives:

```
planning_known = true
```

only when at least one matching plan record is:

1. point-in-time valid for the requested analysis date,
2. `FINALIZED`,
3. `UIP` or `NIP`,
4. spatially verified for the candidate.

Regional ÇDP/WMS coverage alone does not satisfy this rule.

## Verified public WMS context

The project includes a conservative registry of public TUCBS/ULASAV WMS endpoints
whose URLs are explicitly known.

Current entries include:

- Balıkesir-Çanakkale Çevre Düzeni Planı,
- Bilecik Çevre Düzeni Planı,
- Bolu Çevre Düzeni Planı.

This registry is intentionally incomplete.

A candidate outside known service bounds remains unknown.

## Importing official plan evidence

Create a CSV with these required columns:

```
plan_id
title
plan_type
stage
source
source_url
```

Recommended columns:

```
scale_denominator
published_date
decision_date
effective_date
suspension_start
suspension_end
observed_date
geometry_verified
cell_id
province
district
neighborhood
min_lon
min_lat
max_lon
max_lat
decision_no
pin
confidence
note
```

Example:

```csv
plan_id,title,plan_type,stage,source,source_url,scale_denominator,published_date,geometry_verified,cell_id
UIP-123456789,Örnek Kesinleşmiş Uygulama İmar Planı,UİP,kesinleşmiş,e-Plan,https://e-plan.gov.tr/,1000,2026-09-01,true,LR-001-001
```

Import:

```bash
python scripts/import_plan_evidence.py   --csv data/processed/plans.csv
```

Output:

```
data/processed/plan_registry.json
```

## Top-30 planning scan

```bash
bash PLAN_KANIT_TOP30.sh
```

or:

```bash
python scripts/planning_scan.py --as-of 2026-10-25
```

Outputs:

```
data/output/planning_scan/planning_top30.csv
data/output/planning_scan/planning_scan_summary.json
```

## Point-in-time discipline

A plan published after the analysis cutoff is excluded.

This is mandatory for historical backtests.

A current finalized plan must never be leaked into a historical candidate analysis.

## Evidence Packet integration

After planning scan:

```bash
python scripts/build_evidence_packets.py
```

The packet gains:

```
planning_legal.eplan.checked
planning_legal.eplan.planning_known
planning_legal.eplan.cdp_wms_covered
planning_legal.eplan.registry_match_count
planning_legal.eplan.finalized_uip_nip_verified_count
planning_legal.eplan.matched_plan_ids
planning_legal.eplan.matched_plan_stages
```

If the verified final UIP/NIP rule is satisfied:

```
planning_legal.known = true
```

Otherwise it stays false.

## 30 → 10 Gate

Finally:

```bash
bash TOP10_GATE.sh
```

Planning evidence can now genuinely satisfy the planning/legal gate.

The gate still does not rank investments.
