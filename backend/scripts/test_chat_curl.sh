#!/bin/bash
# test_chat_curl.sh
# Test script for Integration Forge chat endpoint using curl
# Usage: ./scripts/test_chat_curl.sh [streaming|non-streaming]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${API_BASE_URL:-http://localhost:8000}"
CHAT_ENDPOINT="$BASE_URL/api/v1/chat"

# Test mode (default: streaming)
MODE="${1:-streaming}"

echo -e "${GREEN}=== Integration Forge Chat API Test ===${NC}"
echo "Base URL: $BASE_URL"
echo "Mode: $MODE"
echo ""

# ============================================================================
# Test 1: Non-Streaming Chat
# ============================================================================

if [ "$MODE" = "non-streaming" ] || [ "$MODE" = "all" ]; then
    echo -e "${YELLOW}[Test 1] Non-Streaming Chat${NC}"
    echo "Sending request..."
    
    RESPONSE=$(curl -s -X POST "$CHAT_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d '{
            "message": "What is LangGraph? Give a brief answer.",
            "stream": false
        }')
    
    echo "Response:"
    echo "$RESPONSE" | jq '.' || echo "$RESPONSE"
    echo ""
    echo -e "${GREEN}✓ Non-streaming test complete${NC}"
    echo ""
fi

# ============================================================================
# Test 2: Streaming Chat (SSE)
# ============================================================================

if [ "$MODE" = "streaming" ] || [ "$MODE" = "all" ]; then
    echo -e "${YELLOW}[Test 2] Streaming Chat (SSE)${NC}"
    echo "Sending request and listening for events..."
    echo ""
    
    curl -X POST "$CHAT_ENDPOINT" \
        -H "Content-Type: application/json" \
        -N \
        -d '{
            "message": "Explain LangGraph in one sentence.",
            "stream": true
        }' | while IFS= read -r line; do
        # Parse SSE events
        if [[ $line == event:* ]]; then
            EVENT_TYPE=$(echo "$line" | cut -d':' -f2- | xargs)
            echo -e "${GREEN}[EVENT]${NC} $EVENT_TYPE"
        elif [[ $line == data:* ]]; then
            DATA=$(echo "$line" | cut -d':' -f2-)
            echo -e "${YELLOW}[DATA]${NC} $DATA" | jq '.' || echo "$DATA"
        fi
    done
    
    echo ""
    echo -e "${GREEN}✓ Streaming test complete${NC}"
    echo ""
fi

# ============================================================================
# Test 3: Streaming with Thread ID (Conversation Continuity)
# ============================================================================

if [ "$MODE" = "thread" ] || [ "$MODE" = "all" ]; then
    echo -e "${YELLOW}[Test 3] Streaming with Thread ID${NC}"
    
    # Generate a thread ID
    THREAD_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    echo "Thread ID: $THREAD_ID"
    echo ""
    
    # First message
    echo "Message 1: Remember my name is Alice"
    curl -X POST "$CHAT_ENDPOINT" \
        -H "Content-Type: application/json" \
        -N \
        -d "{
            \"message\": \"Remember: my name is Alice\",
            \"stream\": true,
            \"thread_id\": \"$THREAD_ID\"
        }" | while IFS= read -r line; do
        if [[ $line == event:end* ]]; then
            break
        fi
    done
    
    echo ""
    echo "Message 2: What is my name?"
    curl -X POST "$CHAT_ENDPOINT" \
        -H "Content-Type: application/json" \
        -N \
        -d "{
            \"message\": \"What is my name?\",
            \"stream\": true,
            \"thread_id\": \"$THREAD_ID\"
        }" | while IFS= read -r line; do
        if [[ $line == event:* ]]; then
            EVENT_TYPE=$(echo "$line" | cut -d':' -f2- | xargs)
            echo -e "${GREEN}[EVENT]${NC} $EVENT_TYPE"
        elif [[ $line == data:* ]]; then
            DATA=$(echo "$line" | cut -d':' -f2-)
            echo -e "${YELLOW}[DATA]${NC} $DATA"
        fi
    done
    
    echo ""
    echo -e "${GREEN}✓ Thread continuity test complete${NC}"
    echo ""
fi

# ============================================================================
# Test 4: Error Handling
# ============================================================================

if [ "$MODE" = "error" ] || [ "$MODE" = "all" ]; then
    echo -e "${YELLOW}[Test 4] Error Handling${NC}"
    
    # Test 4a: Invalid payload (missing message)
    echo "4a. Missing 'message' field (should return 422):"
    curl -s -X POST "$CHAT_ENDPOINT" \
        -H "Content-Type: application/json" \
        -w "\nHTTP Status: %{http_code}\n" \
        -d '{
            "stream": false
        }' | jq '.' || cat
    echo ""
    
    # Test 4b: Empty message (should return 422)
    echo "4b. Empty message (should return 422):"
    curl -s -X POST "$CHAT_ENDPOINT" \
        -H "Content-Type: application/json" \
        -w "\nHTTP Status: %{http_code}\n" \
        -d '{
            "message": "",
            "stream": false
        }' | jq '.' || cat
    echo ""
    
    echo -e "${GREEN}✓ Error handling tests complete${NC}"
    echo ""
fi

# ============================================================================
# Test 5: Document Endpoints
# ============================================================================

if [ "$MODE" = "documents" ] || [ "$MODE" = "all" ]; then
    echo -e "${YELLOW}[Test 5] Document Endpoints${NC}"
    
    # List documents
    echo "Listing documents..."
    curl -s -X GET "$BASE_URL/api/v1/documents" | jq '.' || cat
    echo ""
    
    # Note: Delete requires a valid document ID
    echo "To test DELETE, run:"
    echo "  curl -X DELETE $BASE_URL/api/v1/documents/<DOCUMENT_ID>"
    echo ""
    
    echo -e "${GREEN}✓ Document endpoint test complete${NC}"
    echo ""
fi

# ============================================================================
# Summary
# ============================================================================

echo -e "${GREEN}=== All Tests Complete ===${NC}"
echo ""
echo "Available modes:"
echo "  ./scripts/test_chat_curl.sh streaming      # Default, SSE streaming"
echo "  ./scripts/test_chat_curl.sh non-streaming  # JSON response"
echo "  ./scripts/test_chat_curl.sh thread         # Conversation continuity"
echo "  ./scripts/test_chat_curl.sh error          # Error handling"
echo "  ./scripts/test_chat_curl.sh documents      # Document endpoints"
echo "  ./scripts/test_chat_curl.sh all            # Run all tests"
echo ""
echo "Tip: Install 'jq' for better JSON formatting (brew install jq)"
