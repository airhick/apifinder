"""
Web application for API Key Finder
Deployable on Render with web interface
"""
import os
import threading
import time
import queue
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
import json
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import re

# Load environment variables
load_dotenv()

# Import our existing modules
from downloader import bulk_downloader
from github_crawler import GitHubCrawler
from key_validator import KeyValidator

app = Flask(__name__)
CORS(app)

# Production configuration
if os.environ.get('RENDER'):
    # Running on Render
    app.config['DEBUG'] = False
else:
    # Running locally
    app.config['DEBUG'] = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
app_state = {
    "is_running": False,
    "crawler_thread": None,
    "logs": [],
    "stats": {
        "repos_scanned": 0,
        "keys_found": 0,
        "keys_working": 0,
        "start_time": None,
    },
    "current_run_keys": set(),  # Track keys found in current run
    "current_run_start": None,  # Track when current run started
    "testing_keys": False,  # Track if keys are being tested
    "test_results": [],  # Store test results
}

# Log queue for real-time streaming
log_queue = queue.Queue()

# Initialize key tracking
try:
    import key_tracker
    key_tracker.set_tracking_state(app_state)
except:
    pass

class LogHandler(logging.Handler):
    """Custom log handler that adds logs to queue"""
    def emit(self, record):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": self.format(record)
        }
        log_queue.put(log_entry)
        # Keep more logs in memory (increased from 1000 to 10000)
        if len(app_state["logs"]) > 10000:
            app_state["logs"].pop(0)
        app_state["logs"].append(log_entry)

# Add custom handler to root logger
# This will capture all logs from all modules that use the logging module
root_logger = logging.getLogger()
handler = LogHandler()
handler.setLevel(logging.DEBUG)  # Capture all log levels
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)  # Set root logger level to INFO

def run_crawler():
    """Run the crawler in a separate thread"""
    try:
        app_state["is_running"] = True
        app_state["stats"]["start_time"] = datetime.now().isoformat()
        app_state["current_run_start"] = datetime.now().isoformat()
        app_state["current_run_keys"] = set()  # Reset for new run
        
        logger.info("🚀 Starting API Key Finder...")
        
        # Check if repo_list.txt exists, if not, run big.py to create it
        if not os.path.exists("repo_list.txt") or (os.path.exists("repo_list.txt") and os.path.getsize("repo_list.txt") == 0):
            logger.info("📥 Fetching repository URLs from GitHub archive...")
            try:
                import big
                big.save_repo_urls()
                logger.info("✅ Repository URLs saved to repo_list.txt")
            except Exception as e:
                logger.error(f"❌ Error fetching repo URLs: {e}")
                logger.warning("⚠️  Continuing with empty repo list...")
                with open("repo_list.txt", "w") as f:
                    f.write("")
        
        # Run the bulk downloader
        bulk_downloader()
        
    except Exception as e:
        logger.error(f"❌ Error running crawler: {str(e)}", exc_info=True)
    finally:
        app_state["is_running"] = False
        logger.info("✅ Crawler finished")

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current status"""
    return jsonify({
        "is_running": app_state["is_running"],
        "stats": app_state["stats"]
    })

@app.route('/api/start', methods=['POST'])
def start_crawler():
    """Start the crawler"""
    if app_state["is_running"]:
        return jsonify({"error": "Crawler is already running"}), 400
    
    # Start crawler in background thread
    thread = threading.Thread(target=run_crawler, daemon=True)
    thread.start()
    app_state["crawler_thread"] = thread
    
    return jsonify({"message": "Crawler started", "status": "running"})

@app.route('/api/stop', methods=['POST'])
def stop_crawler():
    """Stop the crawler (graceful shutdown)"""
    if not app_state["is_running"]:
        return jsonify({"error": "Crawler is not running"}), 400
    
    # Set flag to stop (crawler should check this periodically)
    app_state["is_running"] = False
    logger.info("🛑 Stopping crawler...")
    
    return jsonify({"message": "Stop signal sent"})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get all logs"""
    # Return all logs, not just last 100
    limit = request.args.get('limit', type=int)
    if limit:
        logs = app_state["logs"][-limit:]
    else:
        logs = app_state["logs"]  # Return all logs
    return jsonify({
        "logs": logs,
        "total": len(app_state["logs"])
    })

@app.route('/api/logs/stream')
def stream_logs():
    """Stream logs via Server-Sent Events"""
    def generate():
        while True:
            try:
                # Get log from queue (with timeout)
                log_entry = log_queue.get(timeout=1)
                yield f"data: {json.dumps(log_entry)}\n\n"
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics"""
    # Read current counts from files
    keys_found = 0
    keys_working = 0
    
    try:
        if os.path.exists("found_api_keys.txt"):
            with open("found_api_keys.txt", "r") as f:
                keys_found = len([line for line in f if line.strip()])
    except:
        pass
    
    try:
        if os.path.exists("working_api_keys.txt"):
            with open("working_api_keys.txt", "r") as f:
                keys_working = len([line for line in f if line.strip()])
    except:
        pass
    
    stats = app_state["stats"].copy()
    stats["keys_found"] = keys_found
    stats["keys_working"] = keys_working
    
    return jsonify(stats)

@app.route('/api/keys/found', methods=['GET'])
def get_found_keys():
    """Get list of all found keys with type information"""
    try:
        keys = []
        if os.path.exists("found_api_keys.txt"):
            with open("found_api_keys.txt", "r") as f:
                keys = [line.strip() for line in f if line.strip()]
        
        # Read working keys to check which are working
        working_keys = set()
        if os.path.exists("working_api_keys.txt"):
            with open("working_api_keys.txt", "r") as f:
                working_keys = set(line.strip() for line in f if line.strip())
        
        # Mark keys from current run and identify type
        result = []
        key_types_count = {}
        for key in keys:
            is_current_run = key in app_state["current_run_keys"]
            is_working = key in working_keys
            key_type = identify_key_type(key) or "unknown"
            
            # Count by type
            if key_type not in key_types_count:
                key_types_count[key_type] = {"total": 0, "working": 0}
            key_types_count[key_type]["total"] += 1
            if is_working:
                key_types_count[key_type]["working"] += 1
            
            result.append({
                "key": key,
                "key_type": key_type,
                "is_current_run": is_current_run,
                "is_working": is_working
            })
        
        return jsonify({
            "keys": result, 
            "count": len(result),
            "by_type": key_types_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/keys/working', methods=['GET'])
def get_working_keys():
    """Get list of working keys with type information"""
    try:
        keys = []
        if os.path.exists("working_api_keys.txt"):
            with open("working_api_keys.txt", "r") as f:
                keys = [line.strip() for line in f if line.strip()]
        
        # Mark keys from current run and identify type
        result = []
        key_types_count = {}
        for key in keys:
            is_current_run = key in app_state["current_run_keys"]
            key_type = identify_key_type(key) or "unknown"
            
            # Count by type
            if key_type not in key_types_count:
                key_types_count[key_type] = 0
            key_types_count[key_type] += 1
            
            result.append({
                "key": key,
                "key_type": key_type,
                "is_current_run": is_current_run
            })
        
        return jsonify({
            "keys": result, 
            "count": len(result),
            "by_type": key_types_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/detailed', methods=['GET'])
def get_detailed_stats():
    """Get detailed statistics including conversion rates"""
    try:
        found_keys = []
        working_keys = []
        
        if os.path.exists("found_api_keys.txt"):
            with open("found_api_keys.txt", "r") as f:
                found_keys = [line.strip() for line in f if line.strip()]
        
        if os.path.exists("working_api_keys.txt"):
            with open("working_api_keys.txt", "r") as f:
                working_keys = [line.strip() for line in f if line.strip()]
        
        working_set = set(working_keys)
        
        # Calculate stats by type
        stats_by_type = {}
        for key in found_keys:
            key_type = identify_key_type(key) or "unknown"
            if key_type not in stats_by_type:
                stats_by_type[key_type] = {"found": 0, "working": 0}
            stats_by_type[key_type]["found"] += 1
            if key in working_set:
                stats_by_type[key_type]["working"] += 1
        
        # Calculate conversion rates
        for key_type in stats_by_type:
            found = stats_by_type[key_type]["found"]
            working = stats_by_type[key_type]["working"]
            stats_by_type[key_type]["conversion_rate"] = (working / found * 100) if found > 0 else 0
        
        # Overall stats
        total_found = len(found_keys)
        total_working = len(working_keys)
        overall_conversion = (total_working / total_found * 100) if total_found > 0 else 0
        
        return jsonify({
            "total_found": total_found,
            "total_working": total_working,
            "conversion_rate": round(overall_conversion, 2),
            "by_type": stats_by_type
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_detailed_response(key_type, key):
    """Get detailed HTTP response for a key"""
    import requests
    
    try:
        if key_type in ['openai_standard', 'openai_project']:
            headers = {"Authorization": f"Bearer {key}"}
            response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
            response_text = response.text[:300] if response.text else f"Status {response.status_code}"
            return response.status_code, response_text
        elif key_type == 'google_gemini':
            headers = {"X-Goog-Api-Key": key}
            response = requests.get("https://generativelanguage.googleapis.com/v1beta/models", headers=headers, timeout=10)
            response_text = response.text[:300] if response.text else f"Status {response.status_code}"
            return response.status_code, response_text
        elif key_type == 'anthropic':
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
            response = requests.get("https://api.anthropic.com/v1/messages", headers=headers, timeout=10)
            response_text = response.text[:300] if response.text else f"Status {response.status_code}"
            return response.status_code, response_text
        elif key_type == 'huggingface':
            headers = {"Authorization": f"Bearer {key}"}
            response = requests.get("https://api-inference.huggingface.co/models", headers=headers, timeout=10)
            response_text = response.text[:300] if response.text else f"Status {response.status_code}"
            return response.status_code, response_text
        elif key_type == 'cohere':
            headers = {"Authorization": f"Bearer {key}"}
            response = requests.get("https://api.cohere.ai/v1/models", headers=headers, timeout=10)
            response_text = response.text[:300] if response.text else f"Status {response.status_code}"
            return response.status_code, response_text
        else:
            return None, "No detailed response available for this key type"
    except Exception as e:
        return None, f"Error: {str(e)[:200]}"

def identify_key_type(key):
    """Identify the type of API key based on patterns"""
    from config import API_KEY_PATTERNS
    
    # Test each pattern type
    for key_type, patterns in API_KEY_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(key)
            if match:
                # Extract the key from match groups if available
                if match.groups():
                    extracted_key = match.group(1)
                    if extracted_key == key.strip('"\''):
                        return key_type
                else:
                    matched = match.group(0)
                    if matched == key or matched.strip('"\'') == key.strip('"\''):
                        return key_type
    
    # Fallback: Try to identify by prefix/format
    key_clean = key.strip('"\'').strip()
    
    if key_clean.startswith('sk-') and len(key_clean) == 51:
        return 'openai_standard'
    elif key_clean.startswith('sk-proj-'):
        return 'openai_project'
    elif key_clean.startswith('sk-ant-'):
        return 'anthropic'
    elif key_clean.startswith('AIza') and len(key_clean) == 39:
        return 'google_gemini'
    elif key_clean.startswith('hf_') and len(key_clean) == 37:
        return 'huggingface'
    elif len(key_clean) == 40 and not key_clean.startswith(('sk-', 'hf_', 'AIza')):
        return 'cohere'  # Might be Cohere
    elif key_clean.startswith('pc-'):
        return 'pinecone'
    elif len(key_clean) == 36 and '-' in key_clean:
        return 'pinecone'  # UUID format
    
    return None

@app.route('/api/test/keys', methods=['POST'])
def test_keys():
    """Test API keys from file upload or use found_api_keys.txt"""
    try:
        keys_to_test = []
        
        # Check if file was uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename:
                # Read keys from uploaded file
                content = file.read().decode('utf-8')
                keys_to_test = [line.strip() for line in content.split('\n') if line.strip()]
        elif request.json and 'use_found_keys' in request.json:
            # Use keys from found_api_keys.txt
            if os.path.exists("found_api_keys.txt"):
                with open("found_api_keys.txt", "r") as f:
                    keys_to_test = [line.strip() for line in f if line.strip()]
            else:
                return jsonify({"error": "found_api_keys.txt not found"}), 404
        else:
            return jsonify({"error": "No file uploaded or use_found_keys not specified"}), 400
        
        if not keys_to_test:
            return jsonify({"error": "No keys found to test"}), 400
        
        # Remove duplicates
        unique_keys = list(set(keys_to_test))
        
        # Start testing in background thread
        app_state["testing_keys"] = True
        app_state["test_results"] = []
        
        thread = threading.Thread(target=test_keys_thread, args=(unique_keys,), daemon=True)
        thread.start()
        
        return jsonify({
            "message": "Testing started",
            "total_keys": len(unique_keys),
            "status": "testing"
        })
    except Exception as e:
        app_state["testing_keys"] = False
        return jsonify({"error": str(e)}), 500

def test_keys_thread(keys):
    """Test keys in background thread"""
    validator = KeyValidator()
    
    try:
        logger.info(f"🧪 Starting to test {len(keys)} keys...")
        
        for i, key in enumerate(keys, 1):
            if not app_state["testing_keys"]:
                break
            
            key_type = identify_key_type(key)
            
            if not key_type:
                result = {
                    "index": i,
                    "total": len(keys),
                    "key": key[:50] + "..." if len(key) > 50 else key,
                    "key_type": "unknown",
                    "is_valid": False,
                    "message": "Unknown key type",
                    "status_code": None,
                    "response": None
                }
                app_state["test_results"].append(result)
                logger.info(f"[{i}/{len(keys)}] ⏭️  Skipped (unknown type): {key[:30]}...")
                continue
            
            # Test the key
            logger.info(f"[{i}/{len(keys)}] 🧪 Testing {key_type}: {key[:40]}...")
            
            try:
                # Get detailed response first (this also validates)
                status_code, response_text = get_detailed_response(key_type, key)
                
                # Then validate to get the message
                is_valid, message = validator.validate_key(key_type, key)
                
                # Use detailed response if available, otherwise use validation message
                if response_text and response_text != "No detailed response available for this key type":
                    if not response_text.startswith("Error:"):
                        message = f"{message} | Response: {response_text[:150]}"
                
                # Build result with detailed information
                result = {
                    "index": i,
                    "total": len(keys),
                    "key": key[:50] + "..." if len(key) > 50 else key,
                    "key_full": key,  # Full key for display
                    "key_type": key_type,
                    "is_valid": is_valid,
                    "message": message,
                    "status_code": status_code,
                    "response": response_text
                }
                
                app_state["test_results"].append(result)
                
                if is_valid:
                    logger.info(f"[{i}/{len(keys)}] ✅ WORKING {key_type} key ({message})")
                else:
                    logger.info(f"[{i}/{len(keys)}] ❌ Invalid {key_type} key ({message})")
                
            except Exception as e:
                result = {
                    "index": i,
                    "total": len(keys),
                    "key": key[:50] + "..." if len(key) > 50 else key,
                    "key_full": key,
                    "key_type": key_type or "unknown",
                    "is_valid": False,
                    "message": f"Error: {str(e)[:100]}",
                    "status_code": None,
                    "response": None
                }
                app_state["test_results"].append(result)
                logger.error(f"[{i}/{len(keys)}] ❌ Error testing key: {e}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.3)
        
        logger.info(f"✅ Testing complete! Tested {len(keys)} keys")
        
    except Exception as e:
        logger.error(f"❌ Error in test thread: {e}")
    finally:
        app_state["testing_keys"] = False

@app.route('/api/test/status', methods=['GET'])
def get_test_status():
    """Get testing status and results"""
    return jsonify({
        "testing": app_state["testing_keys"],
        "results": app_state["test_results"],
        "total_tested": len(app_state["test_results"]),
        "total_valid": sum(1 for r in app_state["test_results"] if r.get("is_valid", False)),
        "total_invalid": sum(1 for r in app_state["test_results"] if not r.get("is_valid", False))
    })

@app.route('/api/test/stop', methods=['POST'])
def stop_testing():
    """Stop testing keys"""
    app_state["testing_keys"] = False
    return jsonify({"message": "Testing stopped"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8005))
    app.run(host='0.0.0.0', port=port, debug=False)

