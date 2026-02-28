from pydantic import BaseModel
from typing import Dict, Any, Optional

class GitLabEventPayload(BaseModel):
    object_kind: str
    event_type: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    project: Optional[Dict[str, Any]] = None
    object_attributes: Optional[Dict[str, Any]] = None
    repository: Optional[Dict[str, Any]] = None
    # Add other common GitLab Webhook payload fields as needed mapping appropriately.
    # We will expand this as we intercept specific events.

    class Config:
        extra = "allow" # Allow extra fields so we don't crash on unmapped gitlab fields
