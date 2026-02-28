# SPECTER™ — Powered by Game Engine Prime™

This is the source code for the Ghost Engine GitLab Duo Agent, designed for the GitLab AI Hackathon.

## Project Structure

- `agent/`: Core agent logic interfacing with the GitLab Duo Agent Platform (Claude models, natural language processing).
- `ecs/`: Ghost Engine Prime's Entity-Component-System implementation adapted for GitLab events (Issues, Merge Requests).
- `integrations/`: Handlers for GitLab APIs (REST operations like posting comments) and Webhooks.
- `config/`: Configuration management for environment variables and settings.
- `main.py`: Entry point for the application.

## Prerequisites

- Python 3.11+
- Poetry (or standard pip) for dependency management.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # OR if using poetry
   poetry install
   ```

2. Run the application:
   ```bash
   poetry run python main.py
   ```

## Documentation
Please see the `docs/` folder for information regarding local setup and ECS architecture diagrams.
