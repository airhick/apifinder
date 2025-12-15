"""
API Key Validator - Tests found API keys against their respective APIs
"""
import requests
import time
from typing import Dict, List, Tuple
from config import API_VALIDATION_ENDPOINTS
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KeyValidator:
    def __init__(self):
        self.valid_keys: Dict[str, List[Tuple[str, bool, str]]] = {}
        self.invalid_keys: Dict[str, List[str]] = {}
    
    def validate_google_gemini(self, key: str) -> Tuple[bool, str]:
        """Validate Google Gemini API key"""
        try:
            headers = {"X-Goog-Api-Key": key}
            response = requests.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return True, "Valid Google Gemini key"
            elif response.status_code == 403:
                return False, "Invalid or restricted key"
            else:
                return False, f"Status: {response.status_code}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def validate_openai(self, key: str) -> Tuple[bool, str]:
        """Validate OpenAI API key"""
        try:
            headers = {"Authorization": f"Bearer {key}"}
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return True, "Valid OpenAI key"
            elif response.status_code == 401:
                return False, "Invalid key"
            else:
                return False, f"Status: {response.status_code}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def validate_anthropic(self, key: str) -> Tuple[bool, str]:
        """Validate Anthropic API key"""
        try:
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            # Simple validation request
            response = requests.get(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                timeout=10
            )
            # 400 is expected for GET, but means key is valid
            if response.status_code in [200, 400, 404]:
                return True, "Valid Anthropic key"
            elif response.status_code == 401:
                return False, "Invalid key"
            else:
                return False, f"Status: {response.status_code}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def validate_huggingface(self, key: str) -> Tuple[bool, str]:
        """Validate Hugging Face API key"""
        try:
            headers = {"Authorization": f"Bearer {key}"}
            response = requests.get(
                "https://api-inference.huggingface.co/models",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return True, "Valid Hugging Face key"
            elif response.status_code == 401:
                return False, "Invalid Hugging Face key"
            else:
                return False, f"Status: {response.status_code}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def validate_cohere(self, key: str) -> Tuple[bool, str]:
        """Validate Cohere API key"""
        try:
            headers = {"Authorization": f"Bearer {key}"}
            response = requests.get(
                "https://api.cohere.ai/v1/models",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return True, "Valid Cohere key"
            elif response.status_code == 401:
                return False, "Invalid Cohere key"
            else:
                return False, f"Status: {response.status_code}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def validate_pinecone(self, key: str) -> Tuple[bool, str]:
        """Validate Pinecone API key (format check only)"""
        # Pinecone keys can be UUID format or pc- prefix format
        import re
        uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)
        pc_prefix_pattern = re.compile(r'^pc-[a-zA-Z0-9\-_]{20,}$', re.IGNORECASE)
        
        if uuid_pattern.match(key):
            return True, "Valid Pinecone key format (UUID)"
        elif pc_prefix_pattern.match(key):
            return True, "Valid Pinecone key format (pc- prefix)"
        else:
            return False, "Invalid Pinecone key format"
    
    def validate_key(self, key_type: str, key: str) -> Tuple[bool, str]:
        """
        Validate a single API key based on its type
        
        Args:
            key_type: Type of API key
            key: The API key to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        validation_methods = {
            "google_gemini": self.validate_google_gemini,
            "openai": self.validate_openai,
            "openai_standard": self.validate_openai,  # Use same validator
            "openai_project": self.validate_openai,  # Use same validator
            "anthropic": self.validate_anthropic,
            "huggingface": self.validate_huggingface,
            "cohere": self.validate_cohere,
            "pinecone": self.validate_pinecone,
        }
        
        if key_type in validation_methods:
            return validation_methods[key_type](key)
        else:
            return False, "No validation method available"
    
    def validate_all_keys(self, found_keys: Dict[str, set]) -> Dict[str, List[Tuple[str, bool, str]]]:
        """
        Validate all found API keys
        
        Args:
            found_keys: Dictionary of key types to sets of keys
            
        Returns:
            Dictionary of validation results
        """
        logger.info("Starting key validation...")
        
        total_keys = sum(len(keys) for keys in found_keys.values())
        logger.info(f"Total keys to validate: {total_keys}")
        
        with tqdm(total=total_keys, desc="Validating keys") as pbar:
            for key_type, keys in found_keys.items():
                if not keys:
                    continue
                
                logger.info(f"Validating {len(keys)} {key_type} keys...")
                self.valid_keys[key_type] = []
                self.invalid_keys[key_type] = []
                
                for key in keys:
                    is_valid, message = self.validate_key(key_type, key)
                    
                    if is_valid:
                        self.valid_keys[key_type].append((key, True, message))
                        logger.info(f"✓ Valid {key_type} key found!")
                    else:
                        self.invalid_keys[key_type].append(key)
                    
                    pbar.update(1)
                    
                    # Rate limiting
                    time.sleep(0.5)
        
        # Print summary
        total_valid = sum(len(keys) for keys in self.valid_keys.values())
        total_invalid = sum(len(keys) for keys in self.invalid_keys.values())
        
        logger.info(f"\nValidation complete!")
        logger.info(f"Valid keys: {total_valid}")
        logger.info(f"Invalid keys: {total_invalid}")
        
        return self.valid_keys
    
    def get_results(self) -> Tuple[Dict[str, List[Tuple[str, bool, str]]], Dict[str, List[str]]]:
        """Get validation results"""
        return self.valid_keys, self.invalid_keys

