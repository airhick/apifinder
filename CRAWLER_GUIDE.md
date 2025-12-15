# GitHub Full Crawler Guide

## Overview

The program now crawls **all of GitHub** systematically, browsing every repository and every code file to find API keys. It's a complete crawler, not just a keyword searcher.

## How It Works

### 1. Repository Discovery (Unpopular Repos)
- **Targets repos with 0-5 stars** (unpopular/unknown repositories)
- Why? Unpopular repos are more likely to have exposed API keys
- Fetches repos from multiple sources:
  - Repos with 0 stars by language
  - Repos with 1-5 stars by language
  - Recently created repos (often have 0 stars)
  - Repos with API-related keywords (api, key, secret, config, etc.)
  - Multiple programming languages covered

### 2. File Discovery (Recursive - Focus on Code Files)
For each repository:
- Explores all branches (main, master, develop, dev)
- Recursively crawls all directories
- **Prioritizes code files** for API key discovery
- Processes file types in priority order:
  
  **Primary (Code Files):**
  - `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.go`, `.rs`, `.cpp`, `.c`, `.php`, `.rb`, `.swift`, `.kt`, `.scala`, etc.
  
  **Secondary (Config Files):**
  - `.env`, `.config`, `.yaml`, `.yml`, `.json`, `.toml`, `.properties`, `.conf`, etc.
  - Files with names like: `config`, `secret`, `credential`, `key`, `api_key`, `token`, `auth`
  
  **Tertiary (Text Files with Secrets):**
  - `.md`, `.txt` files that contain secret-related keywords

### 3. Key Extraction
- Downloads each file's raw content
- Applies regex patterns to find API keys
- Supports all key types: OpenAI, Google, Perplexity, Anthropic, AWS, GitHub, Stripe, etc.

### 4. Immediate Saving & Testing
When an API key is found:
1. **Immediately saved** to `found_api_keys.txt`
2. **Immediately tested** against the real API
3. **If working**, saved to `working_api_keys.txt`

### 5. High-Speed Crawling
- Configurable speed: up to 100 repos/second
- Minimal delays between requests
- User agent rotation
- Efficient file processing

## File Outputs

### `found_api_keys.txt`
Contains ALL found API keys, one per line:
```
openai: sk-proj-abc123...
google_api_key: AIzaSyAbCdEf...
perplexity: pplx-xyz789...
```

### `working_api_keys.txt`
Contains ONLY working API keys with validation info:
```
openai: sk-proj-abc123... | Valid OpenAI key | 2024-12-15T14:30:22
google_api_key: AIzaSyAbCdEf... | Valid Google API key | 2024-12-15T14:30:25
```

## Configuration

Edit `.env` file:

```env
# Repos per second (default: 10, can go up to 100)
REPOS_PER_SECOND=100.0

# Maximum repos to crawl (default: 10000)
MAX_REPOS=10000
```

## Usage

```bash
python main.py
```

The program will:
1. Start crawling repositories
2. Save keys immediately as they're found
3. Test keys and save working ones separately
4. Show real-time progress

## Progress Output

```
📁 Crawling repo 1: facebook/react
  Found 2500 files in facebook/react
  Processed 100/2500 files | Keys: 2 | Working: 1
  Processed 200/2500 files | Keys: 2 | Working: 1
🔑 Found openai key: sk-proj-abc123...
✅ WORKING openai key: sk-proj-abc123... (Valid OpenAI key)
📁 Crawling repo 2: microsoft/vscode
...
Progress: 10/10000 repos | Rate: 95.23 repos/sec | Keys found: 15 | Working: 3
```

## Statistics

At the end, you'll see:
```
============================================================
  CRAWLING STATISTICS
============================================================
Repos crawled: 1000
Files processed: 250000
Keys found: 45
Keys tested: 45
Working keys: 8
Time elapsed: 10.5 seconds
Average rate: 95.23 repos/sec
============================================================
```

## Important Notes

⚠️ **High Speed Warning**: 
- 100 repos/sec is VERY aggressive
- May result in IP bans
- Use proxies if running at high speeds
- Start with lower speeds (10-20 repos/sec) to test

⚠️ **Rate Limiting**:
- The program includes minimal delays
- GitHub may still rate limit
- Program will wait and retry on rate limits

⚠️ **File Sizes**:
- Large repos may have thousands of files
- Processing time depends on repo size
- Keys are saved immediately, so you won't lose data if interrupted

## Advantages

✅ **Complete Coverage**: Crawls entire repos, not just keyword matches
✅ **Immediate Saving**: Keys saved as soon as found
✅ **Real-time Testing**: Keys tested immediately
✅ **High Speed**: Can process 100 repos/second
✅ **No Token Needed**: Uses web scraping
✅ **Resilient**: Handles errors gracefully, continues crawling

## How It's Different from Before

**Old Method (Keyword Search)**:
- Searched for specific keywords
- Only found files matching search terms
- Missed keys in files without keywords

**New Method (Full Crawl)**:
- Crawls ALL repositories
- Processes ALL files in each repo
- Finds keys regardless of file content
- Much more comprehensive

## Technical Details

### Repository Discovery
- Fetches from GitHub trending pages
- Gets popular repos by language
- Prioritizes high-star repositories

### File Discovery
- Recursive directory traversal
- Explores multiple branches
- Filters for text/code files only
- Skips binary files

### Key Extraction
- Uses regex patterns from `config.py`
- Handles multiple key formats
- Deduplicates keys automatically

### Validation
- Tests each key against real API
- Provides detailed feedback
- Categorizes as working/non-working

This is a complete, production-ready GitHub crawler! 🚀

