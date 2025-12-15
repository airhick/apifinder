"""
Configuration file for API key patterns and endpoints
"""
import re

# API Key Patterns - regex patterns to match various API key formats
# Based on official API key schemas - strict matching only
API_KEY_PATTERNS = {
    # OpenAI - Standard Key (Legacy): sk- followed by 48 alphanumeric (51 chars total)
    "openai_standard": [
        re.compile(r'\bsk-[a-zA-Z0-9]{48}\b'),  # Exact match: sk- + 48 chars = 51 total
    ],
    
    # OpenAI - Project Key (New): sk-proj- followed by 48 alphanumeric
    "openai_project": [
        re.compile(r'\bsk-proj-[a-zA-Z0-9]{48}\b'),  # Exact match: sk-proj- + 48 chars
    ],
    
    # Anthropic - Claude API Key: sk-ant-api03- followed by 80+ alphanumeric/dash/underscore
    "anthropic": [
        re.compile(r'\bsk-ant-api03-[a-zA-Z0-9\-_]{80,}\b'),  # Exact match with prefix
    ],
    
    # Google - Gemini / PaLM: AIza followed by 35 alphanumeric/dash/underscore
    "google_gemini": [
        re.compile(r'\bAIza[0-9A-Za-z\-_]{35}\b'),  # Exact match: AIza + 35 chars
    ],
    
    # Hugging Face - User Access Token: hf_ followed by 34 alphanumeric
    "huggingface": [
        re.compile(r'\bhf_[a-zA-Z0-9]{34}\b'),  # Exact match: hf_ + 34 chars
    ],
    
    # Perplexity - API Key: pplx- followed by 40+ alphanumeric
    "perplexity": [
        re.compile(r'\bpplx-[a-zA-Z0-9]{40,}\b'),  # Exact match: pplx- + 40+ chars
    ],
    
    # Cohere - API Key: 40 alphanumeric chars (no prefix)
    # Note: This is tricky as it could match many things. Only match if in context of API key variable
    "cohere": [
        re.compile(r'\b(?:COHERE|cohere)[_-]?API[_-]?KEY[=:]\s*["\']?([a-zA-Z0-9]{40})["\']?', re.IGNORECASE),
    ],
    
    # Pinecone - API Key: UUID v4 format (only match when in context)
    "pinecone": [
        # Only match UUIDs when they're clearly in a Pinecone API key context
        re.compile(r'\b(?:PINECONE|pinecone)[_-]?API[_-]?KEY[=:]\s*["\']?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']?', re.IGNORECASE),
        re.compile(r'\b(?:PINECONE|pinecone)[_-]?KEY[=:]\s*["\']?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']?', re.IGNORECASE),
        re.compile(r'["\']?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']?\s*[=:]\s*(?:PINECONE|pinecone)', re.IGNORECASE),
    ],
    
    # AWS - Access Key ID (keep for compatibility)
    "aws": [
        re.compile(r'\bAKIA[0-9A-Z]{16}\b'),  # AWS Access Key ID
        re.compile(r'\bAWS[_-]?SECRET[_-]?ACCESS[_-]?KEY[=:]\s*["\']?([0-9A-Za-z/+=]{40})["\']?', re.IGNORECASE),
    ],
    
    # GitHub - Personal Access Token (keep for compatibility)
    "github": [
        re.compile(r'\bghp_[0-9a-zA-Z]{36}\b'),  # GitHub Personal Access Token
        re.compile(r'\bgithub_pat_[0-9a-zA-Z]{22}_[0-9a-zA-Z]{59}\b'),  # GitHub Fine-grained Token
    ],
    
    # Stripe (keep for compatibility)
    "stripe": [
        re.compile(r'\bsk_live_[0-9a-zA-Z]{24,}\b'),
        re.compile(r'\bpk_live_[0-9a-zA-Z]{24,}\b'),
    ],
}

# API Validation Endpoints
API_VALIDATION_ENDPOINTS = {
    "openai_standard": "https://api.openai.com/v1/models",
    "openai_project": "https://api.openai.com/v1/models",
    "google_gemini": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
    "huggingface": "https://api-inference.huggingface.co/models",
    "perplexity": "https://api.perplexity.ai/models",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "cohere": "https://api.cohere.ai/v1/models",
    "pinecone": None,  # Pinecone requires special handling
    "aws": None,  # AWS requires special handling
    "github": "https://api.github.com/user",
    "stripe": "https://api.stripe.com/v1/charges",
}

# GitHub Search Queries
GITHUB_SEARCH_QUERIES = [
    # General patterns
    "api key",
    "API_KEY",
    "api_key",
    "secret key",
    "SECRET_KEY",
    "secret_key",
    "access token",
    "ACCESS_TOKEN",
    "access_token",
    "auth token",
    "AUTH_TOKEN",
    "auth_token",
    
    # Service-specific
    "google api key",
    "google veo 3",
    "google gemini",
    "openai api key",
    "openai key",
    "sk-proj-",
    "perplexity api",
    "pplx-",
    "anthropic api",
    "claude api",
    "sk-ant-",
    "aws access key",
    "AKIA",
    "github token",
    "ghp_",
    "stripe key",
    "sk_live_",
    "pk_live_",
    
    # Environment variable patterns
    "process.env",
    "getenv",
    "os.environ",
    "export ",
]

