"""
Test script to verify API key patterns are working correctly
"""
import re
from config import API_KEY_PATTERNS

# Test cases for each pattern
test_cases = {
    "google_api_key": [
        "AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567",
        "GOOGLE_API_KEY=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567",
    ],
    "google_veo3": [
        "GOOGLE_VEO3=test_key_123456789012345678901234567890",
        "veo3_test_key_123456789012345678901234567890",
    ],
    "openai": [
        "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890",
        "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890",
    ],
    "perplexity": [
        "pplx-abcdefghijklmnopqrstuvwxyz1234567890",
        "PERPLEXITY_API_KEY=pplx-abcdefghijklmnopqrstuvwxyz1234567890",
    ],
    "anthropic": [
        "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnop",
        "ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnop",
    ],
    "github": [
        "ghp_abcdefghijklmnopqrstuvwxyz1234567890",
        "github_pat_abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz1234567890",
    ],
    # Stripe test cases removed to avoid GitHub secret scanning
    # Stripe patterns are tested via regex matching in config.py
}

def test_patterns():
    """Test all API key patterns"""
    print("Testing API key patterns...\n")
    
    all_passed = True
    for key_type, patterns in API_KEY_PATTERNS.items():
        if key_type == "generic":
            continue  # Skip generic patterns for now
        
        print(f"Testing {key_type}:")
        if key_type in test_cases:
            for test_case in test_cases[key_type]:
                found = False
                for pattern in patterns:
                    match = pattern.search(test_case)
                    if match:
                        found = True
                        print(f"  ✓ Matched: {test_case[:50]}...")
                        break
                
                if not found:
                    print(f"  ✗ Failed: {test_case[:50]}...")
                    all_passed = False
        else:
            print(f"  (No test cases defined)")
        print()
    
    if all_passed:
        print("✓ All pattern tests passed!")
    else:
        print("✗ Some pattern tests failed!")
    
    return all_passed

if __name__ == "__main__":
    test_patterns()

