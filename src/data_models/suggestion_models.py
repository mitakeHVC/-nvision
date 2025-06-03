from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import uuid # For generating default IDs if needed

class Suggestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the suggestion")
    title: str = Field(..., description="Short title for the suggestion")
    description: str = Field(..., description="Detailed description of the suggestion/insight")
    source_analysis_type: str = Field(..., description="Type of analysis that triggered this suggestion (e.g., 'sales_trend', 'customer_segment_performance')")
    severity: Optional[str] = Field(None, description="Severity or priority (e.g., 'high', 'medium', 'low')")
    related_data_points: Optional[List[Dict[str, Any]]] = Field(None, description="Key data points supporting the suggestion")
    potential_impact: Optional[str] = Field(None, description="Potential positive impact if addressed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by_user_id: Optional[str] = None # Added for consistency with repo layer

    model_config = ConfigDict(populate_by_name=True)

class ActionPlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the step")
    description: str = Field(..., description="Description of the action to take")
    responsible_area: Optional[str] = Field(None, description="Team/area responsible (e.g., 'Marketing', 'Sales')")
    estimated_effort: Optional[str] = Field(None, description="e.g., 'low', 'medium', 'high'")
    status: str = Field("pending", description="e.g., 'pending', 'in_progress', 'completed', 'deferred'")

    model_config = ConfigDict(populate_by_name=True)

class ActionPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the action plan")
    suggestion_id: str = Field(..., description="ID of the suggestion this plan addresses")
    title: str = Field(..., description="Title of the action plan")
    overview: str = Field(..., description="Brief overview of the plan")
    steps: List[ActionPlanStep] = Field(default_factory=list)
    overall_status: str = Field("pending", description="e.g., 'pending', 'in_progress', 'completed'")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by_user_id: Optional[str] = None # Added for consistency
    updated_by_user_id: Optional[str] = None # Added for consistency

    model_config = ConfigDict(populate_by_name=True)

class SuggestionWithActionPlan(BaseModel):
    suggestion: Suggestion
    action_plan: Optional[ActionPlan] = None

    model_config = ConfigDict(populate_by_name=True)
