#!/bin/bash
# Apply migration 007: Add document_title to search functions

set -e

# Load environment variables
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# Check if SUPABASE_URL and SUPABASE_SERVICE_KEY are set
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo "Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"
    exit 1
fi

echo "Applying migration 007..."
echo "Database: $SUPABASE_URL"

# Execute migration using psql or supabase CLI
# For now, we'll use curl to execute via Supabase REST API
# In production, use psql or Supabase CLI

SQL_FILE="007_add_document_title_to_search.sql"

if [ ! -f "$SQL_FILE" ]; then
    echo "Error: Migration file $SQL_FILE not found"
    exit 1
fi

echo "Migration file found: $SQL_FILE"
echo ""
echo "To apply this migration, run it manually in your Supabase SQL Editor:"
echo "1. Go to https://supabase.com/dashboard/project/YOUR_PROJECT_ID/sql/new"
echo "2. Copy and paste the contents of $SQL_FILE"
echo "3. Click 'Run'"
echo ""
echo "Or use psql:"
echo "psql \$DATABASE_URL < $SQL_FILE"
