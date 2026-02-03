# Thread Management Implementation Guide

## ✅ What's Been Done (Backend)

### 1. **New API Endpoint: `/api/v1/threads`**

Created `backend/app/api/v1/threads.py` with full CRUD operations:

| Endpoint                      | Method | Description                               |
| ----------------------------- | ------ | ----------------------------------------- |
| `GET /api/v1/threads`         | GET    | List all threads for current user         |
| `GET /api/v1/threads/{id}`    | GET    | Get thread details + full message history |
| `POST /api/v1/threads`        | POST   | Create new thread (returns thread_id)     |
| `DELETE /api/v1/threads/{id}` | DELETE | Delete thread permanently                 |
| `PATCH /api/v1/threads/{id}`  | PATCH  | Update thread (rename)                    |

**Key Features:**

- ✅ Queries LangGraph checkpointer tables directly
- ✅ Ownership verification (user_id from JWT)
- ✅ Efficient database queries (no loading unnecessary data)
- ✅ Full message history deserialization
- ✅ Custom title support (stored in checkpoint metadata)

### 2. **Registered Router**

Updated `backend/app/api/v1/__init__.py` to include threads router.

---

## 📋 Next Steps (Implementation Checklist)

### **Phase 1: Test Backend API** ⏱️ 15 min

**Verify the new endpoints work:**

```bash
# 1. Start backend
cd backend
source .venv/bin/activate  # or your venv activation
uvicorn app.main:app --reload

# 2. Test endpoints (replace JWT token with your Clerk token)
TOKEN="your_jwt_token_here"

# List threads
curl -X GET http://localhost:8000/api/v1/threads \
  -H "Authorization: Bearer $TOKEN"

# Create new thread
curl -X POST http://localhost:8000/api/v1/threads \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Test Thread"}'

# Get thread details
curl -X GET http://localhost:8000/api/v1/threads/{thread_id} \
  -H "Authorization: Bearer $TOKEN"

# Delete thread
curl -X DELETE http://localhost:8000/api/v1/threads/{thread_id} \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Results:**

- `GET /threads` returns empty array initially
- After sending a chat message, thread appears in list
- Thread shows correct message count and preview
- Delete removes thread from database

---

### **Phase 2: Frontend - Chat Store** ⏱️ 30-45 min

**File: `frontend/stores/chat-store.ts`**

#### Step 2.1: Add Thread State

```typescript
interface ChatStore {
  // Existing
  messages: Message[];
  isStreaming: boolean;

  // NEW: Thread management
  currentThreadId: string | null; // Track active thread
  threads: Thread[]; // List of all threads
  isLoadingThreads: boolean;

  // NEW: Actions
  loadThreads: () => Promise<void>;
  createNewThread: () => Promise<string>;
  loadThread: (threadId: string) => Promise<void>;
  deleteThread: (threadId: string) => Promise<void>;
  setCurrentThread: (threadId: string | null) => void;
}

interface Thread {
  id: string;
  title: string;
  preview?: string;
  messageCount: number;
  createdAt: Date;
  updatedAt: Date;
}
```

#### Step 2.2: Update `sendMessage` to Use `currentThreadId`

```typescript
// BEFORE (current code):
const response = await fetch("/api/v1/chat", {
  body: JSON.stringify({
    message: content,
    stream: true,
    thread_id: "new", // ❌ Always creates new thread!
  }),
});

// AFTER (with thread management):
const response = await fetch("/api/v1/chat", {
  body: JSON.stringify({
    message: content,
    stream: true,
    thread_id: get().currentThreadId || "new", // ✅ Reuses thread!
  }),
});
```

#### Step 2.3: Capture `thread_id` from END Event

```typescript
// In your SSE event handler:
if (event.event === "end") {
  const data = JSON.parse(event.data);

  // Save thread_id if this was a new thread
  if (data.thread_id && !get().currentThreadId) {
    set({ currentThreadId: data.thread_id });

    // Optionally refresh thread list
    get().loadThreads();
  }
}
```

#### Step 2.4: Implement Thread Actions

```typescript
loadThreads: async () => {
  set({ isLoadingThreads: true });
  try {
    const response = await fetch('/api/v1/threads', {
      headers: { Authorization: `Bearer ${await getToken()}` }
    });
    const threads = await response.json();
    set({ threads, isLoadingThreads: false });
  } catch (error) {
    console.error('Failed to load threads:', error);
    set({ isLoadingThreads: false });
  }
},

createNewThread: async () => {
  const response = await fetch('/api/v1/threads', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${await getToken()}`
    },
    body: JSON.stringify({ title: 'New Chat' })
  });
  const { thread_id } = await response.json();

  // Clear current messages and set new thread
  set({
    currentThreadId: thread_id,
    messages: [],
  });

  return thread_id;
},

loadThread: async (threadId: string) => {
  const response = await fetch(`/api/v1/threads/${threadId}`, {
    headers: { Authorization: `Bearer ${await getToken()}` }
  });
  const { messages } = await response.json();

  set({
    currentThreadId: threadId,
    messages: messages,  // Load full history
  });
},

deleteThread: async (threadId: string) => {
  await fetch(`/api/v1/threads/${threadId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${await getToken()}` }
  });

  // Refresh thread list
  await get().loadThreads();

  // If deleted current thread, reset
  if (get().currentThreadId === threadId) {
    set({ currentThreadId: null, messages: [] });
  }
},
```

---

### **Phase 3: Frontend - Thread List UI** ⏱️ 60-90 min

**File: `frontend/components/chat/thread-sidebar.tsx` (NEW)**

```tsx
"use client";

import { useChatStore } from "@/stores/chat-store";
import { formatDistanceToNow } from "date-fns";
import { Plus, Trash2, MessageSquare } from "lucide-react";

export function ThreadSidebar() {
  const {
    threads,
    currentThreadId,
    isLoadingThreads,
    loadThreads,
    createNewThread,
    loadThread,
    deleteThread,
  } = useChatStore();

  // Load threads on mount
  useEffect(() => {
    loadThreads();
  }, []);

  return (
    <div className='w-64 border-r bg-muted/10 flex flex-col h-full'>
      {/* Header with New Chat button */}
      <div className='p-4 border-b'>
        <button
          onClick={createNewThread}
          className='w-full flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90'
        >
          <Plus className='w-4 h-4' />
          New Chat
        </button>
      </div>

      {/* Thread list */}
      <div className='flex-1 overflow-y-auto p-2'>
        {isLoadingThreads ? (
          <div className='text-center text-muted-foreground py-8'>
            Loading threads...
          </div>
        ) : threads.length === 0 ? (
          <div className='text-center text-muted-foreground py-8'>
            No conversations yet
          </div>
        ) : (
          threads.map((thread) => (
            <ThreadItem
              key={thread.id}
              thread={thread}
              isActive={thread.id === currentThreadId}
              onSelect={() => loadThread(thread.id)}
              onDelete={() => deleteThread(thread.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function ThreadItem({ thread, isActive, onSelect, onDelete }) {
  return (
    <div
      className={cn(
        "group p-3 rounded-lg cursor-pointer mb-1 transition-colors",
        isActive ? "bg-accent" : "hover:bg-accent/50",
      )}
      onClick={onSelect}
    >
      <div className='flex items-start justify-between'>
        <div className='flex-1 min-w-0'>
          <div className='flex items-center gap-2 mb-1'>
            <MessageSquare className='w-4 h-4 text-muted-foreground flex-shrink-0' />
            <p className='font-medium text-sm truncate'>{thread.title}</p>
          </div>
          {thread.preview && (
            <p className='text-xs text-muted-foreground truncate'>
              {thread.preview}
            </p>
          )}
          <p className='text-xs text-muted-foreground mt-1'>
            {formatDistanceToNow(new Date(thread.updatedAt), {
              addSuffix: true,
            })}
          </p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className='opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 rounded transition-opacity'
        >
          <Trash2 className='w-4 h-4 text-destructive' />
        </button>
      </div>
    </div>
  );
}
```

**File: `frontend/app/chat/[id]/page.tsx` (MODIFY)**

```tsx
export default function ChatPage({ params }: { params: { id: string } }) {
  const { loadThread, setCurrentThread } = useChatStore();

  useEffect(() => {
    if (params.id === "new") {
      // New chat - clear state
      setCurrentThread(null);
    } else {
      // Load existing thread
      loadThread(params.id);
    }
  }, [params.id]);

  return (
    <div className='flex h-screen'>
      <ThreadSidebar />
      <div className='flex-1'>{/* Your existing chat UI */}</div>
    </div>
  );
}
```

---

### **Phase 4: URL Management** ⏱️ 15 min

**Update routing to use thread_id in URL:**

```typescript
// When creating new thread:
router.push(`/chat/${newThreadId}`);

// When selecting thread from sidebar:
router.push(`/chat/${thread.id}`);

// For brand new chat:
router.push("/chat/new");
```

---

## 🎯 Minimal Viable Version (Start Here)

If you want to start **super simple** and iterate:

### Quick Win #1: Just Fix Thread Continuity (15 min)

**Only modify `chat-store.ts`:**

```typescript
// Add one field
currentThreadId: string | null;

// Update sendMessage
thread_id: get().currentThreadId || "new";

// Capture thread_id from END event
if (data.thread_id && !get().currentThreadId) {
  set({ currentThreadId: data.thread_id });
}
```

**Result:** Multi-turn conversations will work! No UI changes needed yet.

### Quick Win #2: Add "New Chat" Button (30 min)

Add a button in your existing chat UI:

```tsx
<button
  onClick={() => {
    useChatStore.setState({ currentThreadId: null, messages: [] });
  }}
>
  New Chat
</button>
```

**Result:** Users can start fresh conversations.

---

## 🧪 Testing Checklist

- [ ] Backend: All 5 endpoints return valid responses
- [ ] Backend: Thread list shows correct message counts
- [ ] Backend: Ownership verification prevents accessing other users' threads
- [ ] Frontend: Sending 2nd message in same thread has context from 1st
- [ ] Frontend: "New Chat" button creates fresh conversation
- [ ] Frontend: Thread list displays and refreshes correctly
- [ ] Frontend: Clicking thread loads full history
- [ ] Frontend: Deleting thread removes from list and database
- [ ] End-to-End: Ask "hello" → "what did I ask?" → Gets correct answer!

---

## 📊 Summary

**Backend:** ✅ Complete (5 new API endpoints + router registration)  
**Frontend:** ⏳ Pending (3 phases: store → UI → routing)

**Estimated Total Time:** 2-3 hours for full implementation  
**Estimated Minimal Version:** 30-45 minutes (just thread continuity)

---

## 🚀 Next Step

**Which approach do you want to take?**

**Option A: Minimal (30 min)** - Just fix thread continuity (no UI changes)  
**Option B: Full (2-3 hrs)** - Complete thread management with sidebar UI  
**Option C: Incremental** - Start with minimal, then add UI features iteratively

Let me know and I'll guide you through the implementation! 🎉
