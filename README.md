# GitHub API Key Finder

A comprehensive tool to scrape GitHub repositories for API keys and validate them against their respective APIs.

## Features

- 🔍 **Comprehensive Search**: Searches GitHub for various API key patterns
- 🌐 **No Token Required**: Uses web scraping to bypass GitHub API rate limits (no token needed!)
- 🔑 **Multiple API Support**: Supports Google (Veo 3, Gemini, general), OpenAI, Perplexity, Anthropic, AWS, GitHub, Stripe, and more
- ✅ **Key Validation**: Tests found keys against their respective APIs to verify validity
- 📊 **Detailed Reporting**: Generates JSON reports with all found and validated keys
- 🎨 **Colored Output**: Beautiful terminal output with progress indicators
- 🛡️ **Smart Rate Limiting**: Automatic delays and user agent rotation to avoid detection

## Supported API Keys

- **Google APIs**: General API keys, Veo 3, Gemini
- **OpenAI**: API keys (sk-*)
- **Perplexity**: API keys (pplx-*)
- **Anthropic**: Claude API keys (sk-ant-*)
- **AWS**: Access keys and secret keys
- **GitHub**: Personal access tokens and fine-grained tokens
- **Stripe**: Live API keys

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Create a `.env` file for configuration:
```bash
cp env.example .env
# Edit .env to configure settings (no GitHub token needed!)
```

## Usage

### Basic Usage

```bash
python main.py
```

### Configuration

You can configure the tool using environment variables or a `.env` file:

- `MAX_RESULTS_PER_QUERY`: Maximum results per search query (default: 50)
- `VALIDATE_KEYS`: Whether to validate found keys (default: true)
- `USE_WEB_SCRAPER`: Use web scraping instead of API (default: true)

**Note**: No GitHub token is required! The tool uses web scraping to bypass API limitations.

### Example .env file

```env
MAX_RESULTS_PER_QUERY=100
VALIDATE_KEYS=true
USE_WEB_SCRAPER=true
```

## How It Works

1. **Scraping Phase**: 
   - Searches GitHub using multiple queries related to API keys
   - Uses regex patterns to identify various API key formats
   - Extracts unique keys from code files

2. **Validation Phase**:
   - Tests each found key against its respective API endpoint
   - Determines if keys are valid, invalid, or restricted
   - Provides detailed feedback for each key

3. **Reporting Phase**:
   - Saves results to JSON files in the `results/` directory
   - Displays summary in the terminal

## Output

Results are saved in the `results/` directory with timestamps:

- `found_keys_YYYYMMDD_HHMMSS.json`: All found keys
- `valid_keys_YYYYMMDD_HHMMSS.json`: Validated working keys
- `invalid_keys_YYYYMMDD_HHMMSS.json`: Invalid or non-working keys

## Rate Limiting

The web scraping method bypasses GitHub API rate limits entirely! The tool includes:
- Automatic random delays between requests
- User agent rotation to avoid detection
- Smart retry logic for failed requests
- Respectful scraping with configurable delays

## Legal and Ethical Considerations

⚠️ **IMPORTANT**: This tool is for educational and security research purposes only.

- Only searches public repositories
- Respects GitHub's rate limits
- Use responsibly and ethically
- Do not use found keys for unauthorized access
- Report exposed keys to their respective owners

## Disclaimer

This tool is provided for educational and security research purposes. The authors are not responsible for any misuse of this tool or any keys found using it. Always ensure you have permission before accessing or using any API keys.

## Deployment to Render

### Quick Deploy via GitHub

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Ready for Render deployment"
   git push origin main
   ```

2. **Deploy on Render**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select your repository
   - Render will auto-detect `render.yaml` and configure everything
   - Click "Create Web Service"

3. **Access Your App**:
   - Once deployed, you'll get a URL like: `https://api-key-finder.onrender.com`
   - Open it in your browser to see the dashboard

### Manual Configuration (if needed)

If you prefer manual setup:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120`
- **Python Version**: 3.12.0 (specified in `runtime.txt`)

### Environment Variables (Optional)

Set these in Render dashboard under "Environment":
- `REPOS_PER_SECOND`: Speed of crawling (default: 100.0)
- `MAX_REPOS`: Maximum repos to scan (default: 10000)

### Features After Deployment

✅ **Web Dashboard**: Beautiful interface to control the crawler  
✅ **Real-time Logs**: See all logs in the web interface  
✅ **Statistics**: Track progress in real-time  
✅ **Start/Stop**: Control the crawler from the web interface  
✅ **Working Keys**: View recently found working API keys  

## License

This project is provided as-is for educational purposes.

# apifinder
