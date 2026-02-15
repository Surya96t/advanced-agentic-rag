
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from app.database.client import SupabaseClient
from app.core.config import settings

def test_db():
    print(f"Testing DB Connection...")
    print(f"URL: {settings.supabase_url}")
    # Don't print the key for security, but check if it's set
    print(f"Key set: {'Yes' if settings.supabase_service_key else 'No'}")

    try:
        client = SupabaseClient.get_client()
        print("Client initialized.")
        
        # Try to select from users table
        print("Querying 'users' table...")
        response = client.table("users").select("count", count="exact").execute()
        print(f"Success! detected {response.count} users.")
        
        # Try to insert a test user (and rollback if possible, but supabase HTTP API is auto-commit)
        # We'll just read for now. If read works, write likely works too unless RLS blocks it.
        # But we form the client with service key, so RLS shouldn't block service role.

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_db()
