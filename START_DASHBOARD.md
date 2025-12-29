# How to Start the Dashboard

## Quick Start

1. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Start the dashboard:**
   ```bash
   python dashboard.py
   ```

   OR use the convenience script:
   ```bash
   ./run_dashboard.sh
   ```

3. **Open your browser:**
   Navigate to: `http://localhost:5001`

## Troubleshooting

### "Cannot GET /" Error

This usually means:
- The Flask server is not running
- The server is running on a different port
- There's an error preventing the route from loading

**Solution:**
1. Make sure you see this output when starting:
   ```
   ============================================================
   API KEY DASHBOARD
   ============================================================
   Starting dashboard server...
   Access the dashboard at: http://localhost:5001
   ============================================================
   * Running on http://0.0.0.0:5001
   ```

2. If you see errors, check:
   - Is `working_api_keys.txt` in the same directory?
   - Are all dependencies installed? (`pip install -r requirements.txt`)
   - Is the virtual environment activated?

3. **Check if port 5001 is already in use:**
   ```bash
   lsof -i :5001
   ```
   If something is using it, either stop that process or change the port in `dashboard.py`

## Verify Installation

Test if everything is set up correctly:
```bash
source venv/bin/activate
python -c "from dashboard import app, parse_api_keys_file; keys = parse_api_keys_file(); print(f'Found {len(keys)} keys')"
```

If this works, the dashboard should work too!

