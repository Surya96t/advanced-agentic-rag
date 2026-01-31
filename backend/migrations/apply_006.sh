#!/bin/bash

# Apply migration 006: Add full_name column to users table
# This script applies the migration to add the full_name column

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATION_FILE="$SCRIPT_DIR/006_add_full_name_to_users.sql"

echo "================================================"
echo "Applying Migration 006: Add full_name to users"
echo "================================================"

# Check if .env exists
if [ ! -f "$SCRIPT_DIR/../.env" ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env file with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
    exit 1
fi

# Load environment variables
export $(cat "$SCRIPT_DIR/../.env" | grep -v '^#' | xargs)

# Check required variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "❌ Error: Missing required environment variables"
    echo "Required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY"
    exit 1
fi

# Extract database connection details from Supabase URL
# Format: https://[project-ref].supabase.co
PROJECT_REF=$(echo "$SUPABASE_URL" | sed -E 's|https://([^.]+)\.supabase\.co.*|\1|')

if [ -z "$PROJECT_REF" ]; then
    echo "❌ Error: Could not extract project reference from SUPABASE_URL"
    exit 1
fi

echo ""
echo "📋 Migration Details:"
echo "   Project: $PROJECT_REF"
echo "   File: 006_add_full_name_to_users.sql"
echo ""
echo "⚠️  MANUAL STEP REQUIRED:"
echo ""
echo "Please follow these steps to apply the migration:"
echo ""
echo "1. Open Supabase Dashboard:"
echo "   https://supabase.com/dashboard/project/$PROJECT_REF"
echo ""
echo "2. Navigate to: SQL Editor (left sidebar)"
echo ""
echo "3. Create a new query"
echo ""
echo "4. Copy and paste the following SQL:"
echo ""
cat "$MIGRATION_FILE"
echo ""
echo "5. Click 'Run' or press Cmd/Ctrl + Enter"
echo ""
echo "6. Verify success - you should see 'Success. No rows returned'"
echo ""
echo "================================================"
