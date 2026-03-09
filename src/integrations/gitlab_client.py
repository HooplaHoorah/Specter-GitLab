import os
import httpx
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class GitLabClient:
    """
    Client for interacting with the GitLab REST and GraphQL APIs.
    Allows the agent to take concrete actions on the repository.
    """
    def __init__(self):
        self.gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com").rstrip('/')
        self.api_token = os.getenv("GITLAB_TOKEN")
        self.api_url = f"{self.gitlab_url}/api/v4"
        
        if not self.api_token:
            logger.warning("GITLAB_TOKEN is not set. GitLabClient will operate in mock mode.")
            
    def _headers(self) -> Dict[str, str]:
        return {
            "PRIVATE-TOKEN": self.api_token or "",
            "Content-Type": "application/json"
        }

    async def post_issue_comment(self, project_id: int, issue_iid: int, body: str) -> Optional[Dict[str, Any]]:
        """Post a comment on a specific issue."""
        if not self.api_token:
            logger.info(f"[MOCK] Posted comment on issue {issue_iid} in project {project_id}: {body}")
            return {"mock": True, "body": body}
            
        url = f"{self.api_url}/projects/{project_id}/issues/{issue_iid}/notes"
        return await self._post(url, json={"body": body})

    async def post_mr_comment(self, project_id: int, mr_iid: int, body: str) -> Optional[Dict[str, Any]]:
        """Post a comment on a specific merge request."""
        if not self.api_token:
            logger.info(f"[MOCK] Posted comment on MR {mr_iid} in project {project_id}: {body}")
            return {"mock": True, "body": body}
            
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}/notes"
        return await self._post(url, json={"body": body})

    async def add_issue_labels(self, project_id: int, issue_iid: int, labels: List[str]) -> Optional[Dict[str, Any]]:
        """Add labels to an issue."""
        if not self.api_token:
            logger.info(f"[MOCK] Added labels {labels} to issue {issue_iid} in project {project_id}")
            return {"mock": True, "labels": labels}
            
        labels_str = ",".join(labels)
        url = f"{self.api_url}/projects/{project_id}/issues/{issue_iid}"
        return await self._put(url, json={"add_labels": labels_str})
        
    async def add_mr_labels(self, project_id: int, mr_iid: int, labels: List[str]) -> Optional[Dict[str, Any]]:
        """Add labels to a merge request."""
        if not self.api_token:
            logger.info(f"[MOCK] Added labels {labels} to MR {mr_iid} in project {project_id}")
            return {"mock": True, "labels": labels}
            
        labels_str = ",".join(labels)
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}"
        return await self._put(url, json={"add_labels": labels_str})

    async def create_branch(self, project_id: int, branch_name: str, ref: str) -> Optional[Dict[str, Any]]:
        """Create a new branch in the repository."""
        if not self.api_token:
            logger.info(f"[MOCK] Created branch {branch_name} from {ref} in project {project_id}")
            return {"mock": True, "branch": branch_name}
            
        url = f"{self.api_url}/projects/{project_id}/repository/branches"
        return await self._post(url, json={"branch": branch_name, "ref": ref})

    async def assign_issue(self, project_id: int, issue_iid: int, assignee_ids: List[int]) -> Optional[Dict[str, Any]]:
        """Assign users to an issue."""
        if not self.api_token:
            logger.info(f"[MOCK] Assigned users {assignee_ids} to issue {issue_iid} in project {project_id}")
            return {"mock": True, "assignee_ids": assignee_ids}
            
        url = f"{self.api_url}/projects/{project_id}/issues/{issue_iid}"
        return await self._put(url, json={"assignee_ids": assignee_ids})

    async def assign_mr(self, project_id: int, mr_iid: int, assignee_ids: List[int]) -> Optional[Dict[str, Any]]:
        """Assign users to a merge request."""
        if not self.api_token:
            logger.info(f"[MOCK] Assigned users {assignee_ids} to MR {mr_iid} in project {project_id}")
            return {"mock": True, "assignee_ids": assignee_ids}
            
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}"
        return await self._put(url, json={"assignee_ids": assignee_ids})

    async def get_project_config(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Read project configuration and metadata."""
        if not self.api_token:
            logger.info(f"[MOCK] Read project config for project {project_id}")
            return {"mock": True, "id": project_id, "name": "Mock Project"}
            
        url = f"{self.api_url}/projects/{project_id}"
        return await self._get(url)

    async def _get(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self._headers(), timeout=10.0)
                if response.status_code == 401:
                    logger.error("GitLab Authentication failed (401). Check GITLAB_TOKEN.")
                elif response.status_code == 404:
                    logger.error(f"GitLab Resource not found (404): {url}")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitLab HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"GitLab GET request failed: {e}")
            return None

    async def _post(self, url: str, json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self._headers(), json=json, timeout=10.0)
                if response.status_code == 401:
                    logger.error("GitLab Authentication failed (401). Check GITLAB_TOKEN.")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitLab HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"GitLab POST request failed: {e}")
            return None
            
    async def _put(self, url: str, json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(url, headers=self._headers(), json=json, timeout=10.0)
                if response.status_code == 401:
                    logger.error("GitLab Authentication failed (401). Check GITLAB_TOKEN.")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitLab HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"GitLab PUT request failed: {e}")
            return None
