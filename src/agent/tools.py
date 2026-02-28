"""
GitLab Duo Agent Platform — Tool Definitions

Tools represent the callable actions available to the Ghost Engine agent.
Each tool follows the GitLab Duo Agent Platform specification:
  - name: Unique identifier
  - description: Human-readable purpose
  - parameters: Expected input schema
  - execute(): Async method that produces an analysis string

These tools are registered with the DuoAgentPlatform and selected by
Triggers based on the incoming event type.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result returned by a Duo Tool execution."""
    tool_name: str
    output: str
    severity: Optional[str] = None
    category: Optional[str] = None
    recommended_actions: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)


class DuoTool:
    """Base class for all Duo Agent Platform tools."""
    name: str = "base_tool"
    description: str = "Base tool"
    parameters: Dict[str, str] = {}

    async def execute(self, context: Dict[str, Any], ai_response: str) -> ToolResult:
        raise NotImplementedError


class TriageIssueTool(DuoTool):
    """
    Categorizes GitLab issues by severity and type, recommends labels,
    and provides actionable triage commentary.
    
    Duo Platform Role: Primary tool for Issue triggers.
    """
    name = "triage_issue"
    description = "Analyzes a GitLab issue to determine severity, category, and recommended actions"
    parameters = {
        "title": "Issue title",
        "description": "Issue description body",
        "project_id": "GitLab project ID",
        "issue_id": "Issue IID"
    }

    async def execute(self, context: Dict[str, Any], ai_response: str) -> ToolResult:
        title = context.get("title", "").lower()
        
        # Determine severity based on AI analysis and title heuristics
        severity = "Medium"
        category = "General"
        labels = ["triage::needs-review"]
        
        if any(kw in title for kw in ["security", "vulnerability", "token", "secret", "cve"]):
            severity = "Critical"
            category = "Security Vulnerability"
            labels = ["priority::critical", "type::security", "triage::urgent"]
        elif any(kw in title for kw in ["bug", "crash", "error", "fail", "broken"]):
            severity = "High" if "crash" in title else "Medium"
            category = "Bug"
            labels = ["type::bug", "triage::needs-fix"]
        elif any(kw in title for kw in ["feature", "enhancement", "request", "add"]):
            severity = "Low"
            category = "Feature Request"
            labels = ["type::feature", "triage::backlog"]
        elif any(kw in title for kw in ["docs", "documentation", "readme", "typo"]):
            severity = "Low"
            category = "Documentation"
            labels = ["type::docs", "triage::good-first-issue"]

        recommended_actions = []
        if severity == "Critical":
            recommended_actions = [
                "Immediately assess exposure scope",
                "Rotate any compromised credentials",
                "Apply remediation steps from analysis",
                "Post triage comment with remediation plan"
            ]
        elif category == "Bug":
            recommended_actions = [
                "Reproduce the issue locally",
                "Check for related open issues",
                "Post triage comment with initial analysis"
            ]
        else:
            recommended_actions = [
                "Review for feasibility and alignment",
                "Post triage comment with initial assessment"
            ]

        return ToolResult(
            tool_name=self.name,
            output=ai_response,
            severity=severity,
            category=category,
            recommended_actions=recommended_actions,
            labels=labels
        )


class ReviewMergeRequestTool(DuoTool):
    """
    Analyzes merge request descriptions and recommends approval or changes.
    
    Duo Platform Role: Primary tool for MergeRequest triggers.
    """
    name = "review_merge_request"
    description = "Reviews a GitLab merge request for code quality, potential issues, and approval readiness"
    parameters = {
        "title": "MR title",
        "description": "MR description body",
        "source_branch": "Source branch name",
        "target_branch": "Target branch name",
        "project_id": "GitLab project ID",
        "mr_id": "Merge request IID"
    }

    async def execute(self, context: Dict[str, Any], ai_response: str) -> ToolResult:
        title = context.get("title", "").lower()
        source_branch = context.get("source_branch", "")
        
        category = "Code Review"
        severity = "Medium"
        labels = ["review::pending"]
        
        if any(kw in title for kw in ["fix", "hotfix", "patch", "bug"]):
            category = "Bug Fix"
            labels = ["type::bug-fix", "review::priority"]
        elif any(kw in title for kw in ["chore", "dependency", "update", "bump"]):
            category = "Dependency Update"
            labels = ["type::chore", "review::automated"]
        elif any(kw in title for kw in ["feat", "feature", "add"]):
            category = "Feature"
            labels = ["type::feature", "review::needs-discussion"]
        elif any(kw in title for kw in ["refactor", "cleanup", "reorganize"]):
            category = "Refactor"
            labels = ["type::refactor", "review::standard"]

        recommended_actions = [
            "Review code changes for correctness",
            "Verify tests pass in CI pipeline",
            f"Check branch naming convention: {source_branch}",
            "Post review comment with findings"
        ]

        return ToolResult(
            tool_name=self.name,
            output=ai_response,
            severity=severity,
            category=category,
            recommended_actions=recommended_actions,
            labels=labels
        )


class SecurityScanTool(DuoTool):
    """
    Scans issues and MRs for security concerns such as hardcoded tokens,
    dependency vulnerabilities, and insecure patterns.
    
    Duo Platform Role: Secondary tool invoked alongside triage/review
    when security keywords are detected.
    """
    name = "security_scan"
    description = "Scans GitLab events for security vulnerabilities, credential leaks, and insecure patterns"
    parameters = {
        "title": "Event title",
        "description": "Event description body",
        "event_type": "Type of event (issue/mr)"
    }

    async def execute(self, context: Dict[str, Any], ai_response: str) -> ToolResult:
        description = context.get("description", "").lower()
        title = context.get("title", "").lower()
        combined = f"{title} {description}"
        
        findings = []
        severity = "Low"
        
        if any(kw in combined for kw in ["token", "api_key", "secret", "password", "credential"]):
            findings.append("Potential credential exposure detected")
            severity = "Critical"
        if any(kw in combined for kw in ["cve", "vulnerability", "exploit"]):
            findings.append("Known vulnerability reference found")
            severity = "Critical"
        if any(kw in combined for kw in ["http://", "ftp://"]):
            findings.append("Insecure protocol usage detected")
            severity = "High" if severity != "Critical" else severity
        if any(kw in combined for kw in ["eval(", "exec(", "subprocess", "os.system"]):
            findings.append("Potentially dangerous code execution pattern")
            severity = "High" if severity != "Critical" else severity

        if not findings:
            findings.append("No immediate security concerns detected")

        return ToolResult(
            tool_name=self.name,
            output=ai_response,
            severity=severity,
            category="Security Scan",
            recommended_actions=findings,
            labels=["security::scanned"] if severity == "Low" else ["security::alert", "priority::critical"]
        )


class PipelineAnalysisTool(DuoTool):
    """
    Analyzes CI/CD pipeline status and recommends actions for failures.
    
    Duo Platform Role: Primary tool for Pipeline triggers.
    """
    name = "pipeline_analysis"
    description = "Analyzes CI/CD pipeline results and recommends actions for failures or optimizations"
    parameters = {
        "status": "Pipeline status (success/failed/running)",
        "ref": "Branch reference",
        "pipeline_id": "Pipeline ID"
    }

    async def execute(self, context: Dict[str, Any], ai_response: str) -> ToolResult:
        status = context.get("status", "unknown")
        ref = context.get("ref", "unknown")
        
        if status == "failed":
            severity = "High"
            category = "Pipeline Failure"
            recommended_actions = [
                f"Investigate failed pipeline on branch: {ref}",
                "Check job logs for error details",
                "Verify dependency versions are compatible",
                "Re-run pipeline if failure appears transient"
            ]
            labels = ["pipeline::failed", "priority::high"]
        elif status == "success":
            severity = "Info"
            category = "Pipeline Success"
            recommended_actions = [
                f"Pipeline passed on {ref} — ready for merge review"
            ]
            labels = ["pipeline::passed"]
        else:
            severity = "Info"
            category = "Pipeline Running"
            recommended_actions = [
                f"Pipeline in progress on {ref} — monitoring"
            ]
            labels = ["pipeline::running"]

        return ToolResult(
            tool_name=self.name,
            output=ai_response or f"Pipeline {status} on {ref}",
            severity=severity,
            category=category,
            recommended_actions=recommended_actions,
            labels=labels
        )


# Registry of all available Duo tools
AVAILABLE_TOOLS: Dict[str, DuoTool] = {
    "triage_issue": TriageIssueTool(),
    "review_merge_request": ReviewMergeRequestTool(),
    "security_scan": SecurityScanTool(),
    "pipeline_analysis": PipelineAnalysisTool(),
}
