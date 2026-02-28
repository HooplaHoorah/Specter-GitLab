from fastapi import APIRouter, Request, BackgroundTasks
from integrations.models import GitLabEventPayload
from ecs.core import World, Entity
import logging

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
async def gitlab_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    GitLab webhook endpoint. Receives events and queues them for processing into the ECS.
    """
    # Parse the raw payload instead of relying fully on Pydantic initially
    # to gracefully handle all the varying forms of GitLab webhooks.
    payload = await request.json()
    
    # Add to background tasks so we return 200 immediately to GitLab
    background_tasks.add_task(process_event_in_ecs, payload)
    
    return {"status": "ok", "message": "Event received and queued for processing."}
