# Complete Step-by-Step Explanation of the Program

## Overview
This program scrapes GitHub to find API keys and then validates them. Here's exactly how it works, step by step.

---

## 🚀 PROGRAM STARTUP

### Step 1: Import and Initialization
```python
# main.py lines 4-23
```
**What happens:**
1. **Loads libraries**: `os`, `json`, `datetime`, `dotenv`, `colorama`, `logging`
2. **Imports custom modules**: 
   - `GitHubWebScraper` - handles web scraping
   - `KeyValidator` - tests API keys
3. **Initializes colorama**: Enables colored terminal output
4. **Sets up logging**: Configures log format and level
5. **Loads .env file**: Reads configuration from environment variables

---

## 🎨 STEP 2: Display Banner

### Function: `print_banner()` (lines 26-34)
**What happens:**
- Prints a colored banner to the terminal
- Shows "GitHub API Key Finder & Validator"
- Uses cyan color for visual appeal

**Output:**
```
============================================================
  GitHub API Key Finder & Validator
============================================================
```

---

## ⚙️ STEP 3: Configuration Loading

### In `main()` function (lines 98-101)
**What happens:**
```python
max_results_per_query = int(os.getenv("MAX_RESULTS_PER_QUERY", "50"))
validate_keys = os.getenv("VALIDATE_KEYS", "true").lower() == "true"
use_web_scraper = os.getenv("USE_WEB_SCRAPER", "true").lower() == "true"
```

**Explanation:**
- Reads `MAX_RESULTS_PER_QUERY` from .env (default: 50)
- Reads `VALIDATE_KEYS` from .env (default: true)
- Reads `USE_WEB_SCRAPER` from .env (default: true)
- These control how many results to fetch and whether to validate keys

---

## 🔍 STEP 4: Initialize Web Scraper

### Line 108: `scraper = GitHubWebScraper()`

**What happens inside `GitHubWebScraper.__init__()` (github_web_scraper.py lines 19-30):**

1. **Creates HTTP session**:
   ```python
   self.session = requests.Session()
   ```
   - Reuses connection for better performance

2. **Initializes UserAgent generator**:
   ```python
   self.ua = UserAgent()
   ```
   - Generates random browser user agents

3. **Creates empty storage dictionaries**:
   ```python
   self.found_keys = {}  # Stores found API keys by type
   self.processed_urls = set()  # Tracks URLs we've already checked
   self.processed_raw_urls = set()  # Tracks raw file URLs we've fetched
   ```

4. **Sets up fake browser headers**:
   ```python
   self._update_user_agent()
   ```
   - Makes requests look like they come from a real browser
   - Includes: User-Agent, Accept, Accept-Language, etc.

**Result**: Scraper is ready to make web requests that look like a browser

---

## 🌐 STEP 5: Start Scraping Process

### Line 109: `found_keys = scraper.scrape_all(max_results_per_query=max_results_per_query)`

**What happens inside `scrape_all()` (github_web_scraper.py lines 260-325):**

### 5.1: Loop Through Search Queries
```python
for i, query in enumerate(GITHUB_SEARCH_QUERIES, 1):
```
- Gets queries from `config.py` (e.g., "api key", "openai api key", "sk-proj-", etc.)
- Processes each query one by one

### 5.2: Search GitHub Web Interface
**Calls `search_github_web(query, max_results_per_query)` (lines 56-180)**

#### Sub-step 5.2.1: Build Search URL
```python
search_url = "https://github.com/search"
params = {
    'q': query,           # e.g., "api key"
    'type': 'code',       # Search code files only
    's': 'indexed',       # Sort by most recently indexed
    'o': 'desc',          # Descending order
    'p': 1                # Page number
}
```

**Example URL created:**
```
https://github.com/search?q=api+key&type=code&s=indexed&o=desc&p=1
```

#### Sub-step 5.2.2: Fetch Search Results Page
```python
response = self.session.get(search_url, params=params, timeout=15)
```
- Makes HTTP GET request to GitHub
- Uses fake browser headers
- Gets HTML page with search results

#### Sub-step 5.2.3: Parse HTML
```python
soup = BeautifulSoup(response.content, 'lxml')
```
- Parses HTML into a searchable structure
- Can now find specific elements

#### Sub-step 5.2.4: Extract File URLs (Multiple Strategies)

**Strategy 1**: Find structured code results
```python
code_results = soup.find_all('div', class_='code-list-item')
```

**Strategy 2**: Find by data attribute
```python
code_results = soup.find_all('div', {'data-testid': 'code-search-result'})
```

**Strategy 3**: Find all blob links directly
```python
all_blob_links = soup.find_all('a', href=re.compile(r'/blob/'))
```

**What it finds:**
- URLs like: `/username/repo/blob/main/config.py`
- Converts to: `https://github.com/username/repo/blob/main/config.py`

#### Sub-step 5.2.5: Handle Pagination
- Loops through multiple pages (up to 6 pages)
- Each page has ~10 results
- Stops when enough results found

#### Sub-step 5.2.6: Rate Limiting Protection
```python
self._random_delay(2, 4)  # Wait 2-4 seconds between pages
if page % 3 == 0:
    self._update_user_agent()  # Change user agent every 3 pages
```

**Returns**: List of file URLs to check

---

### 5.3: Fetch Raw File Content

**For each file URL found, calls `get_raw_file_content()` (lines 182-221)**

#### Sub-step 5.3.1: Convert GitHub URL to Raw URL
```python
# Input:  https://github.com/user/repo/blob/main/config.py
# Output: https://raw.githubusercontent.com/user/repo/main/config.py
raw_url = github_url.replace('github.com/', 'raw.githubusercontent.com/').replace('/blob/', '/')
```

**Why?** Raw URLs give plain text content, not HTML

#### Sub-step 5.3.2: Fetch File Content
```python
response = self.session.get(raw_url, timeout=10)
if response.status_code == 200:
    return response.text  # Returns file content as string
```

**Example content fetched:**
```python
API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890
SECRET_KEY=my_secret_key_12345
```

---

### 5.4: Extract API Keys from Content

**Calls `extract_api_keys(content, url)` (lines 223-258)**

#### Sub-step 5.4.1: Check if Already Processed
```python
if url in self.processed_urls:
    return {}  # Skip if already checked
self.processed_urls.add(url)  # Mark as processed
```

#### Sub-step 5.4.2: Loop Through All Pattern Types
```python
for key_type, patterns in API_KEY_PATTERNS.items():
```
- Gets patterns from `config.py`
- Types: "google_api_key", "openai", "perplexity", etc.

#### Sub-step 5.4.3: Apply Regex Patterns
```python
for pattern in patterns:
    matches = pattern.findall(content)
```

**Example patterns:**
- OpenAI: `r'sk-[0-9a-zA-Z]{32,}'` matches `sk-proj-abc123...`
- Google: `r'AIza[0-9A-Za-z-_]{35}'` matches `AIzaSyAbCdEf...`
- Perplexity: `r'pplx-[0-9a-zA-Z]{32,}'` matches `pplx-abc123...`

#### Sub-step 5.4.4: Clean and Store Keys
```python
for match in matches:
    key = match if isinstance(match, str) else match[0]
    if key and len(key) >= 16:  # Minimum length check
        key = key.strip('"\'')  # Remove quotes
        if key not in self.found_keys[key_type]:
            found[key_type].append(key)
            self.found_keys[key_type].add(key)  # Store in set (no duplicates)
```

**Result**: Dictionary of found keys by type
```python
{
    "openai": ["sk-proj-abc123...", "sk-proj-xyz789..."],
    "google_api_key": ["AIzaSyAbCdEf..."],
    "perplexity": ["pplx-abc123..."]
}
```

#### Sub-step 5.4.5: Delay Between Files
```python
if j % 5 == 0:
    self._random_delay(2, 4)  # Longer delay every 5 files
else:
    self._random_delay(0.5, 1.5)  # Short delay otherwise
```

---

### 5.5: Complete Scraping Loop

**After processing all queries:**
- Returns dictionary of all found keys
- Prints summary: "Found X unique API keys"

---

## ✅ STEP 6: Validate Found Keys

### Line 122: `valid_keys = validator.validate_all_keys(found_keys)`

**What happens inside `validate_all_keys()` (key_validator.py):**

### 6.1: Initialize Validator
```python
validator = KeyValidator()
```
- Creates validator with empty storage for valid/invalid keys

### 6.2: Loop Through All Key Types
```python
for key_type, keys in found_keys.items():
```

### 6.3: Validate Each Key
**Calls `validate_key(key_type, key)` which routes to specific validator:**

#### For OpenAI Keys:
```python
def validate_openai(self, key: str):
    headers = {"Authorization": f"Bearer {key}"}
    response = requests.get("https://api.openai.com/v1/models", headers=headers)
    if response.status_code == 200:
        return True, "Valid OpenAI key"
    elif response.status_code == 401:
        return False, "Invalid key"
```

#### For Google Keys:
```python
def validate_google_api_key(self, key: str):
    headers = {"X-Goog-Api-Key": key}
    response = requests.get("https://www.googleapis.com/discovery/v1/apis", headers=headers)
    if response.status_code == 200:
        return True, "Valid Google API key"
```

#### For Perplexity Keys:
```python
def validate_perplexity(self, key: str):
    headers = {"Authorization": f"Bearer {key}"}
    response = requests.get("https://api.perplexity.ai/models", headers=headers)
    # ... similar logic
```

**What happens:**
1. Makes HTTP request to API endpoint with the key
2. Checks response status code
3. Returns `(is_valid: bool, message: str)`

### 6.4: Store Results
```python
if is_valid:
    self.valid_keys[key_type].append((key, True, message))
else:
    self.invalid_keys[key_type].append(key)
```

### 6.5: Progress Tracking
- Uses `tqdm` progress bar
- Shows: "Validating keys: 45%|████▌     | 23/50"
- Adds 0.5 second delay between validations

**Result**: Two dictionaries:
- `valid_keys`: Keys that work
- `invalid_keys`: Keys that don't work

---

## 📊 STEP 7: Display Summary

### Line 126: `print_summary(valid_keys, invalid_keys)`

**What happens (lines 64-91):**

1. **Calculate totals**:
   ```python
   total_valid = sum(len(keys) for keys in valid_keys.values())
   total_invalid = sum(len(keys) for keys in invalid_keys.values())
   ```

2. **Print summary header**:
   ```
   ============================================================
     SUMMARY
   ============================================================
   ```

3. **Print totals**:
   ```
   Valid Keys Found: 5
   Invalid Keys: 23
   ```

4. **Print valid keys by type**:
   ```
   Valid Keys by Type:
     ✓ openai: 2 keys
       - sk-proj-abc123... (Valid OpenAI key)
       - sk-proj-xyz789... (Valid OpenAI key)
     ✓ google_api_key: 1 keys
       - AIzaSyAbCdEf... (Valid Google API key)
   ```

5. **Print invalid keys by type**:
   ```
   Invalid Keys by Type:
     ✗ openai: 15 keys
     ✗ perplexity: 8 keys
   ```

---

## 💾 STEP 8: Save Results to Files

### Line 129: `save_results(valid_keys, invalid_keys, found_keys)`

**What happens (lines 37-61):**

1. **Create results directory**:
   ```python
   os.makedirs("results", exist_ok=True)
   ```

2. **Generate timestamp**:
   ```python
   timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
   # Example: "20241215_143022"
   ```

3. **Save all found keys**:
   ```python
   # results/found_keys_20241215_143022.json
   {
     "openai": ["sk-proj-abc...", "sk-proj-xyz..."],
     "google_api_key": ["AIzaSyAbCdEf..."]
   }
   ```

4. **Save valid keys**:
   ```python
   # results/valid_keys_20241215_143022.json
   {
     "openai": [
       {"key": "sk-proj-abc...", "valid": true, "message": "Valid OpenAI key"}
     ]
   }
   ```

5. **Save invalid keys**:
   ```python
   # results/invalid_keys_20241215_143022.json
   {
     "openai": ["sk-proj-invalid1...", "sk-proj-invalid2..."]
   }
   ```

---

## 🎯 STEP 9: Program Completion

### Lines 134-140: Error Handling and Exit

**Success case:**
```python
print("Process completed successfully!")
```

**If user presses Ctrl+C:**
```python
except KeyboardInterrupt:
    print("Process interrupted by user.")
```

**If error occurs:**
```python
except Exception as e:
    logger.error(f"Error: {e}")
    print(f"Error: {e}")
```

---

## 📋 COMPLETE FLOW DIAGRAM

```
START
  │
  ├─> Load configuration (.env)
  │
  ├─> Initialize GitHubWebScraper
  │   ├─> Create HTTP session
  │   ├─> Set fake browser headers
  │   └─> Initialize storage
  │
  ├─> For each search query:
  │   │
  │   ├─> Search GitHub web (search_github_web)
  │   │   ├─> Build search URL
  │   │   ├─> Fetch HTML page
  │   │   ├─> Parse HTML (BeautifulSoup)
  │   │   ├─> Extract file URLs
  │   │   └─> Handle pagination
  │   │
  │   ├─> For each file URL:
  │   │   ├─> Convert to raw URL
  │   │   ├─> Fetch file content
  │   │   ├─> Extract API keys (regex patterns)
  │   │   └─> Store unique keys
  │   │
  │   └─> Delay between queries
  │
  ├─> Initialize KeyValidator
  │
  ├─> For each found key:
  │   ├─> Test against API endpoint
  │   ├─> Check response status
  │   └─> Categorize as valid/invalid
  │
  ├─> Display summary
  │
  ├─> Save results to JSON files
  │
  └─> END
```

---

## 🔑 KEY CONCEPTS EXPLAINED

### 1. **Web Scraping vs API**
- **API**: Requires token, has rate limits, structured data
- **Web Scraping**: No token needed, parses HTML, more flexible

### 2. **User Agent Rotation**
- Changes browser identity to avoid detection
- Makes requests look like different users

### 3. **Rate Limiting Protection**
- Random delays between requests
- Prevents being blocked by GitHub
- Respectful scraping

### 4. **Pattern Matching**
- Uses regex to find API keys in text
- Multiple patterns per API type
- Handles different formats

### 5. **Key Validation**
- Actually tests keys against real APIs
- Determines if keys are working
- Provides detailed feedback

---

## 📝 EXAMPLE EXECUTION

```
============================================================
  GitHub API Key Finder & Validator
============================================================

Using web scraping method (no GitHub token required!)

Step 1: Scraping GitHub for API keys (web scraping)...

Processing query 1/25: api key
Searching GitHub web for: api key
Found 50 code file URLs
Processing file 1/50: https://github.com/user/repo/blob/main/config.py
✓ Found keys in https://github.com/user/repo/blob/main/config.py: ['openai']
Processing file 2/50: ...
...

Scraping complete! Found 28 unique API keys:
  openai: 15 keys
  google_api_key: 8 keys
  perplexity: 5 keys

Found 28 unique API keys!

Step 2: Validating API keys...

Validating keys: 100%|██████████| 28/28

============================================================
  SUMMARY
============================================================

Valid Keys Found: 3
Invalid Keys: 25

Valid Keys by Type:
  ✓ openai: 2 keys
    - sk-proj-abc123... (Valid OpenAI key)
    - sk-proj-xyz789... (Valid OpenAI key)
  ✓ google_api_key: 1 keys
    - AIzaSyAbCdEf... (Valid Google API key)

Results saved to results/

Process completed successfully!
```

---

This is exactly how the program works from start to finish! 🎉

