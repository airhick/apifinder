import requests
import time
import json
import random
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import sys

# --- CONFIGURATION ---
TARGET_REPOS = 1000000      # Very high number (effectively infinite)
CONTINUOUS_MODE = True      # Run continuously until Ctrl+C
BATCH_SIZE = 30             # Smaller batches for faster writes
# ---------------------

collected_repos = set()

# Headers to look like a real browser/app
headers_list = [
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15'},
    {'User-Agent': 'GitHub-Firehose-Client/1.0'}
]

# Invalid URL patterns to filter out
INVALID_PATTERNS = [
    '/trending/', '/sponsors/', '/explore/', '/topics/', '/marketplace/',
    '/settings/', '/notifications/', '/dashboard/', '/pulls/', '/issues/',
    '/new/', '/organizations/', '/login/', '/logout/', '/join/', '/pricing/',
    '/enterprise/', '/about/', '/blog/', '/contact/', '/security/', '/features/',
    '/team/', '/customer-stories/', '/resources/', '/readme/', '/site/',
    '/raw/', '/blob/', '/tree/', '/commits/', '/branches/', '/tags/', '/releases/',
    '/compare/', '/search/', '/archive/', '/network/', '/graphs/', '/pulse/',
    '/community/', '/discussions/', '/projects/', '/wiki/', '/actions/', '/security/',
    '/stargazers/', '/watchers/', '/forks/', '/insights/', '/settings/', '/releases/',
    '?since=', '?spoken_language_code=', '?tab=', '?q=', '?type='
]

def is_valid_repo_url(url):
    """
    Validate if a URL is a valid GitHub repository URL
    Format: https://github.com/username/repo (no extra path, no query params)
    """
    if not url or not isinstance(url, str):
        return False
    
    # Must start with https://github.com/
    if not url.startswith('https://github.com/'):
        return False
    
    # Remove the base URL
    path = url.replace('https://github.com/', '').strip('/')
    
    # Should be exactly username/repo format
    parts = path.split('/')
    if len(parts) != 2:
        return False
    
    username, repo = parts
    
    # Username and repo should be valid (alphanumeric, hyphens, underscores, dots)
    if not username or not repo:
        return False
    
    # Check for invalid patterns
    for pattern in INVALID_PATTERNS:
        if pattern in url.lower():
            return False
    
    # Username and repo should not be empty and should be reasonable length
    if len(username) < 1 or len(username) > 39 or len(repo) < 1 or len(repo) > 100:
        return False
    
    # Should not contain special characters that aren't allowed in GitHub usernames/repos
    if not re.match(r'^[a-zA-Z0-9._-]+$', username) or not re.match(r'^[a-zA-Z0-9._-]+$', repo):
        return False
    
    return True

def fetch_repos_from_web_search(cycle_num=0, log_callback=None, seen_queries_ref=None):
    """
    Fast method: Scrape GitHub web search directly (no API, no proxies needed)
    Uses rotating queries to find fresh repos each cycle
    """
    step_start = time.time()
    repos = []
    
    try:
        session_start = time.time()
        session = requests.Session()
        session.headers.update({
            'User-Agent': random.choice(headers_list)['User-Agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        session_time = time.time() - session_start
        
        # Rotate through many different search queries to avoid duplicates
        base_queries = [
            'stars:0', 'stars:1', 'stars:2', 'stars:3', 'stars:4', 'stars:5',
            'stars:0..1', 'stars:2..3', 'stars:4..5',
        ]
        
        # Date-based queries (rotate dates) - use more recent dates for freshness
        from datetime import datetime, timedelta
        today = datetime.now()
        date_queries = [
            f'created:>{(today - timedelta(days=i)).strftime("%Y-%m-%d")}' for i in range(1, 15)  # More date ranges
        ]
        date_queries.extend([
            f'pushed:>{(today - timedelta(days=i)).strftime("%Y-%m-%d")}' for i in range(1, 15)
        ])
        
        # Language-based queries (unpopular repos by language)
        languages = ['python', 'javascript', 'java', 'go', 'rust', 'cpp', 'c', 'php', 'ruby', 'swift', 'typescript', 'kotlin']
        lang_queries = [f'language:{lang} stars:0..5' for lang in languages]
        
        # Combine all queries for maximum diversity
        all_queries = base_queries + date_queries + lang_queries
        
        # Rotate queries aggressively based on cycle number to get fresh results
        # Use random queries to avoid duplicates - pick queries we haven't used recently
        num_queries_per_cycle = 2  # Reduced to 2 queries per cycle for speed
        
        # Get queries we haven't used recently (last 20 cycles)
        if seen_queries_ref is not None:
            available_queries = [q for q in all_queries if q not in seen_queries_ref]
            if len(available_queries) < num_queries_per_cycle:
                # Reset if we've used most queries
                seen_queries_ref.clear()
                available_queries = all_queries
            
            # Randomly select from available queries
            queries_to_use = random.sample(available_queries, min(num_queries_per_cycle, len(available_queries)))
            seen_queries_ref.update(queries_to_use)
            
            # Keep only last 30 queries in seen_queries to allow reuse
            if len(seen_queries_ref) > 30:
                seen_queries_ref.clear()  # Clear when too many
        else:
            # Fallback: use cycle-based rotation
            query_index = (cycle_num * 7) % len(all_queries)
            queries_to_use = [all_queries[(query_index + i) % len(all_queries)] for i in range(num_queries_per_cycle)]
        
        url = "https://github.com/search"
        request_times = []
        
        for query in queries_to_use:
            try:
                # Try only first page per query for maximum speed
                for page in range(1, 2):  # Only 1 page per query for speed
                    request_start = time.time()
                    # Use random sort order to get different results each time
                    sort_options = ['updated', 'stars', 'forks', 'created']
                    sort_by = random.choice(sort_options)
                    order = random.choice(['desc', 'asc'])
                    
                    params = {
                        'q': query,
                        'type': 'repositories',
                        's': sort_by,
                        'o': order,
                        'p': page
                    }
                    
                    response = session.get(url, params=params, timeout=1.0)  # Even faster timeout
                    request_time = time.time() - request_start
                    request_times.append(request_time)
                    
                    if response.status_code == 200:
                        parse_start = time.time()
                        soup = BeautifulSoup(response.content, 'lxml')
                        
                        # Find repo links - look for actual repository links in search results
                        # Search results have repos in specific containers
                        repo_links = []
                        
                        # Strategy 1: Look for links in search result items
                        search_results = soup.find_all('div', class_=re.compile(r'repo-list-item|search-result'))
                        for result in search_results:
                            link = result.find('a', href=re.compile(r'^/[^/]+/[^/]+$'))
                            if link:
                                href = link.get('href', '').lstrip('/')
                                if href:
                                    repo_url = f"https://github.com/{href}"
                                    if is_valid_repo_url(repo_url) and repo_url not in repo_links:
                                        repo_links.append(repo_url)
                        
                        # Strategy 2: Look for links with data attributes that indicate repos
                        links = soup.find_all('a', href=re.compile(r'^/[^/]+/[^/]+$'))
                        for link in links[:50]:  # Check more links
                            href = link.get('href', '').lstrip('/')
                            if href:
                                repo_url = f"https://github.com/{href}"
                                if is_valid_repo_url(repo_url) and repo_url not in repo_links:
                                    repo_links.append(repo_url)
                        
                        # Add valid repos
                        for repo_url in repo_links[:25]:  # Limit to 25 per page
                            if repo_url not in repos:
                                repos.append(repo_url)
                                if log_callback:
                                    log_callback(repo_url, "web_search")
                        parse_time = time.time() - parse_start
                    
                    # No delay between pages - maximum speed
                
            except Exception as e:
                continue
        
        step_time = time.time() - step_start
        avg_request_time = sum(request_times) / len(request_times) if request_times else 0
        if log_callback:
            print(f"  ⏱️  Web Search: {step_time:.3f}s total | {len(repos)} repos | Avg request: {avg_request_time:.3f}s | Session init: {session_time:.3f}s")
        
    except Exception as e:
        step_time = time.time() - step_start
        if log_callback:
            print(f"  ⚠️  Web Search failed: {step_time:.3f}s | Error: {str(e)[:50]}")
    
    return repos

def fetch_repos_from_events_api(log_callback=None):
    """
    Fast method: Use GitHub Events API directly (no proxy, faster)
    Gets repos from multiple event types
    """
    step_start = time.time()
    repos = []
    
    try:
        headers_start = time.time()
        url = "https://api.github.com/events"
        headers = random.choice(headers_list).copy()
        headers['Accept'] = 'application/vnd.github.v3+json'
        headers_time = time.time() - headers_start
        
        request_times = []
        # Get multiple pages for more repos - Events API is reliable
        for page in range(1, 6):  # 5 pages for more repos
            try:
                request_start = time.time()
                url_with_param = f"{url}?page={page}&per_page=30&t={random.random()}"
                response = requests.get(url_with_param, headers=headers, timeout=2.0)
                request_time = time.time() - request_start
                request_times.append(request_time)
                
                if response.status_code == 200:
                    parse_start = time.time()
                    data = response.json()
                    for event in data:
                        if 'repo' in event and event['repo']:
                            repo_data = event['repo']
                            if 'name' in repo_data and repo_data['name']:
                                repo_url = f"https://github.com/{repo_data['name']}"
                                if is_valid_repo_url(repo_url) and repo_url not in repos:
                                    repos.append(repo_url)
                                    if log_callback:
                                        log_callback(repo_url, "events_api")
                    parse_time = time.time() - parse_start
                elif response.status_code == 403 or response.status_code == 429:
                    # Rate limited - break early
                    break
            except Exception as e:
                continue
        
        step_time = time.time() - step_start
        avg_request_time = sum(request_times) / len(request_times) if request_times else 0
        if log_callback:
            print(f"  ⏱️  Events API: {step_time:.3f}s total | {len(repos)} repos | Avg request: {avg_request_time:.3f}s | Headers: {headers_time:.3f}s")
    except Exception as e:
        step_time = time.time() - step_start
        if log_callback:
            print(f"  ⚠️  Events API failed: {step_time:.3f}s | Error: {str(e)[:50]}")
    
    return repos

def fetch_repos_from_trending(log_callback=None):
    """
    Fast method: Scrape GitHub trending pages (multiple languages and timeframes)
    """
    step_start = time.time()
    repos = []
    
    try:
        session_start = time.time()
        session = requests.Session()
        session.headers.update({
            'User-Agent': random.choice(headers_list)['User-Agent'],
        })
        session_time = time.time() - session_start
        
        # Try different trending pages with languages
        languages = ['', 'python', 'javascript', 'java', 'go', 'rust']
        timeframes = ['', 'daily', 'weekly']
        
        request_times = []
        # Rotate through combinations
        for lang in languages[:3]:  # Use 3 languages per cycle
            for timeframe in timeframes[:2]:  # Use 2 timeframes
                try:
                    if lang:
                        page_url = f"https://github.com/trending/{lang}"
                    else:
                        page_url = "https://github.com/trending"
                    
                    if timeframe:
                        page_url += f"?since={timeframe}"
                    
                    request_start = time.time()
                    response = session.get(page_url, timeout=3)
                    request_time = time.time() - request_start
                    request_times.append(request_time)
                    
                    if response.status_code == 200:
                        parse_start = time.time()
                        soup = BeautifulSoup(response.content, 'lxml')
                        
                        # Trending page has repos in specific containers - look for actual repo links
                        repo_links = []
                        
                        # Strategy 1: Look for links in trending repo items
                        trending_items = soup.find_all('article', class_=re.compile(r'Box-row|d-inline-block'))
                        for item in trending_items:
                            link = item.find('a', href=re.compile(r'^/[^/]+/[^/]+$'))
                            if link:
                                href = link.get('href', '').lstrip('/')
                                if href:
                                    repo_url = f"https://github.com/{href}"
                                    if is_valid_repo_url(repo_url) and repo_url not in repo_links:
                                        repo_links.append(repo_url)
                        
                        # Strategy 2: Look for h2/h3 headings with repo links (trending page structure)
                        headings = soup.find_all(['h1', 'h2', 'h3'])
                        for heading in headings:
                            link = heading.find('a', href=re.compile(r'^/[^/]+/[^/]+$'))
                            if link:
                                href = link.get('href', '').lstrip('/')
                                if href:
                                    repo_url = f"https://github.com/{href}"
                                    if is_valid_repo_url(repo_url) and repo_url not in repo_links:
                                        repo_links.append(repo_url)
                        
                        # Strategy 3: Fallback - check all links but validate
                        links = soup.find_all('a', href=re.compile(r'^/[^/]+/[^/]+$'))
                        for link in links[:50]:
                            href = link.get('href', '').lstrip('/')
                            if href:
                                repo_url = f"https://github.com/{href}"
                                if is_valid_repo_url(repo_url) and repo_url not in repo_links:
                                    repo_links.append(repo_url)
                        
                        # Add valid repos
                        for repo_url in repo_links[:25]:
                            if repo_url not in repos:
                                repos.append(repo_url)
                                if log_callback:
                                    log_callback(repo_url, "trending")
                        parse_time = time.time() - parse_start
                    
                    time.sleep(0.1)
                except Exception as e:
                    continue
        
        step_time = time.time() - step_start
        avg_request_time = sum(request_times) / len(request_times) if request_times else 0
        if log_callback:
            print(f"  ⏱️  Trending: {step_time:.3f}s total | {len(repos)} repos | Avg request: {avg_request_time:.3f}s | Session: {session_time:.3f}s")
    except Exception as e:
        step_time = time.time() - step_start
        if log_callback:
            print(f"  ⚠️  Trending failed: {step_time:.3f}s | Error: {str(e)[:50]}")
    
    return repos

def fetch_repos_from_explore(log_callback=None):
    """
    Fast method: Scrape GitHub explore page for new repos
    """
    step_start = time.time()
    repos = []
    
    try:
        session_start = time.time()
        session = requests.Session()
        session.headers.update({
            'User-Agent': random.choice(headers_list)['User-Agent'],
        })
        session_time = time.time() - session_start
        
        explore_pages = [
            "https://github.com/explore",
            "https://github.com/explore/collections",
        ]
        
        request_times = []
        for page_url in explore_pages:
            try:
                request_start = time.time()
                response = session.get(page_url, timeout=3)
                request_time = time.time() - request_start
                request_times.append(request_time)
                
                if response.status_code == 200:
                    parse_start = time.time()
                    soup = BeautifulSoup(response.content, 'lxml')
                    
                    # Explore page - look for actual repo links
                    repo_links = []
                    links = soup.find_all('a', href=re.compile(r'^/[^/]+/[^/]+$'))
                    
                    for link in links[:30]:
                        href = link.get('href', '').lstrip('/')
                        if href:
                            repo_url = f"https://github.com/{href}"
                            if is_valid_repo_url(repo_url) and repo_url not in repo_links:
                                repo_links.append(repo_url)
                    
                    # Add valid repos
                    for repo_url in repo_links[:20]:
                        if repo_url not in repos:
                            repos.append(repo_url)
                            if log_callback:
                                log_callback(repo_url, "explore")
                    parse_time = time.time() - parse_start
            except Exception as e:
                continue
        
        step_time = time.time() - step_start
        avg_request_time = sum(request_times) / len(request_times) if request_times else 0
        if log_callback:
            print(f"  ⏱️  Explore: {step_time:.3f}s total | {len(repos)} repos | Avg request: {avg_request_time:.3f}s | Session: {session_time:.3f}s")
    except Exception as e:
        step_time = time.time() - step_start
        if log_callback:
            print(f"  ⚠️  Explore failed: {step_time:.3f}s | Error: {str(e)[:50]}")
    
    return repos

def main():
    print("🚀 Starting optimized repo finder (no threading, direct web scraping)...")
    print("⚡ Using fast methods: web search, events API, trending pages")
    print("📊 Detailed timing logs enabled - showing each step\n")
    
    start_time = time.time()
    file_open_start = time.time()
    file_handle = open("firehose_repos.txt", "a", buffering=8192)  # 8KB buffer
    file_open_time = time.time() - file_open_start
    print(f"📁 File opened: {file_open_time:.3f}s")
    
    batch_repos = []
    cycle = 0
    consecutive_zero_cycles = 0  # Track cycles with 0 repos found
    seen_queries = set()  # Track queries we've used to avoid duplicates
    
    # Log callback function to log each repo found
    def log_repo_found(repo_url, source):
        print(f"  ✓ {repo_url} - scrapped ({source})")
    
    try:
        while len(collected_repos) < TARGET_REPOS:
            cycle += 1
            cycle_start = time.time()
            new_repos_this_cycle = []
            
            # Skip logging every cycle to reduce overhead - only log every 10 cycles
            if cycle % 10 == 1:
                print(f"\n[Cycle {cycle}] Starting...")
            
            # Method 1: Events API - PRIMARY METHOD (fast and reliable)
            # Events API is fast and reliable - use it as primary method
            method2_start = time.time()
            events_repos = fetch_repos_from_events_api(log_callback=log_repo_found)
            events_new_count = 0
            for repo in events_repos:
                if is_valid_repo_url(repo) and repo not in collected_repos:
                    collected_repos.add(repo)
                    new_repos_this_cycle.append(repo)
                    events_new_count += 1
            method2_time = time.time() - method2_start
            
            # Method 2: Web search - SECONDARY (skip if too many zero cycles)
            # Web search is slow and unreliable - only use if Events API isn't working
            method1_time = 0
            skip_web_search = False
            
            # Only use web search if Events API found 0 repos AND we haven't skipped too many times
            if events_new_count == 0:
                if consecutive_zero_cycles >= 3:
                    # Skip web search for 20 cycles after 3 consecutive zeros
                    skip_web_search = True
                    consecutive_zero_cycles -= 1
                    if consecutive_zero_cycles <= -20:  # Skip for 20 cycles, then reset
                        consecutive_zero_cycles = 0
                else:
                    # Try web search
                    method1_start = time.time()
                    repos = fetch_repos_from_web_search(cycle_num=cycle, log_callback=log_repo_found, seen_queries_ref=seen_queries)
                    web_new_count = 0
                    for repo in repos:
                        if is_valid_repo_url(repo) and repo not in collected_repos:
                            collected_repos.add(repo)
                            new_repos_this_cycle.append(repo)
                            web_new_count += 1
                    method1_time = time.time() - method1_start
                    
                    # Track consecutive zero cycles for web search
                    if web_new_count == 0:
                        consecutive_zero_cycles += 1
                    else:
                        consecutive_zero_cycles = 0  # Reset counter when we find repos
            else:
                # Events API found repos - reset counter
                consecutive_zero_cycles = 0
            
            # Method 3: Trending pages (rotates languages/timeframes) - SKIP for now, too many invalid URLs
            method3_time = 0
            # Skip trending as it's finding too many invalid URLs
            # if cycle % 5 == 0:  # Only every 5th cycle
            #     method3_start = time.time()
            #     repos = fetch_repos_from_trending(log_callback=log_repo_found)
            #     for repo in repos:
            #         if is_valid_repo_url(repo) and repo not in collected_repos:
            #             collected_repos.add(repo)
            #             new_repos_this_cycle.append(repo)
            #     method3_time = time.time() - method3_start
            
            # Method 4: Explore page (additional source) - SKIP for now
            method4_time = 0
            # Skip explore as it's not finding many valid repos
            
            # Add to batch
            batch_start = time.time()
            batch_repos.extend(new_repos_this_cycle)
            batch_time = time.time() - batch_start
            
            # Write in batches for speed (write immediately if we have repos)
            write_time = 0
            if len(batch_repos) >= BATCH_SIZE or (new_repos_this_cycle and len(batch_repos) > 0):
                write_start = time.time()
                file_handle.writelines([r + "\n" for r in batch_repos])
                file_handle.flush()
                write_time = time.time() - write_start
                
                new_count = len(collected_repos)
                elapsed = time.time() - start_time
                cycle_total_time = time.time() - cycle_start
                
                if elapsed > 0:
                    speed = len(collected_repos) / elapsed
                    # Only print summary if we found repos or every 20 cycles (reduce logging)
                    if len(new_repos_this_cycle) > 0 or cycle % 20 == 0:
                        print(f"\n  📊 Cycle Summary:")
                        if method1_time > 0:
                            print(f"     • Web Search: {method1_time:.3f}s")
                        elif skip_web_search:
                            print(f"     • Web Search: SKIPPED (too many zero cycles)")
                        if method2_time > 0:
                            print(f"     • Events API: {method2_time:.3f}s")
                        if method3_time > 0:
                            print(f"     • Trending: {method3_time:.3f}s (disabled - too many invalid URLs)")
                        if method4_time > 0:
                            print(f"     • Explore: {method4_time:.3f}s")
                        print(f"     • Batch processing: {batch_time:.3f}s")
                        print(f"     • File write: {write_time:.3f}s")
                        print(f"     • Total cycle time: {cycle_total_time:.3f}s")
                        print(f"  ✅ Found: {len(new_repos_this_cycle)} new | Total: {new_count} | Speed: {speed:.1f} repos/sec | Queue: {len(batch_repos)}")
                
                batch_repos = []
            
            # Minimal delay between cycles (optimized for maximum speed)
            # If no repos found, skip delay entirely to find repos faster
            delay_start = time.time()
            if len(new_repos_this_cycle) > 0:
                time.sleep(0.01)  # 10ms if we found repos (very fast)
            # No delay if no repos found - keep searching immediately
            delay_time = time.time() - delay_start
            if delay_time > 0.005:
                print(f"  ⏸️  Delay: {delay_time:.3f}s")
        
        # Write remaining repos
        if batch_repos:
            file_handle.writelines([r + "\n" for r in batch_repos])
            file_handle.flush()
        
        file_handle.close()
        print(f"\n🏆 Finished! {len(collected_repos)} repositories saved to 'firehose_repos.txt'.")
    
    except KeyboardInterrupt:
        if batch_repos:
            file_handle.writelines([r + "\n" for r in batch_repos])
            file_handle.flush()
        file_handle.close()
        print(f"\n🛑 Scrapper stopped by user. {len(collected_repos)} repositories saved to 'firehose_repos.txt'.")
    except Exception as e:
        if batch_repos:
            file_handle.writelines([r + "\n" for r in batch_repos])
            file_handle.flush()
        file_handle.close()
        print(f"Error: {e}")

if __name__ == "__main__":
    # Clear file
    open("firehose_repos.txt", "w").close()
    main()