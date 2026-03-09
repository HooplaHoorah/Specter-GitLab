import os
import hmac
import hashlib
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Header
from integrations.models import GitLabEventPayload
from ecs.core import World, Entity
import logging
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

# Global reference to the ECS World (set from main.py)
ecs_world: World = None

def set_world(world: World):
    global ecs_world
    ecs_world = world

async def process_event_in_ecs(payload: dict):
    """
    Background task to translate a GitLab webhook payload into ECS Entities/Components 
    and fire a world tick.
    """
    if not ecs_world:
        logger.error("ECS World is not initialized.")
        return

    logger.info(f"Processing event in ECS: {payload.get('object_kind')}")
    
    # Translate GitLab payload into an Entity with specific Components
    from ecs.components import GitLabEventComponent
    issue_entity = Entity()
    issue_entity.add_component(GitLabEventComponent(payload))
    ecs_world.add_entity(issue_entity)
    
    # Process systems
    ecs_world.tick()

@router.post("/webhook")
async def gitlab_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    x_gitlab_token: Optional[str] = Header(None)
):
    """
    GitLab webhook endpoint. Receives events and queues them for processing into the ECS.
    Includes X-Gitlab-Token verification for security.
    """
    # Security: Verify GitLab Webhook Secret if configured
    webhook_secret = os.getenv("GITLAB_WEBHOOK_SECRET")
    if webhook_secret:
        if not x_gitlab_token or x_gitlab_token != webhook_secret:
            logger.warning("Unauthorized webhook attempt: Invalid or missing X-Gitlab-Token")
            raise HTTPException(status_code=403, detail="Invalid X-Gitlab-Token")

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Add to background tasks so we return 200 immediately to GitLab
    background_tasks.add_task(process_event_in_ecs, payload)
    
    return {"status": "ok", "message": "Event received and queued for processing."}
