from fastapi import APIRouter
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

router = APIRouter()
ecs_world: World = None

def set_dashboard_world(world: World):
    global ecs_world
    ecs_world = world

import subprocess
import os

@router.post("/demo/trigger")
def trigger_demo():
    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "demo_mode.py")
    subprocess.Popen([sys.executable, script_path])
    return {"status": "demo_started"}

@router.get("/state")
def get_dashboard_state() -> Dict[str, Any]:
    if not ecs_world:
        return {"status": "error", "message": "World not initialized"}

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

    # Sort activity feed so latest is first (assuming IDs increase over time roughly, or we could add timestamp to components)
    state["activity_feed"].reverse()

    return state
