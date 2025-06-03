from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import uuid

class MetricValue(BaseModel):
    metric_name: str
    value: Any  # Could be float, int, str
    unit: Optional[str] = None  # e.g., "%", "USD", "count"
    change_from_baseline: Optional[float] = None  # e.g., percentage change
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class EffectivenessReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the report")
    report_title: str
    action_plan_id: str = Field(..., description="ID of the action plan being evaluated")
    action_plan_title: str  # For context in the report
    reporting_period_start: datetime
    reporting_period_end: datetime
    baseline_period_start: Optional[datetime] = None  # If comparing to a baseline
    baseline_period_end: Optional[datetime] = None
    key_metrics: List[MetricValue] = Field(default_factory=list)
    summary: str = Field(..., description="Overall summary of effectiveness")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: Optional[str] = None  # User ID or system

    model_config = ConfigDict(populate_by_name=True)
