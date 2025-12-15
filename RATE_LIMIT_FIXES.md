# Rate Limit & Error Handling Improvements

## Problem
The crawler was getting rate limited frequently and experiencing connection errors, causing the program to fail or slow down significantly.

## Solutions Implemented

### 1. **Retry Logic with Exponential Backoff**
- Added `_make_request_with_retry()` method
- Automatically retries failed requests up to 3 times
- Uses exponential backoff: 30s, 60s, 120s delays
- Handles connection errors gracefully

### 2. **Better Rate Limit Handling**
- Detects 429 (rate limit) responses
- Automatically waits with increasing delays
- Rotates user agent on each retry
- Skips problematic queries instead of failing completely

### 3. **Improved Connection Error Handling**
- Catches `ConnectionError`, `Timeout`, and other request exceptions
- Retries with exponential backoff
- Logs errors for debugging
- Continues crawling even if some requests fail

### 4. **Reduced Request Frequency**
- Increased delays between pages (0.5s → 2s)
- Increased delays between language searches (1s → 3s)
- Reduced number of pages per query (10 → 5)
- Reduced language list (21 → 10 languages)

### 5. **User Agent Rotation**
- Rotates user agent every 3 pages
- Rotates on connection errors
- Rotates on rate limits
- Makes requests appear more natural

### 6. **Smarter Query Skipping**
- If a query gets rate limited multiple times, skips it
- Continues with other queries instead of failing
- Logs which queries were skipped

## How It Works Now

### Request Flow:
```
1. Make request
   ↓
2. Check response status
   ↓
3. If 429 (rate limited):
   - Wait 30s (first attempt)
   - Wait 60s (second attempt)  
   - Wait 120s (third attempt)
   - Rotate user agent
   - Retry
   ↓
4. If connection error:
   - Wait with exponential backoff
   - Rotate user agent
   - Retry
   ↓
5. If success: Return response
   If all retries fail: Return None and continue
```

### Error Recovery:
- **Rate Limited**: Automatically waits and retries
- **Connection Error**: Waits and retries with new user agent
- **Server Error (5xx)**: Retries with backoff
- **Client Error (4xx)**: Skips (no retry needed)

## Benefits

✅ **More Resilient**: Handles rate limits and errors gracefully
✅ **Continues Crawling**: Doesn't stop on errors
✅ **Better Performance**: Smarter retry logic prevents wasted time
✅ **Less Aggressive**: Reduced request frequency to avoid bans
✅ **Better Logging**: Clear messages about what's happening

## Configuration

The delays are now:
- **Between pages**: 2 seconds
- **Between language searches**: 3 seconds  
- **Rate limit wait**: 30-120 seconds (exponential)
- **Connection error wait**: 30-120 seconds (exponential)

## Usage

The program will now:
1. Handle rate limits automatically
2. Retry failed requests
3. Continue crawling even with errors
4. Log what's happening for debugging

You should see fewer rate limit errors and the program should continue working even when GitHub rate limits occur.

