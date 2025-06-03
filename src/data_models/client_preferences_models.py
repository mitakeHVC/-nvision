from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ClientPreferenceBase(BaseModel):
    preferences_payload: Dict[str, Any] = Field(..., description="Diverse client input preferences.")
    client_id: str = Field(..., description="Identifier for the client.")


class ClientPreferenceCreate(ClientPreferenceBase):
    pass


class ClientPreferenceUpdate(BaseModel):
    preferences_payload: Optional[Dict[str, Any]] = None


class ClientPreference(ClientPreferenceBase):
    id: str = Field(..., description="Unique identifier for the preference set.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        # For MongoDB or similar, allow population by field name
        allow_population_by_field_name = True
        # Example of what preferences_payload might contain:
        # {
        #     "key_metrics": ["sales_total", "customer_churn_rate"],
        #     "target_areas": ["increase_engagement", "reduce_inventory_cost"],
        #     "industry_type": "retail",
        #     "dashboard_customizations": {"theme": "dark", "widgets": ["kpi_summary", "sales_trend"]}
        # }
