"""
GitLab Duo Agent Platform — Core Adapter

The DuoAgentPlatform is the central orchestration layer that connects
Ghost Engine Prime's ECS with the GitLab Duo Agent Platform concepts:

  - TOOLS: Callable actions (triage, review, scan, pipeline analysis)
  - TRIGGERS: Event-driven activation (webhook events, @mentions)
  - CONTEXT: Rich structured information for AI decision-making

This adapter wraps the underlying ClaudeAgent and enriches its prompts
with Duo-formatted context and tool-aware instructions.
"""

import logging
from typing import Dict, Any, List, Optional
from agent.claude import ClaudeAgent
from agent.tools import DuoTool, ToolResult, AVAILABLE_TOOLS
from agent.triggers import DuoTrigger, match_trigger
from agent.context import DuoContext, ContextBuilder

logger = logging.getLogger(__name__)


class DuoAgentPlatform:
    """
    GitLab Duo Agent Platform adapter for Ghost Engine Prime.
    
    Orchestrates the full Trigger → Context → Tool → AI → Action pipeline
    following the Duo Agent Platform specification.
    """
    
    def __init__(self):
        self.agent = ClaudeAgent()
        self.registered_tools: Dict[str, DuoTool] = dict(AVAILABLE_TOOLS)
        self.execution_log: List[Dict[str, Any]] = []
        logger.info(
            f"DuoAgentPlatform initialized with {len(self.registered_tools)} tools: "
            f"{', '.join(self.registered_tools.keys())}"
        )
    
    def get_registered_tools(self) -> List[Dict[str, str]]:
        """Return metadata for all registered tools (for dashboard display)."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self.registered_tools.values()
        ]
    
    async def process_event(self, event_payload: Dict[str, Any]) -> Optional[ToolResult]:
        """
        Full Duo Agent Platform pipeline:
        1. Match a Trigger to the incoming event
        2. Build Context from the event payload
        3. Select Tools based on the trigger
        4. Generate AI analysis with enriched prompt
        5. Execute tool with AI response to produce structured result
        """
        # Step 1: Match trigger
        trigger = match_trigger(event_payload)
        if not trigger:
            logger.info(f"No trigger matched for event — skipping Duo processing")
            return None
        
        # Step 2: Build tool context from the event payload
        tool_context = trigger.build_tool_context(event_payload)
        
        # Step 3: Select primary tools
        primary_tools = trigger.get_tools()
        secondary_tools = trigger.get_secondary_tools(tool_context)
        all_tools = primary_tools + secondary_tools
        
        if not all_tools:
            logger.warning(f"Trigger {trigger.name} returned no tools")
            return None
        
        # Step 4: Build Duo context for prompt enrichment
        duo_context = self._build_duo_context(trigger, tool_context)
        
        # Step 5: Generate AI analysis with context-enriched prompt
        prompt = self._build_enriched_prompt(duo_context, all_tools, tool_context)
        ai_response = await self.agent._call_claude(prompt)
        
        # Step 6: Execute primary tool with AI response
        primary_tool = primary_tools[0]
        result = await primary_tool.execute(tool_context, ai_response)
        
        # Execute secondary tools and merge results
        for sec_tool in secondary_tools:
            sec_result = await sec_tool.execute(tool_context, ai_response)
            if sec_result.severity == "Critical":
                result.severity = "Critical"
                result.labels.extend(sec_result.labels)
                result.recommended_actions.extend(sec_result.recommended_actions)
        
        # Log execution
        self.execution_log.append({
            "trigger": trigger.name,
            "tools_used": [t.name for t in all_tools],
            "result_severity": result.severity,
            "result_category": result.category
        })
        
        logger.info(
            f"Duo pipeline complete: {trigger.name} → "
            f"{[t.name for t in all_tools]} → {result.category} ({result.severity})"
        )
        
        return result
    
    def _build_duo_context(self, trigger: DuoTrigger, tool_context: Dict[str, Any]) -> DuoContext:
        """Build a DuoContext from the trigger and tool context."""
        project_id = tool_context.get("project_id", 0)
        project_name = tool_context.get("project_name", "unknown")
        event_type = tool_context.get("event_type", "")
        
        if event_type == "issue":
            return ContextBuilder.from_issue(
                project_id=project_id,
                project_name=project_name,
                issue_id=tool_context.get("issue_id", 0),
                title=tool_context.get("title", ""),
                description=tool_context.get("description", ""),
                state=tool_context.get("state", "")
            )
        elif event_type == "merge_request":
            return ContextBuilder.from_merge_request(
                project_id=project_id,
                project_name=project_name,
                mr_id=tool_context.get("mr_id", 0),
                title=tool_context.get("title", ""),
                description=tool_context.get("description", ""),
                source_branch=tool_context.get("source_branch", ""),
                target_branch=tool_context.get("target_branch", ""),
                state=tool_context.get("state", ""),
                author_id=tool_context.get("author_id", 0)
            )
        elif event_type == "pipeline":
            return ContextBuilder.from_pipeline(
                project_id=project_id,
                project_name=project_name,
                status=tool_context.get("status", ""),
                ref=tool_context.get("ref", "")
            )
        else:
            return DuoContext(
                project=ContextBuilder.from_issue(
                    project_id, project_name, 0, "", "", ""
                ).project
            )
    
    def _build_enriched_prompt(self, context: DuoContext, tools: List[DuoTool], 
                                tool_context: Dict[str, Any]) -> str:
        """
        Build a context-enriched prompt following the Duo Agent Platform pattern.
        The prompt includes structured context, available tools, and specific instructions.
        """
        tool_descriptions = "\n".join([
            f"  - {tool.name}: {tool.description}"
            for tool in tools
        ])
        
        context_block = context.to_prompt_context()
        
        title = tool_context.get("title", "")
        description = tool_context.get("description", "")
        
        prompt = (
            f"You are a GitLab Duo AI Agent operating within the SPECTER™ platform, powered by Game Engine Prime™.\n"
            f"You have access to the following tools:\n{tool_descriptions}\n\n"
            f"{context_block}\n\n"
            f"TASK:\n"
            f"Analyze the following GitLab event and provide actionable recommendations.\n"
            f"Title: {title}\n"
            f"Description: {description}\n\n"
            f"Provide your analysis in the following format:\n"
            f"SEVERITY: [Critical/High/Medium/Low]\n"
            f"CATEGORY: [Bug/Feature/Security/Review/Pipeline]\n\n"
            f"ANALYSIS:\n[Your detailed analysis]\n\n"
            f"RECOMMENDED ACTIONS:\n[Numbered list of specific actions]\n\n"
            f"Include any security findings if applicable."
        )
        
        return prompt

    async def analyze_issue(self, title: str, description: str) -> str:
        """
        Backward-compatible method that wraps the Duo pipeline.
        Creates a synthetic event payload and processes it through
        the full Trigger → Context → Tool → AI pipeline.
        """
        synthetic_payload = {
            "object_kind": "issue",
            "project": {"id": 0, "name": "unknown"},
            "object_attributes": {
                "id": 0,
                "title": title,
                "description": description,
                "state": "opened"
            }
        }
        
        result = await self.process_event(synthetic_payload)
        if result:
            return self._format_result(result)
        
        # Fallback to direct Claude call
        return await self.agent.analyze_issue(title, description)

    async def analyze_mr(self, title: str, description: str, 
                         source_branch: str = "", target_branch: str = "") -> str:
        """
        Backward-compatible method for MR analysis through the Duo pipeline.
        """
        synthetic_payload = {
            "object_kind": "merge_request",
            "project": {"id": 0, "name": "unknown"},
            "object_attributes": {
                "id": 0,
                "title": title,
                "description": description,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "state": "opened",
                "author_id": 0
            }
        }
        
        result = await self.process_event(synthetic_payload)
        if result:
            return self._format_result(result)
        
        return await self.agent.analyze_issue(title, description)

    def _format_result(self, result: ToolResult) -> str:
        """Format a ToolResult into a human-readable analysis string."""
        lines = []
        lines.append(f"SEVERITY: {result.severity}")
        lines.append(f"CATEGORY: {result.category}")
        lines.append(f"DUO TOOL: {result.tool_name}")
        lines.append("")
        lines.append("ANALYSIS:")
        lines.append(result.output)
        lines.append("")
        if result.recommended_actions:
            lines.append("RECOMMENDED ACTIONS:")
            for i, action in enumerate(result.recommended_actions, 1):
                lines.append(f"{i}. {action}")
        if result.labels:
            lines.append("")
            lines.append(f"LABELS: {', '.join(result.labels)}")
        return "\n".join(lines)
