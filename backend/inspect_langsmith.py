import asyncio
from dotenv import load_dotenv
import os
from datetime import datetime

# Load env from backend/.env
load_dotenv(".env")
# Also need to manually load from backend if running from root, or just trust the environment
if not os.getenv("LANGCHAIN_API_KEY"):
    load_dotenv("backend/.env")

from langsmith import Client

async def analyze_langsmith_project():
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project_name = os.getenv("LANGCHAIN_PROJECT")
    
    if not api_key or not project_name:
        print("Error: LANGCHAIN_API_KEY or LANGCHAIN_PROJECT not set in environment")
        return

    print(f"\nLocked on Project: '{project_name}'")
    client = Client()

    # 1. Project Overview
    try:
        project = client.read_project(project_name=project_name)
        print(f"\n--- Project Metadata ---")
        print(f"ID: {project.id}")
        print(f"Run Count: {project.run_count}")
        print(f"Latency (p50): {project.latency_p50}")
        print(f"Latency (p99): {project.latency_p99}")
    except Exception as e:
        print(f"Could not read project stats directly: {e}")

    # 2. Runs Analysis (Inspect RAW Data)
    print("\n--- RAW Run Data (Latest 1) ---")
    runs = list(client.list_runs(
        project_name=project_name,
        is_root=True,
        limit=1
    ))
    
    if runs:
        import json
        # Convert the Run object to a dictionary and print it as formatted JSON
        # using default=str to handle datetime objects
        run_data = runs[0].dict()
        print(json.dumps(run_data, indent=2, default=str))
        
        print("\n--- fields available to query ---")
        print(list(run_data.keys()))
    else:
        print("No runs found to inspect.")

if __name__ == "__main__":
    asyncio.run(analyze_langsmith_project())
