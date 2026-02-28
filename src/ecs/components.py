from ecs.core import Component
from typing import Dict, Any, Optional

class GitLabEventComponent(Component):
    """Component to hold the raw webhook payload from GitLab."""
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.processed = False

class IssueComponent(Component):
    """Component representing a parsed GitLab Issue."""
    def __init__(self, issue_id: int, project_id: int, title: str, description: str, state: str):
        self.issue_id = issue_id
        self.project_id = project_id
        self.title = title
        self.description = description
        self.state = state

class MergeRequestComponent(Component):
    """Component representing a parsed GitLab Merge Request."""
    def __init__(self, mr_id: int, project_id: int, title: str, description: str, source_branch: str, target_branch: str, state: str, author_id: int):
        self.mr_id = mr_id
        self.project_id = project_id
        self.title = title
        self.description = description
        self.source_branch = source_branch
        self.target_branch = target_branch
        self.state = state
        self.author_id = author_id

class PipelineStatusComponent(Component):
    """Component representing the CI/CD pipeline status of an MR or branch."""
    def __init__(self, status: str, ref: str, web_url: str):
        self.status = status
        self.ref = ref
        self.web_url = web_url

class AgentAnalysisComponent(Component):
    """Component storing the result of an AI agent's analysis."""
    def __init__(self, analysis_result: str):
        self.analysis_result = analysis_result
        self.action_taken = False

