#!/bin/bash
# Test script for webhook - simulates what the program sends

# Test working key webhook
echo "Testing working key webhook..."
curl -X POST https://n8n.goreview.fr/webhook-test/workingkey \
  -H "Content-Type: application/json" \
  -d '{
    "key": "sk-test123456789012345678901234567890123456789012345",
    "key_type": "openai_standard",
    "company": "OpenAI",
    "is_working": true,
    "message": "Valid API key found"
  }'

echo -e "\n\n"

# Test found key webhook (non-working)
echo "Testing found key webhook (non-working)..."
curl -X POST https://n8n.goreview.fr/webhook-test/apikey \
  -H "Content-Type: application/json" \
  -d '{
    "key": "sk-test123456789012345678901234567890123456789012345",
    "key_type": "openai_standard",
    "company": "OpenAI",
    "is_working": false,
    "message": "API key found"
  }'

echo -e "\n\nDone!"

