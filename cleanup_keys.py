"""
Script to clean up found_api_keys.txt - remove keys that don't match valid API key patterns
"""
import re
from config import API_KEY_PATTERNS

def is_valid_api_key(key):
    """
    Check if a key matches a valid API key pattern
    """
    key_clean = key.strip('"\'').strip()
    
    # Skip empty or too short
    if not key_clean or len(key_clean) < 20:
        return False
    
    # Skip hashes
    if key_clean.lower().startswith(('sha', 'md5', 'base64')):
        return False
    
    # Test each pattern type
    for key_type, patterns in API_KEY_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(key_clean)
            if match:
                # Extract the key from match groups if available
                if match.groups():
                    extracted_key = match.group(1)
                    if extracted_key == key_clean or key_clean in extracted_key:
                        # Validate format
                        return validate_key_format(key_clean, key_type)
                else:
                    # Full match - check if it matches exactly
                    matched = match.group(0)
                    if matched == key_clean or matched.strip('"\'') == key_clean:
                        return validate_key_format(key_clean, key_type)
    
    return False

def validate_key_format(key, key_type):
    """
    Validate that the key matches the expected format for its type
    """
    if key_type == 'openai_standard' and len(key) == 51 and key.startswith('sk-'):
        return True
    elif key_type == 'openai_project' and key.startswith('sk-proj-') and len(key) >= 57:
        return True
    elif key_type == 'anthropic' and key.startswith('sk-ant-api03-') and len(key) >= 95:
        return True
    elif key_type == 'google_gemini' and key.startswith('AIza') and len(key) == 39:
        return True
    elif key_type == 'huggingface' and key.startswith('hf_') and len(key) == 37:
        return True
    elif key_type == 'perplexity' and key.startswith('pplx-') and len(key) >= 45:
        return True
    elif key_type == 'cohere' and len(key) == 40:
        return True
    elif key_type == 'pinecone' and len(key) == 36 and '-' in key:
        # Only valid if it was found in context (we can't check that here, so be conservative)
        # Actually, since we updated patterns, standalone UUIDs shouldn't match anymore
        return True
    elif key_type == 'aws' and (key.startswith('AKIA') or len(key) == 40):
        return True
    elif key_type == 'github' and (key.startswith('ghp_') or key.startswith('github_pat_')):
        return True
    elif key_type == 'stripe' and (key.startswith('sk_live_') or key.startswith('pk_live_')):
        return True
    
    return False

def cleanup_keys():
    """
    Clean up found_api_keys.txt - keep only valid API keys
    """
    print("🧹 Cleaning up found_api_keys.txt...")
    
    # Read all keys
    try:
        with open("found_api_keys.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("❌ found_api_keys.txt not found!")
        return
    
    valid_keys = []
    invalid_count = 0
    
    for line in lines:
        key = line.strip()
        # Skip empty lines and comments
        if not key or key.startswith('#'):
            continue
        
        if is_valid_api_key(key):
            valid_keys.append(key)
        else:
            invalid_count += 1
    
    # Write cleaned keys
    with open("found_api_keys.txt", "w", encoding="utf-8") as f:
        for key in valid_keys:
            f.write(f"{key}\n")
    
    print(f"✅ Cleanup complete!")
    print(f"   Total keys: {len(lines)}")
    print(f"   Valid keys: {len(valid_keys)}")
    print(f"   Removed invalid: {invalid_count}")
    print(f"\n💾 Cleaned keys saved to found_api_keys.txt")

if __name__ == "__main__":
    cleanup_keys()

