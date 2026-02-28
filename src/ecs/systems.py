import logging
from ecs.core import System
from ecs.components import (
    GitLabEventComponent, IssueComponent, AgentAnalysisComponent, 
    MergeRequestComponent, PipelineStatusComponent
)
from agent.claude import ClaudeAgent

logger = logging.getLogger(__name__)

class GitLabEventTranslationSystem(System):
    """Translates raw GitLab event payloads into specific ECS components (Issues, MRs, etc)."""
    
    def update(self) -> None:
        if not self.world:
            return
            
        entities = self.world.get_entities_with_components(GitLabEventComponent)
        
        for entity in entities:
            evt_comp = entity.get_component(GitLabEventComponent)
            if not evt_comp or evt_comp.processed:
                continue
                
            payload = evt_comp.payload
            kind = payload.get("object_kind")
            
            if kind == "issue":
                attrs = payload.get("object_attributes", {})
                issue_comp = IssueComponent(
                    issue_id=attrs.get("id", 0),
                    project_id=payload.get("project", {}).get("id", 0),
                    title=attrs.get("title", ""),
                    description=attrs.get("description", ""),
                    state=attrs.get("state", "")
                )
                entity.add_component(issue_comp)
                logger.info(f"Translated Issue event: {issue_comp.title}")
            elif kind == "merge_request":
                attrs = payload.get("object_attributes", {})
                mr_comp = MergeRequestComponent(
                    mr_id=attrs.get("id", 0),
                    project_id=payload.get("project", {}).get("id", 0),
                    title=attrs.get("title", ""),
                    description=attrs.get("description", ""),
                    source_branch=attrs.get("source_branch", ""),
                    target_branch=attrs.get("target_branch", ""),
                    state=attrs.get("state", ""),
                    author_id=attrs.get("author_id", 0)
                )
                entity.add_component(mr_comp)
                logger.info(f"Translated MR event: {mr_comp.title}")
            elif kind == "pipeline":
                attrs = payload.get("object_attributes", {})
                pipe_comp = PipelineStatusComponent(
                    status=attrs.get("status", ""),
                    ref=attrs.get("ref", ""),
                    web_url=attrs.get("detailed_status", {}).get("details_path", "")
                )
                entity.add_component(pipe_comp)
                logger.info(f"Translated Pipeline event: {pipe_comp.status} for {pipe_comp.ref}")
            
            evt_comp.processed = True


import asyncio
from agent.duo_platform import DuoAgentPlatform

class AgentProcessingSystem(System):
    """
    Processes Entities that have actionable data using the GitLab Duo Agent Platform.
    
    Routes all analysis through the DuoAgentPlatform which orchestrates:
    Trigger matching → Context building → Tool selection → AI analysis
    """
    
    def __init__(self):
        super().__init__()
        self.platform = DuoAgentPlatform()
        
    def update(self) -> None:
        if not self.world:
            return
            
        # Process Issues
        issue_entities = self.world.get_entities_with_components(IssueComponent)
        for entity in issue_entities:
            if entity.has_component(AgentAnalysisComponent):
                continue
                
            issue_comp = entity.get_component(IssueComponent)
            if not issue_comp:
                continue
            
            entity.add_component(AgentAnalysisComponent(analysis_result="[ANALYSIS IN PROGRESS]"))
            asyncio.create_task(self._process_issue_async(entity, issue_comp))

        # Process Merge Requests
        mr_entities = self.world.get_entities_with_components(MergeRequestComponent)
        for entity in mr_entities:
            if entity.has_component(AgentAnalysisComponent):
                continue
                
            mr_comp = entity.get_component(MergeRequestComponent)
            if not mr_comp:
                continue
                
            entity.add_component(AgentAnalysisComponent(analysis_result="[ANALYSIS IN PROGRESS]"))
            asyncio.create_task(self._process_mr_async(entity, mr_comp))

    async def _process_issue_async(self, entity, issue_comp: IssueComponent):
        logger.info(f"[Duo Platform] Processing Issue via Trigger → Tool pipeline: {issue_comp.title}")
        try:
            analysis = await self.platform.analyze_issue(issue_comp.title, issue_comp.description)
            entity.add_component(AgentAnalysisComponent(analysis_result=analysis))
            logger.info(f"[Duo Platform] Finished Issue Analysis: {issue_comp.title}")
        except Exception as e:
            logger.error(f"Error processing issue via Duo Platform: {e}")
            entity.add_component(AgentAnalysisComponent(analysis_result=f"[ERROR] {e}"))

    async def _process_mr_async(self, entity, mr_comp: MergeRequestComponent):
        logger.info(f"[Duo Platform] Processing MR via Trigger → Tool pipeline: {mr_comp.title}")
        try:
            analysis = await self.platform.analyze_mr(
                mr_comp.title, mr_comp.description,
                mr_comp.source_branch, mr_comp.target_branch
            )
            entity.add_component(AgentAnalysisComponent(analysis_result=analysis))
            logger.info(f"[Duo Platform] Finished MR Analysis: {mr_comp.title}")
        except Exception as e:
            logger.error(f"Error processing MR via Duo Platform: {e}")
            entity.add_component(AgentAnalysisComponent(analysis_result=f"[ERROR] {e}"))


from integrations.gitlab_client import GitLabClient

class ActionExecutionSystem(System):
    """Translates Agent Analysis results into concrete GitLab REST API actions."""
    
    def __init__(self):
        super().__init__()
        self.gitlab = GitLabClient()
        
    def update(self) -> None:
        if not self.world:
            return
            
        entities = self.world.get_entities_with_components(AgentAnalysisComponent)
        
        for entity in entities:
            analysis_comp = entity.get_component(AgentAnalysisComponent)
            if not analysis_comp or analysis_comp.action_taken:
                continue
            
            if "[ANALYSIS IN PROGRESS]" in analysis_comp.analysis_result or "[ERROR]" in analysis_comp.analysis_result:
                continue
                
            issue_comp = entity.get_component(IssueComponent)
            mr_comp = entity.get_component(MergeRequestComponent)
            
            if issue_comp:
                asyncio.create_task(self._execute_issue_action(issue_comp, analysis_comp))
                analysis_comp.action_taken = True
                
            elif mr_comp:
                asyncio.create_task(self._execute_mr_action(mr_comp, analysis_comp))
                analysis_comp.action_taken = True
                
    async def _execute_issue_action(self, issue_comp: IssueComponent, analysis_comp: AgentAnalysisComponent):
        logger.info(f"Executing action for Issue: {issue_comp.title}")
        comment_body = f"🤖 **SPECTER™ Analysis** — Powered by Game Engine Prime™\n\n{analysis_comp.analysis_result}"
        await self.gitlab.post_issue_comment(issue_comp.project_id, issue_comp.issue_id, comment_body)

    async def _execute_mr_action(self, mr_comp: MergeRequestComponent, analysis_comp: AgentAnalysisComponent):
        logger.info(f"Executing action for Merge Request: {mr_comp.title}")
        comment_body = f"🤖 **SPECTER™ Analysis** — Powered by Game Engine Prime™\n\n{analysis_comp.analysis_result}"
        await self.gitlab.post_mr_comment(mr_comp.project_id, mr_comp.mr_id, comment_body)

