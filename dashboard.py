from flask import Flask, render_template, jsonify, request
import re
import json
import requests
from datetime import datetime
import urllib3
from requests.exceptions import SSLError

# Disable SSL warnings for requests with verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

def parse_api_keys_file():
    """Parse working_api_keys.txt and extract all API keys with metadata."""
    keys = []
    try:
        with open("working_api_keys.txt", "r") as f:
            content = f.read()
        
        # Split by separator
        sections = content.split("=" * 60)
        
        for section in sections:
            if not section.strip():
                continue
            
            key_data = {}
            lines = section.strip().split("\n")
            
            for line in lines:
                if line.startswith("Service:"):
                    key_data["service"] = line.replace("Service:", "").strip()
                elif line.startswith("API Key:"):
                    key_data["key"] = line.replace("API Key:", "").strip()
                elif line.startswith("Repository:"):
                    key_data["repository"] = line.replace("Repository:", "").strip()
                elif line.startswith("File:"):
                    key_data["file"] = line.replace("File:", "").strip()
                elif line.startswith("Timestamp:"):
                    key_data["timestamp"] = line.replace("Timestamp:", "").strip()
            
            if "service" in key_data and "key" in key_data:
                key_data["id"] = len(keys)  # Simple ID for tracking
                keys.append(key_data)
        
        return keys
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error parsing API keys file: {e}")
        return []

# Import validation functions from request.py
import sys
import importlib.util

# Load validation functions from request.py
spec = importlib.util.spec_from_file_location("request_module", "request.py")
request_module = importlib.util.module_from_spec(spec)
sys.modules["request_module"] = request_module
spec.loader.exec_module(request_module)

# Service-specific API endpoints and request details (AI companies only)
SERVICE_ENDPOINTS = {
    # AI Companies - Text Generation
    "OpenAI": {
        "url": "https://api.openai.com/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "method": "POST",
        "headers": lambda key: {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
    },
    "Cohere": {
        "url": "https://api.cohere.ai/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Hugging Face": {
        "url": "https://huggingface.co/api/whoami",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"}
    },
    "Perplexity AI": {
        "url": "https://api.perplexity.ai/chat/completions",
        "method": "POST",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Together AI": {
        "url": "https://api.together.xyz/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Groq": {
        "url": "https://api.groq.com/openai/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Mistral AI": {
        "url": "https://api.mistral.ai/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "AI21 Labs": {
        "url": "https://api.ai21.com/studio/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    # AI Companies - Image Generation
    "Stability AI": {
        "url": "https://api.stability.ai/v1/user/account",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Replicate": {
        "url": "https://api.replicate.com/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Token {key}"}
    },
    "Leonardo AI": {
        "url": "https://cloud.leonardo.ai/api/rest/v1/me",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    # AI Companies - Video Generation
    "Runway ML": {
        "url": "https://api.runwayml.com/v1/account",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Pika Labs": {
        "url": "https://api.pika.art/v1/user",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    # AI Companies - Speech/Audio
    "ElevenLabs": {
        "url": "https://api.elevenlabs.io/v1/user",
        "method": "GET",
        "headers": lambda key: {"xi-api-key": key}
    },
    "Deepgram": {
        "url": "https://api.deepgram.com/v1/projects",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Token {key}"}
    },
    "AssemblyAI": {
        "url": "https://api.assemblyai.com/v2/transcript",
        "method": "GET",
        "headers": lambda key: {"authorization": key}
    },
    # AI Companies - Google AI
    "Google Gemini": {
        "url": "https://generativelanguage.googleapis.com/v1/models",
        "method": "GET",
        "headers": lambda key: {},
        "params": lambda key: {"key": key}
    },
    # AI Companies - Other
    "Aleph Alpha": {
        "url": "https://api.aleph-alpha.com/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Character.AI": {
        "url": "https://beta.character.ai/api/user",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Jasper AI": {
        "url": "https://api.jasper.ai/v1/user",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Copy.ai": {
        "url": "https://api.copy.ai/v1/user",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    # AI Companies - Google AI Services
    "Google Vertex AI": {
        "url": "https://aiplatform.googleapis.com/v1/projects",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"}
    },
}

def generate_curl_command(request_details, service, key):
    """Generate curl command from request details."""
    if not request_details or not request_details.get('method') or not request_details.get('url'):
        return None
    
    method = request_details['method']
    url = request_details['url']
    headers = request_details.get('headers', {})
    params = request_details.get('params')
    auth = request_details.get('auth')
    
    curl_parts = ['curl']
    
    # Add method
    if method != 'GET':
        curl_parts.append(f'-X {method}')
    
    # Add headers
    for header_name, header_value in headers.items():
        # Escape single quotes in header values
        escaped_value = str(header_value).replace("'", "'\\''")
        curl_parts.append(f"-H '{header_name}: {escaped_value}'")
    
    # Add auth
    if auth and isinstance(auth, tuple):
        curl_parts.append(f"-u '{auth[0]}:{auth[1]}'")
    
    # Add URL with params if GET
    if method == 'GET' and params:
        import urllib.parse
        url_with_params = url + '?' + urllib.parse.urlencode(params)
        curl_parts.append(f"'{url_with_params}'")
    else:
        curl_parts.append(f"'{url}'")
    
    return ' '.join(curl_parts)

def generate_python_request(request_details, service, key):
    """Generate Python requests code from request details."""
    if not request_details or not request_details.get('method') or not request_details.get('url'):
        return None
    
    method = request_details['method'].lower()
    url = request_details['url']
    headers = request_details.get('headers', {})
    params = request_details.get('params')
    auth = request_details.get('auth')
    
    code_parts = ['import requests', '']
    
    # Build request
    if method == 'get':
        if params:
            code_parts.append(f"url = '{url}'")
            code_parts.append(f"headers = {repr(headers)}")
            code_parts.append(f"params = {repr(params)}")
            code_parts.append('response = requests.get(url, headers=headers, params=params, timeout=10)')
        elif auth:
            code_parts.append(f"url = '{url}'")
            code_parts.append(f"headers = {repr(headers)}")
            code_parts.append(f"auth = {repr(auth)}")
            code_parts.append('response = requests.get(url, headers=headers, auth=auth, timeout=10)')
        else:
            code_parts.append(f"url = '{url}'")
            code_parts.append(f"headers = {repr(headers)}")
            code_parts.append('response = requests.get(url, headers=headers, timeout=10)')
    elif method == 'post':
        if auth:
            code_parts.append(f"url = '{url}'")
            code_parts.append(f"headers = {repr(headers)}")
            code_parts.append(f"auth = {repr(auth)}")
            code_parts.append('response = requests.post(url, headers=headers, auth=auth, timeout=10)')
        else:
            code_parts.append(f"url = '{url}'")
            code_parts.append(f"headers = {repr(headers)}")
            code_parts.append('response = requests.post(url, headers=headers, timeout=10)')
    
    code_parts.append('')
    code_parts.append('print(f"Status: {response.status_code}")')
    code_parts.append('print(response.json())')
    
    return '\n'.join(code_parts)

def generate_javascript_fetch(request_details, service, key):
    """Generate JavaScript fetch code from request details."""
    if not request_details or not request_details.get('method') or not request_details.get('url'):
        return None
    
    method = request_details['method']
    url = request_details['url']
    headers = request_details.get('headers', {})
    params = request_details.get('params')
    
    # Build URL with params
    full_url = url
    if params:
        import urllib.parse
        full_url = url + '?' + urllib.parse.urlencode(params)
    
    code_parts = []
    code_parts.append('fetch(\'' + full_url + '\', {')
    code_parts.append(f"  method: '{method}',")
    code_parts.append('  headers: ' + json.dumps(headers, indent=2).replace('\n', '\n  '))
    code_parts.append('})')
    code_parts.append('  .then(response => response.json())')
    code_parts.append('  .then(data => console.log(data))')
    code_parts.append('  .catch(error => console.error(error));')
    
    return '\n'.join(code_parts)

def test_api_key(service, key):
    """Test an API key and return detailed request/response info."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    request_details = {}
    response_details = {}
    terminal_logs = []
    validator_result = None  # Store validator result for services not in SERVICE_ENDPOINTS
    
    def log_terminal(message):
        """Add message to terminal logs and print to console exactly as shown."""
        # Capture exact terminal output - preserve all formatting
        terminal_logs.append(message)
        # Print to actual terminal (stdout) so user sees it in console
        print(message, flush=True)
    
    try:
        # Try to get detailed endpoint info and make actual request
        if service in SERVICE_ENDPOINTS:
            endpoint_info = SERVICE_ENDPOINTS[service]
            # Handle URL as function or string
            url = endpoint_info['url'](key) if callable(endpoint_info['url']) else endpoint_info['url']
            method = endpoint_info['method']
            headers = endpoint_info['headers'](key)
            
            request_details = {
                "method": method,
                "url": url,
                "headers": headers
            }
            
            if 'params' in endpoint_info:
                params = endpoint_info['params'](key)
                request_details["params"] = params
                request_details["params_formatted"] = json.dumps(params, indent=2)
            
            if 'auth' in endpoint_info:
                auth = endpoint_info['auth'](key)
                request_details["auth"] = auth  # Store tuple for curl generation
                request_details["auth_display"] = f"Basic Auth (username: {auth[0]})"
        
        # Generate and log curl command - ONLY show the command
        curl_command = generate_curl_command(request_details, service, key)
        if curl_command:
            log_terminal(curl_command)
            log_terminal("")
        
        # Get the validator function
        if service not in request_module.API_KEY_PATTERNS:
            error_msg = f"Unknown service: {service}"
            log_terminal(f"✗ Error: {error_msg}")
            log_terminal("="*70 + "\n")
            return {
                "success": False,
                "error": error_msg,
                "service": service,
                "timestamp": timestamp,
                "request": request_details,
                "response": response_details,
                "terminal_logs": terminal_logs
            }
        
        # Make actual HTTP request to capture response details
        start_time = datetime.now()
        actual_response = None
        
        try:
            # Always try to make the request if we have endpoint info
            if service in SERVICE_ENDPOINTS:
                endpoint_info = SERVICE_ENDPOINTS[service]
                # Handle URL as function or string
                url = endpoint_info['url'](key) if callable(endpoint_info['url']) else endpoint_info['url']
                method = endpoint_info['method']
                headers = endpoint_info['headers'](key)
                
                # Execute the request silently (no logging here)
                # Make request with SSL error handling
                try:
                    if 'params' in endpoint_info:
                        params = endpoint_info['params'](key)
                        actual_response = requests.get(url, headers=headers, params=params, timeout=10, verify=True)
                    elif 'auth' in endpoint_info:
                        auth = endpoint_info['auth'](key)
                        if method == "GET":
                            actual_response = requests.get(url, headers=headers, auth=auth, timeout=10, verify=True)
                        else:
                            actual_response = requests.post(url, headers=headers, auth=auth, timeout=10, verify=True)
                    else:
                        if method == "GET":
                            actual_response = requests.get(url, headers=headers, timeout=10, verify=True)
                        else:
                            actual_response = requests.post(url, headers=headers, timeout=10, verify=True)
                except SSLError as ssl_error:
                    # SSL verification failed - retry with verify=False and log the error
                    log_terminal("")
                    log_terminal(f"SSL Error: {str(ssl_error)}")
                    log_terminal("Retrying with SSL verification disabled...")
                    log_terminal("")
                    try:
                        if 'params' in endpoint_info:
                            params = endpoint_info['params'](key)
                            actual_response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
                        elif 'auth' in endpoint_info:
                            auth = endpoint_info['auth'](key)
                            if method == "GET":
                                actual_response = requests.get(url, headers=headers, auth=auth, timeout=10, verify=False)
                            else:
                                actual_response = requests.post(url, headers=headers, auth=auth, timeout=10, verify=False)
                        else:
                            if method == "GET":
                                actual_response = requests.get(url, headers=headers, timeout=10, verify=False)
                            else:
                                actual_response = requests.post(url, headers=headers, timeout=10, verify=False)
                    except Exception as retry_error:
                        log_terminal(f"Request failed even with SSL verification disabled: {str(retry_error)}")
                        actual_response = None
                
                # Capture and log response details for services in SERVICE_ENDPOINTS
                if actual_response:
                    response_details = {
                        "status_code": actual_response.status_code,
                        "status_text": actual_response.reason,
                        "headers": dict(actual_response.headers),
                        "headers_formatted": json.dumps(dict(actual_response.headers), indent=2)
                    }
                    
                    # Try to parse response body
                    try:
                        response_body = actual_response.json()
                        response_details["body"] = response_body
                        response_details["body_formatted"] = json.dumps(response_body, indent=2)
                    except:
                        response_details["body"] = actual_response.text
                        response_details["body_formatted"] = actual_response.text
                    
                    # Log ONLY the raw response - no formatting, no summaries
                    log_terminal("")
                    # Show raw response text/JSON exactly as received
                    if response_details.get("body_formatted"):
                        log_terminal(response_details["body_formatted"])
                    else:
                        log_terminal(actual_response.text)
            else:
                # Service not in SERVICE_ENDPOINTS - intercept validator's HTTP requests
                log_terminal("Note: Service endpoint configuration not available")
                log_terminal("Using validator function - intercepting HTTP requests...")
                log_terminal("")
                
                # Monkey-patch requests to capture the validator's actual HTTP calls
                original_get = requests.get
                original_post = requests.post
                captured_request = {"method": None, "url": None, "headers": None, "params": None, "auth": None}
                captured_response = None
                
                def capture_get(*args, **kwargs):
                    captured_request["method"] = "GET"
                    captured_request["url"] = args[0] if args else kwargs.get("url")
                    captured_request["headers"] = kwargs.get("headers", {})
                    captured_request["params"] = kwargs.get("params")
                    captured_request["auth"] = kwargs.get("auth")
                    # Handle SSL errors
                    if 'verify' not in kwargs:
                        kwargs['verify'] = True
                    try:
                        response = original_get(*args, **kwargs)
                    except SSLError:
                        log_terminal("SSL Error detected, retrying with SSL verification disabled...")
                        kwargs['verify'] = False
                        response = original_get(*args, **kwargs)
                    nonlocal captured_response
                    captured_response = response
                    return response
                
                def capture_post(*args, **kwargs):
                    captured_request["method"] = "POST"
                    captured_request["url"] = args[0] if args else kwargs.get("url")
                    captured_request["headers"] = kwargs.get("headers", {})
                    captured_request["params"] = kwargs.get("params")
                    captured_request["auth"] = kwargs.get("auth")
                    # Handle SSL errors
                    if 'verify' not in kwargs:
                        kwargs['verify'] = True
                    try:
                        response = original_post(*args, **kwargs)
                    except SSLError:
                        log_terminal("SSL Error detected, retrying with SSL verification disabled...")
                        kwargs['verify'] = False
                        response = original_post(*args, **kwargs)
                    nonlocal captured_response
                    captured_response = response
                    return response
                
                # Temporarily replace requests methods
                requests.get = capture_get
                requests.post = capture_post
                
                validator_result = None
                try:
                    # Call validator - it will make HTTP requests which we'll capture
                    validator = request_module.API_KEY_PATTERNS[service]["validate"]
                    validator_result = validator(key)
                    
                    # Restore original methods
                    requests.get = original_get
                    requests.post = original_post
                    
                    # Generate curl from captured request - ONLY show the command
                    if captured_request["method"] and captured_request["url"]:
                        request_details = {
                            "method": captured_request["method"],
                            "url": captured_request["url"],
                            "headers": captured_request["headers"] or {},
                            "params": captured_request.get("params"),
                            "auth": captured_request.get("auth")
                        }
                        curl_cmd = generate_curl_command(request_details, service, key)
                        if curl_cmd:
                            log_terminal(curl_cmd)
                            log_terminal("")
                    
                    # Log captured response
                    if captured_response:
                        actual_response = captured_response
                except Exception as validator_error:
                    # Restore original methods even on error
                    requests.get = original_get
                    requests.post = original_post
                    log_terminal(f"Validator error: {str(validator_error)}")
                
                # Capture response details
                if actual_response:
                    response_details = {
                        "status_code": actual_response.status_code,
                        "status_text": actual_response.reason,
                        "headers": dict(actual_response.headers),
                        "headers_formatted": json.dumps(dict(actual_response.headers), indent=2)
                    }
                    
                    # Try to parse response body
                    try:
                        response_body = actual_response.json()
                        response_details["body"] = response_body
                        response_details["body_formatted"] = json.dumps(response_body, indent=2)
                    except:
                        response_details["body"] = actual_response.text
                        response_details["body_formatted"] = actual_response.text
                    
                    # Log ONLY the raw response - no formatting, no summaries
                    log_terminal("")
                    # Show raw response text/JSON exactly as received
                    if response_details.get("body_formatted"):
                        log_terminal(response_details["body_formatted"])
                    else:
                        log_terminal(actual_response.text)
        except Exception as req_error:
            log_terminal("")
            log_terminal("=== REQUEST ERROR ===")
            log_terminal(f"Error: {str(req_error)}")
            import traceback
            log_terminal("Traceback:")
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    log_terminal(f"  {line}")
            response_details["error"] = str(req_error)
        
        # Use validator for result (if not already called)
        if service in SERVICE_ENDPOINTS:
            # We already made the request above, now just validate
            validator = request_module.API_KEY_PATTERNS[service]["validate"]
            result = validator(key)
        else:
            # Validator was already called above to capture request/response
            result = validator_result if 'validator_result' in locals() and validator_result is not None else False
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Don't log summary - just command and response
        
        # Generate request examples
        curl_command = generate_curl_command(request_details, service, key)
        python_code = generate_python_request(request_details, service, key)
        javascript_code = generate_javascript_fetch(request_details, service, key)
        
        request_examples = {
            "curl": curl_command,
            "python": python_code,
            "javascript": javascript_code
        }
        
        return {
            "success": result,
            "service": service,
            "key_preview": key[:20] + "..." if len(key) > 20 else key,
            "timestamp": timestamp,
            "duration": f"{duration:.2f}s",
            "request": request_details,
            "response": response_details,
            "terminal_logs": terminal_logs,
            "request_examples": request_examples
        }
        
    except Exception as e:
        error_msg = str(e)
        log_terminal("\n" + "="*70)
        log_terminal(f"[TEST ERROR] {service}")
        log_terminal("="*70)
        log_terminal(f"Time: {timestamp}")
        log_terminal(f"Service: {service}")
        log_terminal(f"Key: {key[:30]}..." if len(key) > 30 else f"Key: {key}")
        log_terminal("-"*70)
        log_terminal(f"✗ Error: {error_msg}")
        import traceback
        log_terminal(f"Traceback: {traceback.format_exc()}")
        log_terminal("="*70 + "\n")
        
        # Generate request examples even on error
        curl_command = generate_curl_command(request_details, service, key)
        python_code = generate_python_request(request_details, service, key)
        javascript_code = generate_javascript_fetch(request_details, service, key)
        
        request_examples = {
            "curl": curl_command,
            "python": python_code,
            "javascript": javascript_code
        }
        
        return {
            "success": False,
            "error": error_msg,
            "service": service,
            "timestamp": timestamp,
            "request": request_details,
            "response": response_details,
            "terminal_logs": terminal_logs,
            "request_examples": request_examples
        }

@app.route('/')
def index():
    """Main dashboard page."""
    try:
        keys = parse_api_keys_file()
        return render_template('dashboard.html', keys=keys)
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        import traceback
        traceback.print_exc()
        return f"Error loading dashboard: {str(e)}", 500

@app.route('/api/test', methods=['POST'])
def test_key():
    """API endpoint to test an API key."""
    data = request.json
    service = data.get('service')
    key = data.get('key')
    
    if not service or not key:
        return jsonify({"success": False, "error": "Missing service or key"}), 400
    
    result = test_api_key(service, key)
    return jsonify(result)

@app.route('/api/keys', methods=['GET'])
def get_keys():
    """API endpoint to get all keys."""
    keys = parse_api_keys_file()
    return jsonify(keys)

if __name__ == '__main__':
    print("="*60)
    print("API KEY DASHBOARD")
    print("="*60)
    
    # Test parsing before starting server
    try:
        keys = parse_api_keys_file()
        print(f"Loaded {len(keys)} API key(s) from working_api_keys.txt")
    except Exception as e:
        print(f"Warning: Error parsing API keys file: {e}")
    
    print("Starting dashboard server...")
    print("Access the dashboard at: http://localhost:5002")
    print("Press Ctrl+C to stop the server")
    print("="*60)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5002)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()

