#!/bin/bash
# System Integration Test
# Tests all components of the AI Systems Starter

set -e  # Exit on error

echo "AI Systems Starter - System Test"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

test_service() {
    local name=$1
    local command=$2

    echo -n "Testing $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC}"
        ((TESTS_FAILED++))
    fi
}

echo "1. Docker Services"
test_service "PostgreSQL" "docker exec ai-systems-postgres pg_isready -U postgres"
test_service "Redis" "docker exec ai-systems-redis redis-cli ping"
test_service "Weaviate" "curl -sf http://localhost:8080/v1/.well-known/ready"
test_service "MinIO" "curl -sf http://localhost:9000/minio/health/live"
test_service "Ollama" "curl -sf http://localhost:11434"
test_service "RedisInsight" "curl -sf http://localhost:5540"
echo ""

echo "2. Database Connectivity"
test_service "PostgreSQL Connection" "docker exec ai-systems-postgres psql -U postgres -d ai_systems -c 'SELECT 1'"
test_service "Redis Connection" "docker exec ai-systems-redis redis-cli SET test_key test_value"
test_service "Weaviate Schema" "curl -sf http://localhost:8080/v1/schema"
echo ""

echo "3. Python Environment"
source venv/bin/activate 2>/dev/null || true
test_service "Python Version" "python --version | grep '3.11'"
test_service "Weaviate Client" "python -c 'from backend.plugins.vector_dbs.weaviate_db import WeaviateDB'"
test_service "Embedding Service" "python -c 'from backend.services.embedding_service import EmbeddingService'"
test_service "Database Client" "python -c 'from backend.core.database import get_db_session'"
echo ""

echo "4. Vector Database"
test_service "Weaviate Test" "python -m backend.tests.test_weaviate_fix 2>&1 | grep -q 'TEST COMPLETE'"
echo ""

echo "Test Summary"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi
