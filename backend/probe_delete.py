import asyncio, hashlib, time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.deps import get_current_user_id, check_user_rate_limit
from app.database.client import get_supabase_client
from app.database.models import Document, DocumentStatus
from app.database.repositories.documents import DocumentRepository


async def main() -> None:
    """Override app dependencies and probe the delete-document endpoint locally."""
    # Provide a fixed test user ID instead of a real Clerk-verified JWT
    app.dependency_overrides[get_current_user_id] = lambda: "test_user_123"
    # Return a permissive (limit, remaining, reset) tuple so rate-limit checks pass
    app.dependency_overrides[check_user_rate_limit] = lambda: (100, 99, int(time.time()) + 3600)
    db = get_supabase_client()
    repo = DocumentRepository(db)
    content = "probe"
    db.table("users").upsert({"id": "test_user_123", "email": "test_user_123@test.com"}).execute()
    doc = Document(
        user_id="test_user_123",
        title="Probe",
        file_type="txt",
        file_size=4,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        status=DocumentStatus.COMPLETED,
    )
    doc = repo.create(doc)
    print(f"Created doc id: {doc.id}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.delete(f"/api/v1/documents/{doc.id}")
        print("STATUS:", r.status_code)
        print("BODY:", r.json())


asyncio.run(main())
