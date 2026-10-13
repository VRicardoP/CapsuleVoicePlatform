#!/bin/bash
# =============================================================================
# SferaAI Backend Integration Tests Runner
# =============================================================================
#
# This script runs integration tests for the backend against PostgreSQL.
#
# Requirements:
# - PostgreSQL database with sferaai.sql schema loaded
# - Python 3.12+ with pytest, pytest-asyncio installed
# - Environment variables set (or defaults used)
#
# Usage:
#   ./tests/run_integration_tests.sh [options]
#
# Options:
#   -v          Verbose output
#   -x          Stop on first failure
#   --cov       Generate coverage report
#   <pattern>   Run specific tests matching pattern
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  SferaAI Backend Integration Tests${NC}"
echo -e "${BLUE}=============================================${NC}"

# =============================================================================
# Environment Configuration
# =============================================================================

# Database configuration (can be overridden by environment)
export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+asyncpg://postgres:postgres@localhost:5432/sfera}"

# KMS keys for encryption tests
export TEST_KMS_MASTER_KEY="${TEST_KMS_MASTER_KEY:-test_master_key_32_characters_!}"
export TEST_AUDIT_HMAC_KEY="${TEST_AUDIT_HMAC_KEY:-test_hmac_key_32_characters_ok!}"

# Python path
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Database: ${TEST_DATABASE_URL%@*}@***"
echo "  Backend dir: $BACKEND_DIR"
echo ""

# =============================================================================
# Pre-flight Checks
# =============================================================================

echo -e "${YELLOW}Running pre-flight checks...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "  Python version: $PYTHON_VERSION"

# Check pytest
if ! python3 -c "import pytest" &> /dev/null; then
    echo -e "${RED}Error: pytest not installed. Run: pip install pytest pytest-asyncio${NC}"
    exit 1
fi

# Check pytest-asyncio
if ! python3 -c "import pytest_asyncio" &> /dev/null; then
    echo -e "${RED}Error: pytest-asyncio not installed. Run: pip install pytest-asyncio${NC}"
    exit 1
fi

# Check database connectivity
echo "  Checking database connection..."
if ! python3 -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import os

async def check_db():
    url = os.getenv('TEST_DATABASE_URL')
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT 1'))
        assert result.scalar() == 1
    await engine.dispose()

asyncio.run(check_db())
" 2>/dev/null; then
    echo -e "${RED}Error: Cannot connect to database${NC}"
    echo "  Please ensure PostgreSQL is running and accessible"
    echo "  Database URL: ${TEST_DATABASE_URL%@*}@***"
    exit 1
fi
echo -e "  ${GREEN}Database connection OK${NC}"

# Check if schema is loaded
echo "  Checking schema..."
if ! python3 -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import os

async def check_schema():
    url = os.getenv('TEST_DATABASE_URL')
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        # Check for key tables
        result = await conn.execute(text('''
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name IN ('users', 'audit_log', 'data_subject_requests', 'robinson_checks')
        '''))
        count = result.scalar()
        assert count >= 4, f'Schema incomplete: only {count}/4 key tables found'
    await engine.dispose()

asyncio.run(check_schema())
" 2>/dev/null; then
    echo -e "${RED}Error: Database schema not loaded${NC}"
    echo "  Please run: psql -d sfera -f sferaai.sql"
    exit 1
fi
echo -e "  ${GREEN}Schema check OK${NC}"

echo ""

# =============================================================================
# Parse Arguments
# =============================================================================

PYTEST_ARGS=""
VERBOSE=""
COVERAGE=""
PATTERN=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -x|--exitfirst)
            PYTEST_ARGS="$PYTEST_ARGS -x"
            shift
            ;;
        --cov|--coverage)
            COVERAGE="--cov=app --cov-report=html --cov-report=term"
            shift
            ;;
        *)
            PATTERN="$PATTERN $1"
            shift
            ;;
    esac
done

# =============================================================================
# Run Tests
# =============================================================================

cd "$BACKEND_DIR"

echo -e "${BLUE}Running integration tests...${NC}"
echo ""

# Build pytest command
PYTEST_CMD="python3 -m pytest tests/integration/ $VERBOSE $PYTEST_ARGS $COVERAGE"

if [ -n "$PATTERN" ]; then
    PYTEST_CMD="$PYTEST_CMD -k \"$PATTERN\""
fi

# Add standard options
PYTEST_CMD="$PYTEST_CMD --tb=short --asyncio-mode=auto"

echo "Command: $PYTEST_CMD"
echo ""

# Run tests
if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}=============================================${NC}"
    echo -e "${GREEN}  All integration tests PASSED${NC}"
    echo -e "${GREEN}=============================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}=============================================${NC}"
    echo -e "${RED}  Some tests FAILED${NC}"
    echo -e "${RED}=============================================${NC}"
    exit 1
fi
