import asyncio
from app.retrieval.rerankers.flashrank import FlashRankReranker
from app.schemas.retrieval import SearchResult
from uuid import uuid4

async def main():
    reranker = FlashRankReranker(model_name="ms-marco-MiniLM-L-12-v2")
    
    query = "How do I authenticate?"
    
    # Create dummy search results
    results = [
        SearchResult(
            chunk_id=uuid4(),
            document_id=uuid4(),
            document_title="Auth Guide",
            content="Authentication is the process of verifying who a user is.",
            metadata={"source": "doc"},
            score=0.9,
            rank=1,
            source="vector"
        ),
        SearchResult(
            chunk_id=uuid4(),
            document_id=uuid4(),
            document_title="Random text",
            content="The weather is nice today.",
            metadata={"source": "doc"},
            score=0.5,
            rank=2,
            source="vector"
        )
    ]
    
    print("Reranking...")
    reranked = await reranker.rerank(query, results)
    
    for r in reranked:
        print(f"Content: {r.content[:30]}... | Score: {r.score}")

if __name__ == "__main__":
    asyncio.run(main())
