import json
import httpx
import asyncio
import os
import sys

async def post_event(client, payload, description):
    print(f"[DEMO] Sending {description}...")
    try:
        response = await client.post("http://localhost:8000/api/v1/webhook", json=payload)
        response.raise_for_status()
        print(f"[DEMO] {description} accepted.")
    except Exception as e:
        print(f"[DEMO ERROR] Failed to send {description}: {e}")

async def run_demo():
    print("====================================")
    print(" GHOST ENGINE PRIME - GOLDEN DEMO")
    print("====================================")
    
    # Load payloads
    payloads_file = os.path.join(os.path.dirname(__file__), "demo_payloads.json")
    try:
        with open(payloads_file, "r") as f:
            payloads = json.load(f)
    except Exception as e:
        print(f"Failed to load payloads: {e}")
        sys.exit(1)

    # We will orchestrate a realistic flow for screenshot purposes
    # Dashboard should be open already

    async with httpx.AsyncClient() as client:
        # 1. Start with a running pipeline to show something in pipeline board
        await post_event(client, payloads["pipeline_running"], "Pipeline (Running) - main")
        await asyncio.sleep(2)
        
        # 2. Issue 1 arrives (Bug)
        await post_event(client, payloads["issue_bug"], "Issue (Bug)")
        await asyncio.sleep(6) # Let agent analyze and post response
        
        # 3. MR 1 arrives (Fix for Bug)
        await post_event(client, payloads["mr_review"], "Merge Request (Review)")
        await asyncio.sleep(2)
        
        # 4. Pipeline starts for MR 1
        await post_event(client, payloads["pipeline_success"], "Pipeline (Success) - MR 1")
        await asyncio.sleep(5) # Let agent finish analysis
        
        # 5. Issue 2 arrives (Feature)
        await post_event(client, payloads["issue_feature"], "Issue (Feature)")
        await asyncio.sleep(4)
        
        # 6. Issue 3 arrives (Security)
        await post_event(client, payloads["issue_security"], "Issue (Security)")
        await asyncio.sleep(6)
        
        # 7. MR 2 arrives (Dependency - Pipeline Failed)
        await post_event(client, payloads["mr_dependency"], "Merge Request (Dependency Update)")
        await asyncio.sleep(2)
        await post_event(client, payloads["pipeline_failed"], "Pipeline (Failed) - MR 2")
        await asyncio.sleep(4)
        
        print("====================================")
        print(" DEMO SCENARIO COMPLETE")
        print(" All entities should be visible on dashboard.")
        print("====================================")

if __name__ == "__main__":
    asyncio.run(run_demo())
