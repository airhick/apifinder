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
    }
}

# Log queue for real-time streaming
log_queue = queue.Queue()

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

@app.route('/api/keys/working', methods=['GET'])
def get_working_keys():
    """Get list of working keys (last 50)"""
    try:
        if os.path.exists("working_api_keys.txt"):
            with open("working_api_keys.txt", "r") as f:
                keys = [line.strip() for line in f if line.strip()][-50:]
                return jsonify({"keys": keys, "count": len(keys)})
        return jsonify({"keys": [], "count": 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8005))
    app.run(host='0.0.0.0', port=port, debug=False)

