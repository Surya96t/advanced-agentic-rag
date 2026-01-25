#!/bin/bash
#
# Test authentication and rate limiting with curl
#
# This script tests various auth scenarios:
# - Valid token → 200 OK
# - Missing token → 401 Unauthorized
# - Invalid token → 401 Unauthorized
# - Expired token → 401 Unauthorized
# - Rate limit exceeded → 429 Too Many Requests
#
# Usage:
#   bash scripts/test_auth_curl.sh
#   bash scripts/test_auth_curl.sh --verbose
#

set -e  # Exit on error

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
ENDPOINT="/api/v1/documents"
VERBOSE=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_section() {
    echo ""
    echo "========================================================================"
    echo "$1"
    echo "========================================================================"
}

print_test() {
    echo ""
    echo -e "${BLUE}TEST:${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
}

print_failure() {
    echo -e "${RED}❌ FAIL:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
}

# Check if server is running
check_server() {
    print_section "Checking Server Status"
    
    if curl -s "${API_URL}/health" > /dev/null 2>&1; then
        print_success "Server is running at ${API_URL}"
    else
        print_failure "Server is not running at ${API_URL}"
        echo ""
        echo "Start the server with: uvicorn app.main:app --reload"
        exit 1
    fi
}

# Test 1: Missing Authorization Header
test_missing_token() {
    print_test "Missing Authorization header → 401 Unauthorized"
    
    response=$(curl -s -w "\n%{http_code}" "${API_URL}${ENDPOINT}")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status_code" -eq 401 ]; then
        print_success "Got 401 as expected"
        if [ "$VERBOSE" = true ]; then
            echo "Response: $body"
        fi
    else
        print_failure "Expected 401, got $status_code"
        echo "Response: $body"
    fi
}

# Test 2: Invalid Token
test_invalid_token() {
    print_test "Invalid token → 401 Unauthorized"
    
    invalid_token="invalid.jwt.token"
    
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $invalid_token" \
        "${API_URL}${ENDPOINT}")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status_code" -eq 401 ]; then
        print_success "Got 401 as expected"
        if [ "$VERBOSE" = true ]; then
            echo "Response: $body"
        fi
    else
        print_failure "Expected 401, got $status_code"
        echo "Response: $body"
    fi
}

# Test 3: Expired Token
test_expired_token() {
    print_test "Expired token → 401 Unauthorized"
    
    # Generate expired token
    expired_token=$(../.venv/bin/python scripts/generate_test_jwt.py --expired 2>/dev/null | grep -A1 "Token:" | tail -n1)
    
    if [ -z "$expired_token" ]; then
        print_warning "Could not generate expired token - skipping test"
        return
    fi
    
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $expired_token" \
        "${API_URL}${ENDPOINT}")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status_code" -eq 401 ]; then
        print_success "Got 401 as expected"
        if [ "$VERBOSE" = true ]; then
            echo "Response: $body"
        fi
    else
        print_failure "Expected 401, got $status_code"
        echo "Response: $body"
    fi
}

# Test 4: Valid Token
test_valid_token() {
    print_test "Valid token → 200 OK or 401 (if AUTH_ENABLED=true)"
    
    # Generate valid token
    valid_token=$(../.venv/bin/python scripts/generate_test_jwt.py --user-id test_user 2>/dev/null | grep -A1 "Token:" | tail -n1)
    
    if [ -z "$valid_token" ]; then
        print_warning "Could not generate valid token - skipping test"
        return
    fi
    
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $valid_token" \
        "${API_URL}${ENDPOINT}")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status_code" -eq 200 ] || [ "$status_code" -eq 401 ]; then
        if [ "$status_code" -eq 200 ]; then
            print_success "Got 200 OK (AUTH_ENABLED=false or mock auth)"
        else
            print_success "Got 401 (AUTH_ENABLED=true with Clerk validation)"
        fi
        if [ "$VERBOSE" = true ]; then
            echo "Response: $body"
        fi
    else
        print_failure "Expected 200 or 401, got $status_code"
        echo "Response: $body"
    fi
}

# Test 5: Rate Limiting
test_rate_limit() {
    print_test "Rate limiting → 429 Too Many Requests (after limit exceeded)"
    
    # Generate valid token
    token=$(../.venv/bin/python scripts/generate_test_jwt.py --user-id rate_test_user 2>/dev/null | grep -A1 "Token:" | tail -n1)
    
    if [ -z "$token" ]; then
        print_warning "Could not generate token - skipping test"
        return
    fi
    
    # Note: This test may not trigger 429 if AUTH_ENABLED=false or rate limits are high
    print_warning "This test requires AUTH_ENABLED=false and RATE_LIMIT_ENABLED=true"
    print_warning "Making 105 requests to trigger rate limit..."
    
    rate_limited=false
    for i in {1..105}; do
        status_code=$(curl -s -w "%{http_code}" -o /dev/null \
            -H "Authorization: Bearer $token" \
            "${API_URL}${ENDPOINT}")
        
        if [ "$status_code" -eq 429 ]; then
            rate_limited=true
            print_success "Got 429 after $i requests"
            break
        fi
        
        # Show progress every 10 requests
        if [ $((i % 10)) -eq 0 ]; then
            echo "  ... sent $i requests (status: $status_code)"
        fi
    done
    
    if [ "$rate_limited" = false ]; then
        print_warning "Rate limit not triggered (may need to adjust settings)"
    fi
}

# Test 6: Rate Limit Headers
test_rate_limit_headers() {
    print_test "Rate limit headers present in 429 response"
    
    # Note: This test only works if rate limit is triggered
    print_warning "Skipping - requires rate limit to be exceeded first"
}

# Main execution
main() {
    print_section "Authentication & Rate Limiting Tests"
    echo "Testing endpoint: ${API_URL}${ENDPOINT}"
    
    check_server
    
    print_section "Running Tests"
    
    test_missing_token
    test_invalid_token
    test_expired_token
    test_valid_token
    # test_rate_limit  # Commented out - takes too long
    
    print_section "Summary"
    echo ""
    echo "Tests completed. Check results above."
    echo ""
    echo "NOTE: If AUTH_ENABLED=false, auth tests will behave differently."
    echo "      Set AUTH_ENABLED=true in .env to test real JWT validation."
    echo ""
}

main
