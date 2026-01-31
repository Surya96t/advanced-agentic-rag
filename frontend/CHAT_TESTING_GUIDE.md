# Chat Interface - Testing Guide

## 🧪 Quick Test Scenarios

### Test 1: Basic Question-Answer Flow

**Goal:** Verify end-to-end chat functionality

1. Navigate to http://localhost:3000/chat
2. Type: `What is LangGraph?`
3. Press Enter

**Expected Result:**

- ✅ Your message appears on the right (primary color)
- ✅ Loading spinner shows in send button
- ✅ AI response appears on the left (muted color)
- ✅ Citations show as badges below response
- ✅ Timestamp displays below each message

---

### Test 2: Markdown Rendering

**Goal:** Verify markdown formatting works

1. Ask: `Can you show me a code example?`
2. Wait for response

**Expected Result:**

- ✅ Code blocks have syntax highlighting
- ✅ Lists are properly formatted
- ✅ Inline code has monospace font
- ✅ Headings and bold text render correctly

---

### Test 3: Auto-Resize Textarea

**Goal:** Verify input grows with content

1. Type a long message with multiple lines
2. Press Shift+Enter to add new lines
3. Watch textarea expand

**Expected Result:**

- ✅ Textarea height increases as you type
- ✅ Max height caps at 200px
- ✅ Scroll appears if exceeds max height
- ✅ After sending, textarea resets to single line

---

### Test 4: Auto-Scroll Behavior

**Goal:** Verify messages stay in view

1. Send multiple messages to fill the screen
2. Observe scroll behavior

**Expected Result:**

- ✅ Automatically scrolls to bottom on new message
- ✅ Smooth scroll animation
- ✅ Latest message always visible

---

### Test 5: Error Handling

**Goal:** Verify error states work

1. Stop the backend server
2. Try to send a message
3. Observe error handling

**Expected Result:**

- ✅ Error toast notification appears
- ✅ Message not added to chat
- ✅ Input remains enabled for retry
- ✅ Error message is user-friendly

---

### Test 6: Empty State

**Goal:** Verify initial state

1. Open chat page for first time
2. Observe empty state

**Expected Result:**

- ✅ Shows "Start a conversation" message
- ✅ Input is enabled and focused
- ✅ No error messages
- ✅ Clean, centered layout

---

### Test 7: Citation Display

**Goal:** Verify citations show correctly

1. Upload a document first (if needed)
2. Ask a question about the document
3. Check citations in response

**Expected Result:**

- ✅ Citations appear as badges
- ✅ Document title is visible
- ✅ Similarity score percentage shows
- ✅ File icon displays
- ✅ Multiple citations wrap to new line

---

### Test 8: Keyboard Navigation

**Goal:** Verify accessibility

1. Use Tab to navigate
2. Try Enter and Shift+Enter
3. Test Escape key (future feature)

**Expected Result:**

- ✅ Tab focuses on textarea
- ✅ Enter sends message
- ✅ Shift+Enter adds new line
- ✅ Focus indicators visible

---

### Test 9: Mobile Responsiveness

**Goal:** Verify mobile layout

1. Open DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Select iPhone or Android device
4. Test chat interface

**Expected Result:**

- ✅ Messages width adjusts to screen
- ✅ Input remains usable
- ✅ No horizontal scroll
- ✅ Touch targets are large enough

---

### Test 10: Multiple Messages

**Goal:** Verify conversation flow

1. Send 5-6 messages in a row
2. Observe conversation structure

**Expected Result:**

- ✅ Messages alternate left-right
- ✅ Avatars show correctly (User vs Bot)
- ✅ Timestamps are accurate
- ✅ Spacing is consistent
- ✅ No layout breaks

---

## 🐛 Known Limitations (Checkpoint 3)

- ❌ **No streaming** - Response appears all at once (fixed in Checkpoint 4)
- ❌ **No conversation history** - Messages clear on page refresh
- ❌ **No agent status** - Can't see what the agent is doing (added in Checkpoint 4)
- ❌ **No cancel button** - Can't stop ongoing request
- ❌ **No retry** - Must retype message if error occurs

---

## 📊 Performance Checks

### Expected Metrics:

- **Time to Interactive:** < 2 seconds
- **Message Send Latency:** < 500ms (frontend only)
- **Response Time:** Depends on backend (typically 2-10 seconds)
- **Scroll Performance:** 60 FPS smooth scroll
- **Memory Usage:** < 50MB for 100 messages

---

## 🔍 Debug Tips

### Check Browser Console:

```javascript
// View chat store state
window.__ZUSTAND_STORE__; // If devtools enabled

// Check for errors
console.log("Errors in console?");

// Network tab
// Look for POST /api/chat requests
// Verify 200 OK responses
```

### Check Network Tab:

1. Open DevTools → Network
2. Send a message
3. Look for `/api/chat` request
4. Check request payload and response

### Common Issues:

**Problem:** Message not sending

- ✅ Check backend is running (http://localhost:8000)
- ✅ Check console for errors
- ✅ Verify Clerk authentication is working

**Problem:** No AI response

- ✅ Check backend logs for errors
- ✅ Verify documents are uploaded
- ✅ Check BFF route is forwarding correctly

**Problem:** Markdown not rendering

- ✅ Verify `react-markdown` installed
- ✅ Check message has `role: 'assistant'`
- ✅ Inspect DOM for prose classes

---

## ✅ Success Criteria

All tests pass when:

- ✅ Can send and receive messages
- ✅ Markdown renders correctly
- ✅ Citations display properly
- ✅ Auto-scroll works smoothly
- ✅ Input auto-resizes
- ✅ Errors show helpful messages
- ✅ Mobile layout is usable
- ✅ Keyboard navigation works
- ✅ No console errors
- ✅ Build passes with zero warnings

---

**Ready to test!** 🚀

Start both servers:

```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
pnpm run dev
```

Then navigate to: http://localhost:3000/chat
