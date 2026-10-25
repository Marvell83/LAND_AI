from datetime import date

import pytest

from land_radar.models import Evidence
from land_radar.risk import (
    RiskFinding,
    RiskSeverity,
    summarize_risks,
    to_legacy_hard_flags,
)


def _evidence():
    return Evidence(
        source="official hazard source",
        claim="risk finding",
        published_date=date(2026, 1, 1),
        confidence=90,
    )


def test_nonzero_risk_requires_evidence():
    finding = RiskFinding(
        category="flood",
        severity=RiskSeverity.HIGH,
    )
    with pytest.raises(ValueError):
        finding.validate()


def test_high_risk_is_not_automatically_hard_veto():
    finding = RiskFinding(
        category="flood",
        severity=RiskSeverity.HIGH,
        hard_veto=False,
        evidence=[_evidence()],
    )
    summary = summarize_risks([finding])
    assert summary.hard_veto is False
    assert summary.max_severity == RiskSeverity.HIGH


def test_explicit_hard_veto_bridges_to_scoring_flags():
    finding = RiskFinding(
        category="no_legal_access",
        severity=RiskSeverity.CRITICAL,
        hard_veto=True,
        evidence=[_evidence()],
    )
    summary = summarize_risks([finding])
    flags = to_legacy_hard_flags([finding])

    assert summary.hard_veto is True
    assert summary.hard_veto_categories == ("no_legal_access",)
    assert flags.no_legal_access is True
