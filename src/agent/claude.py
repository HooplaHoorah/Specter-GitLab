import os
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ClaudeAgent:
    """
    Interface for interacting with Anthropic's Claude model via the GitLab Duo Agent Platform
    or directly via Anthropic's API if needed for the hackathon.
    """
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY is not set. Claude Agent will operate in mock mode.")
        
    async def analyze_issue(self, title: str, description: str) -> str:
        """
        Analyzes an issue and provides a summary or suggested action.
        Backward-compatible entry point — use DuoAgentPlatform for
        the full Tools/Triggers/Context pipeline.
        """
        prompt = f"Please analyze this GitLab issue and suggest an action:\nTitle: {title}\nDescription: {description}"
        return await self._call_claude(prompt)

    async def analyze_with_tools(self, prompt: str, tool_names: Optional[list] = None) -> str:
        """
        Enhanced analysis method for the Duo Agent Platform pipeline.
        Accepts a context-enriched prompt built by DuoAgentPlatform.
        """
        if tool_names:
            logger.info(f"Claude analysis with Duo tools: {tool_names}")
        return await self._call_claude(prompt)

    async def _call_claude(self, prompt: str) -> str:
        if not self.api_key:
            # Mock mode — return a realistic mock response
            return "[MOCK] Claude response to: " + prompt
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 1024,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return str(data['content'][0]['text'])
        except Exception as e:
            logger.error(f"Error calling Claude: {e}")
            return f"Error analyzing with Claude: {e}"
