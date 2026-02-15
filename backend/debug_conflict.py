import os
import sys
import traceback
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from app.database.client import SupabaseClient

def test_conflict():
    print("Testing Conflict Scenarios...")
    try:
        client = SupabaseClient.get_client()
        
        email = "conflict_test@example.com"
        id1 = "user_111"
        id2 = "user_222"

        # 1. Clean up
        print("Cleaning up test users...")
        client.table("users").delete().eq("email", email).execute()
        client.table("users").delete().eq("id", id1).execute()
        client.table("users").delete().eq("id", id2).execute()

        # 2. Insert User 1
        print(f"Inserting User 1: {id1}, {email}")
        client.table("users").insert({
            "id": id1,
            "email": email,
            "full_name": "User One"
        }).execute()
        print("User 1 inserted.")

        # 3. Insert User 2 with SAME EMAIL but DIFFERENT ID
        print(f"Inserting User 2: {id2}, {email} (Should FAIL)")
        client.table("users").insert({
            "id": id2,
            "email": email,
            "full_name": "User Two"
        }).execute()
        print("User 2 inserted (Unexpected).")

    except Exception as e:
        print(f"Caught expected error: {e}")
        # print specific details if available
        if hasattr(e, 'code'):
            print(f"Error Code: {e.code}")
        if hasattr(e, 'details'):
            print(f"Error Details: {e.details}")
        if hasattr(e, 'message'):
            print(f"Error Message: {e.message}")

if __name__ == "__main__":
    test_conflict()
