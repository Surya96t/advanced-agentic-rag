#!/bin/bash

# ============================================================================
# Apply Migration 008: LangGraph Checkpointer Setup
# ============================================================================
#
# This script applies the LangGraph checkpointer migration to Supabase.
#
# USAGE:
#   chmod +x apply_008.sh
#   ./apply_008.sh
#
# REQUIREMENTS:
#   - psql installed (PostgreSQL client)
#   - SUPABASE_DB_PASSWORD environment variable set
#   - Internet connection to Supabase
# ============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0.32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Migration 008: LangGraph Checkpointer${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo -e "${RED}❌ Error: ../.env file not found${NC}"
    echo "Please create a .env file with SUPABASE_URL and SUPABASE_DB_PASSWORD"
    exit 1
fi

# Load environment variables
set -a
source ../.env
set +a

# Check required environment variables
if [ -z "$SUPABASE_URL" ]; then
    echo -e "${RED}❌ Error: SUPABASE_URL not set in .env${NC}"
    exit 1
fi

if [ -z "$SUPABASE_DB_PASSWORD" ]; then
    echo -e "${RED}❌ Error: SUPABASE_DB_PASSWORD not set in .env${NC}"
    exit 1
fi

# Parse Supabase URL to extract project reference
# Format: https://[project-ref].supabase.co
PROJECT_REF=$(echo "$SUPABASE_URL" | sed -E 's|https://([^.]+)\.supabase\.co.*|\1|')

if [ -z "$PROJECT_REF" ]; then
    echo -e "${RED}❌ Error: Could not extract project reference from SUPABASE_URL${NC}"
    echo "Expected format: https://[project-ref].supabase.co"
    exit 1
fi

echo -e "${YELLOW}📋 Migration Details:${NC}"
echo "   Project: $PROJECT_REF"
echo "   Migration: 008_setup_langgraph_checkpointer.sql"
echo "   Action: Create LangGraph checkpoint tables"
echo ""

# Prompt for confirmation
read -p "Apply migration? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Migration cancelled${NC}"
    exit 0
fi

# Build connection string
# Using Session Pooler (port 5432) for compatibility with psql
USERNAME="postgres.${PROJECT_REF}"
HOST="aws-0-us-west-1.pooler.supabase.com"
PORT="5432"
DATABASE="postgres"

echo -e "${BLUE}🔄 Applying migration...${NC}"

# Apply migration using psql
# -v ON_ERROR_STOP=1: Stop on first error
# -q: Quiet mode (less verbose)
# -f: Read commands from file
PGPASSWORD="$SUPABASE_DB_PASSWORD" psql \
    "postgresql://${USERNAME}:${SUPABASE_DB_PASSWORD}@${HOST}:${PORT}/${DATABASE}?sslmode=require" \
    -v ON_ERROR_STOP=1 \
    -f 008_setup_langgraph_checkpointer.sql

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Migration 008 applied successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📋 Tables created:${NC}"
    echo "   - checkpoints (agent state snapshots)"
    echo "   - checkpoint_writes (state write history)"
    echo "   - checkpoint_blobs (binary data storage)"
    echo ""
    echo -e "${GREEN}✨ LangGraph checkpointer is now ready to use!${NC}"
else
    echo ""
    echo -e "${RED}❌ Migration failed${NC}"
    echo "Check the error messages above for details"
    exit 1
fi
