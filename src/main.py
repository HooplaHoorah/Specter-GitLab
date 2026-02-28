import logging
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from ecs.core import World
from integrations.webhook import router as webhook_router, set_world
from dashboard.router import router as dashboard_router, set_dashboard_world

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ghost Engine GitLab Agent")

# Initialize the ECS World
world = World()
from ecs.systems import GitLabEventTranslationSystem, AgentProcessingSystem, ActionExecutionSystem
translation_system = GitLabEventTranslationSystem()
agent_system = AgentProcessingSystem()
action_system = ActionExecutionSystem()

world.add_system(translation_system)
world.add_system(agent_system)
world.add_system(action_system)

set_world(world)
set_dashboard_world(world)

app.include_router(webhook_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1/dashboard")

# Mount static files for the dashboard frontend
import os
dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard")
app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard_ui")

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "ghost-engine-gitlab-agent"}

def main():
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Ghost Engine GitLab Duo Agent on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()

