# API Key Tester Dashboard

A simple web dashboard to test all found API keys and view request/response details in the terminal.

## Features

- 📊 View all found API keys in a clean web interface
- 🧪 Test each API key with a single click
- terminal output showing detailed request/response information
- ✅ Real-time status updates for each test
- 🎨 Modern, responsive UI

## Installation

1. Create a virtual environment (if not already created):
```bash
python3 -m venv venv
```

2. Activate the virtual environment:
```bash
source venv/bin/activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Make sure you have found some API keys (run `request.py` first to find keys)

2. Activate the virtual environment:
```bash
source venv/bin/activate
```

3. Start the dashboard:
```bash
python dashboard.py
```

**OR** use the convenience script:
```bash
./run_dashboard.sh
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

4. Click the "Test" button next to any API key to test it

5. Watch the terminal for detailed request/response information:
   - Request details (endpoint, headers, method)
   - Response status
   - Duration
   - Any errors

## Dashboard Features

- **Service Badge**: Shows which service the API key is for
- **Test Button**: Click to test the API key
- **Key Information**: Displays repository, file, and timestamp
- **Status Indicator**: Shows test results (Success/Failed)
- **Terminal Output**: Detailed request/response logging

## Notes

- The dashboard reads from `working_api_keys.txt`
- All API requests are logged to the terminal where you run `dashboard.py`
- Tests use the same validation functions as the scraper
- The dashboard runs on port 5000 by default

