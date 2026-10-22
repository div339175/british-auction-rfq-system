import json
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, field_validator


class ActivityLogResponse(BaseModel):
    id: str
    rfq_id: str
    event_type: str
    carrier_name: Optional[str] = None
    quote_id: Optional[str] = None
    previous_close_time: Optional[datetime] = None
    new_close_time: Optional[datetime] = None
    message: str
    metadata_json: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    @field_validator("metadata", mode="before")
    def parse_metadata(cls, v, info):
        if v is not None and isinstance(v, dict):
            return v
        # Try parsing metadata_json if provided
        data = info.data
        raw = data.get("metadata_json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    model_config = {"from_attributes": True}
