from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AlertType(StrEnum):
    wash_trade = "wash_trade"
    spoofing = "spoofing"


class AlertStatus(StrEnum):
    open = "open"
    investigating = "investigating"
    dismissed = "dismissed"
    confirmed = "confirmed"


class AlertSummary(BaseModel):
    alert_id: str
    alert_type: AlertType
    status: AlertStatus
    severity: Literal["low", "medium", "high", "critical"]
    detected_at: datetime
    symbol: str
    trader_ref: str = Field(description="Stable pseudonymous reference; never a name or account ID")
    risk_score: float = Field(ge=0, le=100)
    evidence_count: int = Field(ge=0)


class AlertDetail(AlertSummary):
    window_start: datetime
    window_end: datetime
    notional_value: float = Field(ge=0)
    order_count: int = Field(ge=0)
    rationale: str
    evidence_refs: list[str] = Field(description="Redacted event references, not raw PII")


class TraderRisk(BaseModel):
    as_of: date
    trader_ref: str
    alert_count: int = Field(ge=0)
    confirmed_count: int = Field(ge=0)
    total_notional: float = Field(ge=0)
    max_risk_score: float = Field(ge=0, le=100)
    risk_band: Literal["low", "medium", "high", "critical"]


class AuditEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    actor_ref: str = Field(description="Pseudonymous operator reference")
    action: str
    resource_type: str
    resource_id: str
    outcome: Literal["success", "denied", "failure"]
    metadata: dict[str, str] = Field(default_factory=dict)
