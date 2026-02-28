"""
GitLab Duo Agent Platform — Trigger Definitions

Triggers map incoming GitLab events to specific tool invocations and context.
This follows the Duo Agent Platform pattern where agents are activated by:
  - Webhook events (issue opened, MR created, pipeline status change)
  - @mentions in comments
  - Scheduled intervals

Each trigger defines:
  - which event types it responds to
  - which tools to invoke
  - how to build the context
"""

import logging
from typing import Dict, Any, List, Optional
from agent.tools import DuoTool, AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


class DuoTrigger:
    """Base class for Duo Agent Platform triggers."""
    name: str = "base_trigger"
    description: str = "Base trigger"
    event_types: List[str] = []

    def matches(self, event_payload: Dict[str, Any]) -> bool:
        """Check if this trigger should fire for the given event."""
        object_kind = event_payload.get("object_kind", "")
        return object_kind in self.event_types

    def get_tools(self) -> List[DuoTool]:
        """Return the tools this trigger should invoke."""
        raise NotImplementedError

    def build_tool_context(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the relevant context dict from the event payload for tool execution."""
        raise NotImplementedError


class IssueTrigger(DuoTrigger):
    """
    Fires when a GitLab Issue webhook event is received.
    Invokes: TriageIssueTool + SecurityScanTool
    """
    name = "issue_trigger"
    description = "Triggered by GitLab Issue events (opened, updated, closed)"
    event_types = ["issue"]

    def get_tools(self) -> List[DuoTool]:
        tools = [AVAILABLE_TOOLS["triage_issue"]]
        return tools

    def get_secondary_tools(self, context: Dict[str, Any]) -> List[DuoTool]:
        """Conditionally add security scan if keywords detected."""
        title = context.get("title", "").lower()
        desc = context.get("description", "").lower()
        combined = f"{title} {desc}"
        
        secondary = []
        if any(kw in combined for kw in ["security", "token", "secret", "vulnerability", "cve", "credential"]):
            secondary.append(AVAILABLE_TOOLS["security_scan"])
        return secondary

    def build_tool_context(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        attrs = event_payload.get("object_attributes", {})
        project = event_payload.get("project", {})
        return {
            "title": attrs.get("title", ""),
            "description": attrs.get("description", ""),
            "project_id": project.get("id", 0),
            "project_name": project.get("name", "unknown"),
            "issue_id": attrs.get("id", 0),
            "state": attrs.get("state", ""),
            "event_type": "issue"
        }


class MergeRequestTrigger(DuoTrigger):
    """
    Fires when a GitLab Merge Request webhook event is received.
    Invokes: ReviewMergeRequestTool + SecurityScanTool (conditional)
    """
    name = "merge_request_trigger"
    description = "Triggered by GitLab Merge Request events (opened, updated, merged)"
    event_types = ["merge_request"]

    def get_tools(self) -> List[DuoTool]:
        return [AVAILABLE_TOOLS["review_merge_request"]]

    def get_secondary_tools(self, context: Dict[str, Any]) -> List[DuoTool]:
        """Conditionally add security scan for dependency/security MRs."""
        title = context.get("title", "").lower()
        desc = context.get("description", "").lower()
        combined = f"{title} {desc}"
        
        secondary = []
        if any(kw in combined for kw in ["security", "dependency", "cve", "vulnerability"]):
            secondary.append(AVAILABLE_TOOLS["security_scan"])
        return secondary

    def build_tool_context(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        attrs = event_payload.get("object_attributes", {})
        project = event_payload.get("project", {})
        return {
            "title": attrs.get("title", ""),
            "description": attrs.get("description", ""),
            "source_branch": attrs.get("source_branch", ""),
            "target_branch": attrs.get("target_branch", ""),
            "project_id": project.get("id", 0),
            "project_name": project.get("name", "unknown"),
            "mr_id": attrs.get("id", 0),
            "state": attrs.get("state", ""),
            "author_id": attrs.get("author_id", 0),
            "event_type": "merge_request"
        }


class PipelineTrigger(DuoTrigger):
    """
    Fires when a GitLab Pipeline webhook event is received.
    Invokes: PipelineAnalysisTool
    """
    name = "pipeline_trigger"
    description = "Triggered by GitLab CI/CD Pipeline status changes"
    event_types = ["pipeline"]

    def get_tools(self) -> List[DuoTool]:
        return [AVAILABLE_TOOLS["pipeline_analysis"]]

    def get_secondary_tools(self, context: Dict[str, Any]) -> List[DuoTool]:
        return []

    def build_tool_context(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        attrs = event_payload.get("object_attributes", {})
        project = event_payload.get("project", {})
        return {
            "status": attrs.get("status", ""),
            "ref": attrs.get("ref", ""),
            "pipeline_id": attrs.get("id", 0),
            "project_id": project.get("id", 0),
            "project_name": project.get("name", "unknown"),
            "event_type": "pipeline"
        }


# Registry of all available triggers
AVAILABLE_TRIGGERS: List[DuoTrigger] = [
    IssueTrigger(),
    MergeRequestTrigger(),
    PipelineTrigger(),
]


def match_trigger(event_payload: Dict[str, Any]) -> Optional[DuoTrigger]:
    """Find the first trigger that matches the incoming event."""
    for trigger in AVAILABLE_TRIGGERS:
        if trigger.matches(event_payload):
            logger.info(f"Matched trigger: {trigger.name} for event: {event_payload.get('object_kind')}")
            return trigger
    logger.warning(f"No trigger matched for event: {event_payload.get('object_kind')}")
    return None
