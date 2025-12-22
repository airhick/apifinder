"""
Configuration file for API key patterns and endpoints
"""
import re

# API Key Patterns - regex patterns to match specified API key formats only
# Focused on: OpenAI, Anthropic, Google Gemini, Hugging Face, Cohere, Pinecone
API_KEY_PATTERNS = {
    # OpenAI - Standard Key: sk- followed by 48 alphanumeric characters (51 chars total)
    "openai_standard": [
        re.compile(r'\bsk-[a-zA-Z0-9]{48}\b'),  # sk- + 48 alphanumeric = 51 total
    ],
    
    # OpenAI - Project Key: sk-proj- followed by 48 alphanumeric characters
    "openai_project": [
        re.compile(r'\bsk-proj-[a-zA-Z0-9]{48}\b'),  # sk-proj- + 48 alphanumeric
    ],
    
    # Anthropic - Claude API Key: sk-ant- followed by alphanumeric characters
    "anthropic": [
        re.compile(r'\bsk-ant-[a-zA-Z0-9\-_]{20,}\b'),  # sk-ant- + alphanumeric/dash/underscore
        re.compile(r'\bsk-ant-api03-[a-zA-Z0-9\-_]{20,}\b'),  # Also match api03 variant
    ],
    
    # Google Gemini - API Key: AIza followed by 35 alphanumeric characters (39 chars total)
    "google_gemini": [
        re.compile(r'\bAIza[0-9A-Za-z\-_]{35}\b'),  # AIza + 35 chars = 39 total
    ],
    
    # Hugging Face - Access Token: hf_ followed by 34 alphanumeric characters
    "huggingface": [
        re.compile(r'\bhf_[a-zA-Z0-9]{34}\b'),  # hf_ + 34 alphanumeric
    ],
    
    # Cohere - API Key: 40-character alphanumeric string (no specific prefix)
    # Match only when in context of Cohere API key variable names
    "cohere": [
        re.compile(r'\b(?:COHERE|cohere)[_-]?API[_-]?KEY[=:]\s*["\']?([a-zA-Z0-9]{40})["\']?', re.IGNORECASE),
        re.compile(r'\b(?:COHERE|cohere)[_-]?KEY[=:]\s*["\']?([a-zA-Z0-9]{40})["\']?', re.IGNORECASE),
        re.compile(r'["\']?([a-zA-Z0-9]{40})["\']?\s*[=:]\s*(?:COHERE|cohere)', re.IGNORECASE),
    ],
    
    # Pinecone - API Key: pc- prefix or UUID-style format
    "pinecone": [
        # Match pc- prefix format
        re.compile(r'\bpc-[a-zA-Z0-9\-_]{20,}\b'),
        # Match UUID format when in Pinecone context
        re.compile(r'\b(?:PINECONE|pinecone)[_-]?API[_-]?KEY[=:]\s*["\']?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']?', re.IGNORECASE),
        re.compile(r'\b(?:PINECONE|pinecone)[_-]?KEY[=:]\s*["\']?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']?', re.IGNORECASE),
        re.compile(r'["\']?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']?\s*[=:]\s*(?:PINECONE|pinecone)', re.IGNORECASE),
    ],
    
    # Perplexity - API Key: pplx- prefix followed by alphanumeric characters
    "perplexity": [
        re.compile(r'\bpplx-[a-zA-Z0-9]{32,}\b'),  # pplx- + alphanumeric
        re.compile(r'\b(?:PERPLEXITY|perplexity)[_-]?API[_-]?KEY[=:]\s*["\']?(pplx-[a-zA-Z0-9]{32,})["\']?', re.IGNORECASE),
        re.compile(r'\b(?:PERPLEXITY|perplexity)[_-]?KEY[=:]\s*["\']?(pplx-[a-zA-Z0-9]{32,})["\']?', re.IGNORECASE),
    ],
    
    # Mistral AI - API Key: alphanumeric string, typically starts with specific patterns
    "mistral": [
        re.compile(r'\b(?:MISTRAL|mistral)[_-]?API[_-]?KEY[=:]\s*["\']?([a-zA-Z0-9]{32,})["\']?', re.IGNORECASE),
        re.compile(r'\b(?:MISTRAL|mistral)[_-]?KEY[=:]\s*["\']?([a-zA-Z0-9]{32,})["\']?', re.IGNORECASE),
        # Common Mistral key format (if known pattern exists)
        re.compile(r'\b([a-zA-Z0-9]{40,})\b.*(?:mistral|MISTRAL)', re.IGNORECASE),
    ],
    
    # Groq - API Key: gsk_ prefix followed by alphanumeric characters
    "groq": [
        re.compile(r'\bgsk_[a-zA-Z0-9]{32,}\b'),  # gsk_ + alphanumeric
        re.compile(r'\b(?:GROQ|groq)[_-]?API[_-]?KEY[=:]\s*["\']?(gsk_[a-zA-Z0-9]{32,})["\']?', re.IGNORECASE),
        re.compile(r'\b(?:GROQ|groq)[_-]?KEY[=:]\s*["\']?(gsk_[a-zA-Z0-9]{32,})["\']?', re.IGNORECASE),
    ],
}

# API Validation Endpoints
API_VALIDATION_ENDPOINTS = {
    "openai_standard": "https://api.openai.com/v1/models",
    "openai_project": "https://api.openai.com/v1/models",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "google_gemini": "https://generativelanguage.googleapis.com/v1beta/models",
    "huggingface": "https://api-inference.huggingface.co/models",
    "cohere": "https://api.cohere.ai/v1/models",
    "pinecone": None,  # Pinecone requires special handling
    "perplexity": "https://api.perplexity.ai/models",
    "mistral": "https://api.mistral.ai/v1/models",
    "groq": "https://api.groq.com/openai/v1/models",
}

# GitHub Search Queries - Focused on target API key types
GITHUB_SEARCH_QUERIES = [
    # General patterns
    "api key",
    "API_KEY",
    "api_key",
    "access token",
    "ACCESS_TOKEN",
    "access_token",
    
    # OpenAI specific
    "openai api key",
    "openai key",
    "sk-proj-",
    "sk-",
    "OPENAI_API_KEY",
    
    # Anthropic specific
    "anthropic api",
    "claude api",
    "sk-ant-",
    "ANTHROPIC_API_KEY",
    
    # Google Gemini specific
    "google gemini",
    "google api key",
    "AIza",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    
    # Hugging Face specific
    "hugging face token",
    "hf_",
    "HUGGINGFACE_TOKEN",
    "HF_TOKEN",
    
    # Cohere specific
    "cohere api",
    "cohere key",
    "COHERE_API_KEY",
    
    # Pinecone specific
    "pinecone api",
    "pinecone key",
    "pc-",
    "PINECONE_API_KEY",
    
    # Perplexity specific
    "perplexity api",
    "perplexity key",
    "pplx-",
    "PERPLEXITY_API_KEY",
    
    # Mistral AI specific
    "mistral api",
    "mistral key",
    "MISTRAL_API_KEY",
    
    # Groq specific
    "groq api",
    "groq key",
    "gsk_",
    "GROQ_API_KEY",
    
    # Environment variable patterns
    "process.env",
    "getenv",
    "os.environ",
    "export ",
]

