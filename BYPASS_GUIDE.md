# GitHub Token Bypass Guide

## Overview

This tool now uses **web scraping** instead of the GitHub API, completely bypassing the need for a GitHub token and API rate limits!

## How It Works

### Old Method (API-based)
- Required GitHub Personal Access Token
- Rate limited: 60 requests/hour (no token) or 5,000/hour (with token)
- Used PyGithub library
- Limited by GitHub API restrictions

### New Method (Web Scraping) ✅
- **No token required!**
- Scrapes GitHub's web search interface directly
- Bypasses API rate limits entirely
- Uses multiple strategies to find code files:
  1. Parses GitHub's search results HTML
  2. Extracts file URLs from search pages
  3. Fetches raw file content from `raw.githubusercontent.com`
  4. Rotates user agents to avoid detection
  5. Implements smart delays between requests

## Key Features

### 1. User Agent Rotation
- Automatically rotates user agents using `fake-useragent`
- Makes requests appear to come from different browsers
- Reduces chance of being blocked

### 2. Smart Rate Limiting
- Random delays between requests (1-3 seconds)
- Longer delays between search queries (3-6 seconds)
- Automatic backoff on rate limit detection
- Respectful scraping to avoid overwhelming servers

### 3. Multiple Parsing Strategies
- Tries multiple HTML selectors to find code files
- Handles different GitHub page layouts
- Fallback methods if primary parsing fails

### 4. Raw Content Fetching
- Converts GitHub URLs to raw content URLs
- Directly fetches file contents without API
- Handles 404s and rate limits gracefully

## Usage

Simply run the tool - no configuration needed:

```bash
python main.py
```

The tool will automatically use web scraping (no token required).

## Configuration Options

You can still configure behavior via `.env`:

```env
# No GitHub token needed!
MAX_RESULTS_PER_QUERY=100
VALIDATE_KEYS=true
USE_WEB_SCRAPER=true  # Default: true
```

## Advantages

✅ **No Token Required** - Works immediately without setup  
✅ **No Rate Limits** - Not limited by GitHub API restrictions  
✅ **More Flexible** - Can scrape more results than API allows  
✅ **Stealth Mode** - User agent rotation makes it harder to detect  
✅ **Resilient** - Multiple parsing strategies handle page changes  

## Technical Details

### Search Method
1. Constructs GitHub search URL: `https://github.com/search?q={query}&type=code`
2. Parses HTML response with BeautifulSoup
3. Extracts file URLs from search results
4. Fetches raw content from `raw.githubusercontent.com`

### Error Handling
- Handles 429 (rate limit) responses with automatic backoff
- Retries failed requests with exponential backoff
- Skips invalid URLs gracefully
- Logs warnings for debugging

### Performance
- Processes multiple pages of results
- Parallel processing of file content fetching
- Efficient deduplication of URLs
- Progress tracking with detailed logging

## Limitations

⚠️ **Note**: Web scraping is slower than API calls but has no rate limits
⚠️ GitHub may change their HTML structure - the tool includes fallback parsers
⚠️ Very aggressive scraping may still trigger rate limits - the tool includes delays

## Best Practices

1. **Use reasonable delays** - Don't set `MAX_RESULTS_PER_QUERY` too high
2. **Monitor logs** - Watch for rate limit warnings
3. **Respect servers** - The tool includes automatic delays
4. **Test first** - Start with small queries to verify it works

## Troubleshooting

### Issue: No results found
- **Solution**: GitHub may have changed their HTML structure. Check logs for parsing errors.

### Issue: Rate limited
- **Solution**: The tool automatically waits 30 seconds and retries. Increase delays in code if needed.

### Issue: Slow performance
- **Solution**: This is normal - web scraping is slower than API. Reduce `MAX_RESULTS_PER_QUERY` for faster results.

## Conclusion

The web scraping method successfully bypasses GitHub API limitations while maintaining functionality. No token is required, and you can scrape as many results as needed (within reason)!

