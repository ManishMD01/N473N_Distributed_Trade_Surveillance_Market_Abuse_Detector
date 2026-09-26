from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import AlertDetail, AlertStatus, AlertSummary, AuditEvent, TraderRisk

router = APIRouter(tags=["compliance"])

# Replace these fixtures with repository calls. They intentionally contain only
# pseudonymous references and aggregate evidence.
_ALERTS: dict[str, AlertDetail] = {}


@router.get("/alerts", response_model=list[AlertSummary])
def list_alerts(
    status: AlertStatus | None = None,
    alert_type: str | None = None,
    symbol: str | None = None,
    since: datetime | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[AlertSummary]:
    """Return redacted alerts with bounded pagination/filter parameters."""
    alerts = list(_ALERTS.values())
    if status:
        alerts = [a for a in alerts if a.status == status]
    if alert_type:
        alerts = [a for a in alerts if a.alert_type == alert_type]
    if symbol:
        alerts = [a for a in alerts if a.symbol == symbol.upper()]
    if since:
        alerts = [a for a in alerts if a.detected_at >= since]
    return [AlertSummary.model_validate(a) for a in alerts[:limit]]


@router.get("/alerts/{alert_id}", response_model=AlertDetail)
def get_alert(alert_id: str) -> AlertDetail:
    alert = _ALERTS.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/risk/daily", response_model=list[TraderRisk])
def daily_risk(
    as_of: date | None = None,
    trader_ref: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[TraderRisk]:
    """Expose aggregates only; identity resolution belongs in a restricted system."""
    target = as_of or datetime.now(timezone.utc).date()
    risks: list[TraderRisk] = []
    for alert in _ALERTS.values():
        if alert.detected_at.date() != target or (trader_ref and alert.trader_ref != trader_ref):
            continue
        risks.append(TraderRisk(
            as_of=target, trader_ref=alert.trader_ref, alert_count=1,
            confirmed_count=int(alert.status == AlertStatus.confirmed),
            total_notional=alert.notional_value, max_risk_score=alert.risk_score,
            risk_band=alert.severity,
        ))
    return risks[:limit]


@router.get("/audit", response_model=list[AuditEvent])
def audit_log(
    resource_id: str | None = None,
    since: datetime | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[AuditEvent]:
    """Return access/change events; raw request payloads and PII are excluded."""
    return []
