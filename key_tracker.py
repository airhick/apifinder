"""
Helper module to track keys found in current run
"""
# Global state for tracking - will be set by app.py
_tracking_state = None

def set_tracking_state(state):
    """Set the app state for tracking"""
    global _tracking_state
    _tracking_state = state

def track_key(key: str):
    """Track a key found in the current run"""
    global _tracking_state
    try:
        if _tracking_state and _tracking_state.get("is_running"):
            _tracking_state["current_run_keys"].add(key)
    except:
        pass  # Silently fail if tracking not available

