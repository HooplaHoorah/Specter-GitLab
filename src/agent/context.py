"""
GitLab Duo Agent Platform — Context Builder

Context provides the AI agent with rich, structured information about the
GitLab environment so it can make informed decisions. This follows the
Duo Agent Platform's three context tiers:

1. Always-available context: Project metadata, language, default branch
2. Location-based context: The specific issue, MR, or pipeline being processed
3. Explicitly-referenced context: Related issues, MRs, or external resources
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Always-available context about the GitLab project."""
    project_id: int
    project_name: str
    default_branch: str = "main"
    language: str = "Python"
    url: str = ""
    description: str = ""


@dataclass  
class IssueContext:
    """Location-based context for a specific Issue."""
    issue_id: int
    project_id: int
    title: str
    description: str
    state: str
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)
    related_mrs: List[int] = field(default_factory=list)


@dataclass
class MergeRequestContext:
    """Location-based context for a specific Merge Request."""
    mr_id: int
    project_id: int
    title: str
    description: str
    source_branch: str
    target_branch: str
    state: str
    author_id: int
    diff_summary: str = ""
    related_issues: List[int] = field(default_factory=list)


@dataclass
class PipelineContext:
    """Location-based context for a specific Pipeline run."""
    pipeline_id: int = 0
    project_id: int = 0
    status: str = ""
    ref: str = ""
    web_url: str = ""
    stages: List[str] = field(default_factory=list)
    failure_reason: str = ""


@dataclass
class DuoContext:
    """
    Aggregated context object passed to the AI agent.
    Combines project-level, event-level, and reference-level context
    following the Duo Agent Platform context model.
    """
    project: ProjectContext
    issue: Optional[IssueContext] = None
    merge_request: Optional[MergeRequestContext] = None
    pipeline: Optional[PipelineContext] = None
    references: List[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Serialize context into a structured prompt section for the AI model."""
        sections = []
        
        # Project context (always available)
        sections.append(
            f"PROJECT CONTEXT:\n"
            f"  Name: {self.project.project_name}\n"
            f"  ID: {self.project.project_id}\n"
            f"  Language: {self.project.language}\n"
            f"  Default Branch: {self.project.default_branch}"
        )
        
        # Event-specific context
        if self.issue:
            sections.append(
                f"ISSUE CONTEXT:\n"
                f"  Issue #{self.issue.issue_id}: {self.issue.title}\n"
                f"  State: {self.issue.state}\n"
                f"  Description: {self.issue.description}"
            )
            if self.issue.labels:
                sections.append(f"  Labels: {', '.join(self.issue.labels)}")
                
        if self.merge_request:
            sections.append(
                f"MERGE REQUEST CONTEXT:\n"
                f"  MR !{self.merge_request.mr_id}: {self.merge_request.title}\n"
                f"  State: {self.merge_request.state}\n"
                f"  Branches: {self.merge_request.source_branch} → {self.merge_request.target_branch}\n"
                f"  Description: {self.merge_request.description}"
            )
            
        if self.pipeline:
            sections.append(
                f"PIPELINE CONTEXT:\n"
                f"  Status: {self.pipeline.status}\n"
                f"  Branch: {self.pipeline.ref}"
            )
            if self.pipeline.failure_reason:
                sections.append(f"  Failure Reason: {self.pipeline.failure_reason}")
        
        # References
        if self.references:
            sections.append(
                f"REFERENCED CONTEXT:\n  " + "\n  ".join(self.references)
            )
        
        return "\n\n".join(sections)


class ContextBuilder:
    """
    Factory for constructing DuoContext objects from ECS components.
    Maps the Ghost Engine ECS data model to the Duo Agent Platform context model.
    """
    
    @staticmethod
    def from_issue(project_id: int, project_name: str,
                   issue_id: int, title: str, description: str, state: str) -> DuoContext:
        """Build context for an Issue event."""
        return DuoContext(
            project=ProjectContext(
                project_id=project_id,
                project_name=project_name
            ),
            issue=IssueContext(
                issue_id=issue_id,
                project_id=project_id,
                title=title,
                description=description,
                state=state
            )
        )
    
    @staticmethod
    def from_merge_request(project_id: int, project_name: str,
                           mr_id: int, title: str, description: str,
                           source_branch: str, target_branch: str,
                           state: str, author_id: int) -> DuoContext:
        """Build context for a Merge Request event."""
        return DuoContext(
            project=ProjectContext(
                project_id=project_id,
                project_name=project_name
            ),
            merge_request=MergeRequestContext(
                mr_id=mr_id,
                project_id=project_id,
                title=title,
                description=description,
                source_branch=source_branch,
                target_branch=target_branch,
                state=state,
                author_id=author_id
            )
        )
    
    @staticmethod
    def from_pipeline(project_id: int, project_name: str,
                      status: str, ref: str, web_url: str = "") -> DuoContext:
        """Build context for a Pipeline event."""
        return DuoContext(
            project=ProjectContext(
                project_id=project_id,
                project_name=project_name
            ),
            pipeline=PipelineContext(
                project_id=project_id,
                status=status,
                ref=ref,
                web_url=web_url
            )
        )
