"""Check messages in the latest checkpoint"""
import argparse
import asyncio
from app.core.config import settings


async def main(thread_id: str) -> None:
    """Inspect LangGraph checkpoint messages for a given thread ID."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    async with AsyncPostgresSaver.from_conn_string(settings.supabase_connection_string) as checkpointer:
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = await checkpointer.aget(config)

        if not checkpoint:
            print("No checkpoint found")
            return

        state = checkpoint.get("channel_values", {})
        messages = state.get("messages", [])
        print(f"Messages count: {len(messages)}")
        for i, msg in enumerate(messages):
            msg_type = getattr(msg, "type", "?")
            content_preview = str(getattr(msg, "content", ""))[:80]
            print(f"  [{i}] type={msg_type} content={content_preview!r}")
            ak = getattr(msg, "additional_kwargs", {})
            if ak:
                print(f"       additional_kwargs keys: {list(ak.keys())}")
                if "citations" in ak:
                    print(f"       citations count: {len(ak['citations'])}")
                    for c in ak["citations"][:2]:
                        print(f"         - chunk_id={c.get('chunk_id','?')} doc={c.get('document_title','?')[:40]}")
                if "citation_map" in ak:
                    cm = ak["citation_map"]
                    print(f"       citation_map keys: {list(cm.keys())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect LangGraph checkpoint messages for a thread.")
    parser.add_argument("thread_id", type=str, help="LangGraph thread UUID to inspect")
    args = parser.parse_args()
    asyncio.run(main(args.thread_id))
