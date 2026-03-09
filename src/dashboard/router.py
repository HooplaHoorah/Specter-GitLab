import json
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from ecs.core import World
from ecs.components import (
    GitLabEventComponent,
    IssueComponent, 
    MergeRequestComponent, 
    PipelineStatusComponent, 
    AgentAnalysisComponent
)
from typing import Dict, Any
import sys
import subprocess
import os

router = APIRouter()
ecs_world: World = None

def set_dashboard_world(world: World):
    global ecs_world
    ecs_world = world

@router.post("/demo/trigger")
def trigger_demo():
    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "demo_mode.py")
    subprocess.Popen([sys.executable, script_path])
    return {"status": "demo_started"}

@router.get("/state")
def get_dashboard_state() -> Dict[str, Any]:
    if not ecs_world:
        return {"status": "error", "message": "World not initialized"}
    return _calculate_state()

def _calculate_state() -> Dict[str, Any]:
    if not ecs_world:
        return {"error": "World not initialized", "entities": {"issues": 0, "mrs": 0, "pipelines": 0}, "activity_feed": []}
        
    state: Dict[str, Any] = {
        "activity_feed": [],
        "pipelines": [],
        "entities": {
            "issues": 0,
            "mrs": 0,
            "pipelines": 0
        },
        "latest_analysis": None,
        "config": {
            "project": "ghost-engine-gitlab",
            "webhook_endpoint": "/api/v1/webhook",
            "mock_mode": True,  # Default for demo
            "components": ["GitLabEvent", "Issue", "MergeRequest", "PipelineStatus", "AgentAnalysis"]
        }
    }

    # Gather Issues
    issue_entities = ecs_world.get_entities_with_components(IssueComponent)
    state["entities"]["issues"] = len(issue_entities)
    for ent in issue_entities:
        issue = ent.get_component(IssueComponent)
        analysis = ent.get_component(AgentAnalysisComponent)
        
        feed_item = {
            "type": "Issue",
            "id": issue.issue_id,
            "title": issue.title,
            "state": issue.state,
            "analysis_status": "done" if (analysis and analysis.action_taken) else "in_progress" if analysis else "pending",
            "action_taken": analysis.action_taken if analysis else False
        }
        state["activity_feed"].append(feed_item)

        if analysis and analysis.analysis_result != "[ANALYSIS IN PROGRESS]" and "[ERROR]" not in analysis.analysis_result:
            if not state["latest_analysis"]:
                state["latest_analysis"] = {
                    "target": issue.title,
                    "result": analysis.analysis_result,
                    "action_executed": analysis.action_taken
                }

    # Gather MRs
    mr_entities = ecs_world.get_entities_with_components(MergeRequestComponent)
    state["entities"]["mrs"] = len(mr_entities)
    for ent in mr_entities:
        mr = ent.get_component(MergeRequestComponent)
        analysis = ent.get_component(AgentAnalysisComponent)
        
        feed_item = {
            "type": "Merge Request",
            "id": mr.mr_id,
            "title": mr.title,
            "state": mr.state,
            "analysis_status": "done" if (analysis and analysis.action_taken) else "in_progress" if analysis else "pending",
            "action_taken": analysis.action_taken if analysis else False
        }
        state["activity_feed"].append(feed_item)

        if analysis and analysis.analysis_result != "[ANALYSIS IN PROGRESS]" and "[ERROR]" not in analysis.analysis_result:
            if not state["latest_analysis"]:
                state["latest_analysis"] = {
                    "target": mr.title,
                    "result": analysis.analysis_result,
                    "action_executed": analysis.action_taken
                }

    # Gather Pipelines
    pipeline_entities = ecs_world.get_entities_with_components(PipelineStatusComponent)
    state["entities"]["pipelines"] = len(pipeline_entities)
    for ent in pipeline_entities:
        pipe = ent.get_component(PipelineStatusComponent)
        state["pipelines"].append({
            "ref": pipe.ref,
            "status": pipe.status,
            "url": pipe.web_url
        })

    # Sort activity feed so latest is first
    state["activity_feed"].reverse()
    return state

@router.get("/stream")
async def stream_dashboard_state(request: Request):
    """
    Server-Sent Events (SSE) endpoint for real-time dashboard updates.
    """
    async def event_generator():
        last_state_hash = None
        while True:
            if await request.is_disconnected():
                break

            current_state = _calculate_state()
            current_state_hash = hash(json.dumps(current_state, sort_keys=True))

            if current_state_hash != last_state_hash:
                yield {
                    "event": "message",
                    "data": json.dumps(current_state)
                }
                last_state_hash = current_state_hash

            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
