#!/bin/bash
# Quick API Test Script for Task Manager PRO

BASE_URL="http://localhost:8000"

echo "🚀 Task Manager PRO - Quick API Test"
echo "====================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Health Check
echo -e "${YELLOW}1. Health Check${NC}"
curl -s $BASE_URL/health | python3 -m json.tool
echo -e "\n"

# 2. Register User
echo -e "${YELLOW}2. Register User${NC}"
REGISTER_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!"
  }')
echo $REGISTER_RESPONSE | python3 -m json.tool
echo -e "\n"

# 3. Login
echo -e "${YELLOW}3. Login & Get Token${NC}"
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!"
  }')

echo $LOGIN_RESPONSE | python3 -m json.tool

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}Failed to get token. User might already exist - trying to login with existing credentials${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Token acquired${NC}"
echo -e "\n"

# 4. Create Task
echo -e "${YELLOW}4. Create Task${NC}"
TASK_RESPONSE=$(curl -s -X POST $BASE_URL/api/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Test API Integration",
    "description": "Testing the Task Manager PRO API",
    "due_date": "2026-12-31",
    "priority": "high"
  }')

echo $TASK_RESPONSE | python3 -m json.tool
TASK_ID=$(echo $TASK_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
echo -e "\n"

# 5. List Tasks
echo -e "${YELLOW}5. List All Tasks${NC}"
curl -s -X GET $BASE_URL/api/tasks \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

# 6. Get Current User
echo -e "${YELLOW}6. Get Current User Info${NC}"
curl -s -X GET $BASE_URL/api/users/me \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

echo -e "${GREEN}✅ All tests completed!${NC}"
echo -e "\n📚 Visit http://localhost:8000/api/docs for interactive documentation"
