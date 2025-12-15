"""
GitHub web scraper - Bypasses GitHub API by scraping the web interface directly
"""
import time
import re
import random
from typing import List, Dict, Set, Optional
from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
from config import API_KEY_PATTERNS, GITHUB_SEARCH_QUERIES
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubWebScraper:
    def __init__(self):
        """Initialize web scraper without requiring GitHub token"""
        self.session = requests.Session()
        self.ua = UserAgent()
        self.found_keys: Dict[str, Set[str]] = {key_type: set() for key_type in API_KEY_PATTERNS.keys()}
        self.processed_urls: Set[str] = set()
        self.processed_raw_urls: Set[str] = set()
        
        # Rotate user agents to avoid detection
        self._update_user_agent()
        
        logger.info("GitHub web scraper initialized (no token required)")
    
    def _update_user_agent(self):
        """Update session with random user agent"""
        try:
            user_agent = self.ua.random
            self.session.headers.update({
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
        except Exception:
            # Fallback user agent
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
    
    def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Add random delay to avoid rate limiting"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def search_github_web(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Search GitHub using web interface (bypasses API)
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of code file information
        """
        results = []
        
        try:
            # GitHub code search URL
            search_url = f"https://github.com/search"
            params = {
                'q': query,
                'type': 'code',
                's': 'indexed',  # Sort by indexed (most recent)
                'o': 'desc',
                'p': 1  # Page number
            }
            
            logger.info(f"Searching GitHub web for: {query}")
            
            # Try multiple pages
            for page in range(1, min(6, (max_results // 10) + 2)):  # GitHub shows ~10 results per page
                if len(results) >= max_results:
                    break
                
                params['p'] = page
                
                try:
                    response = self.session.get(search_url, params=params, timeout=15)
                    
                    if response.status_code == 429:
                        logger.warning("Rate limited. Waiting 30 seconds...")
                        time.sleep(30)
                        continue
                    
                    if response.status_code != 200:
                        logger.warning(f"Unexpected status code: {response.status_code}")
                        break
                    
                    soup = BeautifulSoup(response.content, 'lxml')
                    
                    # Multiple strategies to find code file links
                    found_links = set()
                    
                    # Strategy 1: Find code-list-item divs
                    code_results = soup.find_all('div', class_='code-list-item')
                    
                    # Strategy 2: Find data-testid elements
                    if not code_results:
                        code_results = soup.find_all('div', {'data-testid': 'code-search-result'})
                    
                    # Strategy 3: Find all links with /blob/ pattern
                    all_blob_links = soup.find_all('a', href=re.compile(r'/blob/'))
                    
                    # Process structured results
                    for result in code_results:
                        if len(found_links) >= max_results:
                            break
                        
                        # Extract file URL from structured result
                        link = result.find('a', href=re.compile(r'/blob/'))
                        if link:
                            href = link.get('href', '')
                            if href and '/blob/' in href:
                                found_links.add(href)
                    
                    # Process direct blob links if we didn't find enough
                    if len(found_links) < max_results:
                        for link in all_blob_links:
                            if len(found_links) >= max_results:
                                break
                            href = link.get('href', '')
                            if href and '/blob/' in href:
                                found_links.add(href)
                    
                    # Convert to results format
                    for href in found_links:
                        if len(results) >= max_results:
                            break
                        
                        full_url = f"https://github.com{href}" if not href.startswith('http') else href
                        
                        if full_url not in self.processed_urls:
                            # Extract repository and file path
                            parts = href.split('/blob/')
                            if len(parts) == 2:
                                repo_path = parts[0].lstrip('/')
                                file_path = parts[1]
                            else:
                                repo_path = ""
                                file_path = href.split('/')[-1] if '/' in href else ""
                            
                            results.append({
                                "url": full_url,
                                "repository": repo_path,
                                "path": file_path,
                            })
                    
                    # Random delay between pages
                    self._random_delay(2, 4)
                    
                    # Rotate user agent occasionally
                    if page % 3 == 0:
                        self._update_user_agent()
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Request error on page {page}: {e}")
                    self._random_delay(5, 10)
                    continue
                except Exception as e:
                    logger.warning(f"Error parsing page {page}: {e}")
                    continue
            
            logger.info(f"Found {len(results)} code file URLs for query: {query}")
            
        except Exception as e:
            logger.error(f"Error in web search: {e}")
        
        return results
    
    def get_raw_file_content(self, github_url: str) -> Optional[str]:
        """
        Get raw file content from GitHub URL
        
        Args:
            github_url: GitHub file URL (e.g., https://github.com/user/repo/blob/main/file.py)
            
        Returns:
            File content as string or None
        """
        if github_url in self.processed_raw_urls:
            return None
        
        self.processed_raw_urls.add(github_url)
        
        try:
            # Convert GitHub URL to raw content URL
            # https://github.com/user/repo/blob/branch/file.py
            # -> https://raw.githubusercontent.com/user/repo/branch/file.py
            if '/blob/' in github_url:
                raw_url = github_url.replace('github.com/', 'raw.githubusercontent.com/').replace('/blob/', '/')
            else:
                raw_url = github_url.replace('github.com/', 'raw.githubusercontent.com/')
            
            response = self.session.get(raw_url, timeout=10)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.debug(f"File not found: {raw_url}")
            elif response.status_code == 429:
                logger.warning("Rate limited on raw content. Waiting...")
                time.sleep(30)
            else:
                logger.debug(f"Unexpected status {response.status_code} for {raw_url}")
            
        except Exception as e:
            logger.debug(f"Error fetching raw content: {e}")
        
        return None
    
    def extract_api_keys(self, content: str, url: str) -> Dict[str, List[str]]:
        """
        Extract API keys from content using pattern matching
        
        Args:
            content: Text content to search
            url: URL of the content (for deduplication)
            
        Returns:
            Dictionary mapping key types to list of found keys
        """
        found = {}
        
        if url in self.processed_urls:
            return found
        
        self.processed_urls.add(url)
        
        for key_type, patterns in API_KEY_PATTERNS.items():
            for pattern in patterns:
                matches = pattern.findall(content)
                if matches:
                    if key_type not in found:
                        found[key_type] = []
                    
                    for match in matches:
                        # Handle tuple matches (from groups)
                        key = match if isinstance(match, str) else match[0] if match else None
                        if key and len(key) >= 16:  # Minimum key length
                            # Clean up the key
                            key = key.strip('"\'')
                            if key not in self.found_keys[key_type]:
                                found[key_type].append(key)
                                self.found_keys[key_type].add(key)
        
        return found
    
    def scrape_all(self, max_results_per_query: int = 50) -> Dict[str, Set[str]]:
        """
        Scrape GitHub for all API keys using web scraping
        
        Args:
            max_results_per_query: Maximum results per search query
            
        Returns:
            Dictionary of found keys by type
        """
        logger.info(f"Starting GitHub web scrape with {len(GITHUB_SEARCH_QUERIES)} search queries")
        logger.info("Using web scraping (no GitHub token required)")
        
        for i, query in enumerate(GITHUB_SEARCH_QUERIES, 1):
            logger.info(f"Processing query {i}/{len(GITHUB_SEARCH_QUERIES)}: {query}")
            
            try:
                # Search for code files
                code_results = self.search_github_web(query, max_results_per_query)
                logger.info(f"Found {len(code_results)} code file URLs")
                
                # Fetch and process each file
                for j, result in enumerate(code_results, 1):
                    try:
                        logger.debug(f"Processing file {j}/{len(code_results)}: {result['url']}")
                        
                        # Get raw file content
                        content = self.get_raw_file_content(result["url"])
                        
                        if content:
                            # Extract API keys
                            found_keys = self.extract_api_keys(content, result["url"])
                            if found_keys:
                                logger.info(f"✓ Found keys in {result['url']}: {list(found_keys.keys())}")
                        
                        # Delay between files to avoid rate limiting
                        if j % 5 == 0:
                            self._random_delay(2, 4)
                        else:
                            self._random_delay(0.5, 1.5)
                        
                        # Rotate user agent every 10 files
                        if j % 10 == 0:
                            self._update_user_agent()
                    
                    except Exception as e:
                        logger.warning(f"Error processing file {result.get('url', 'unknown')}: {e}")
                        continue
                
                # Delay between queries
                logger.info(f"Completed query {i}/{len(GITHUB_SEARCH_QUERIES)}")
                self._random_delay(3, 6)
                
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
                self._random_delay(5, 10)
                continue
        
        # Print summary
        total_keys = sum(len(keys) for keys in self.found_keys.values())
        logger.info(f"\nScraping complete! Found {total_keys} unique API keys:")
        for key_type, keys in self.found_keys.items():
            if keys:
                logger.info(f"  {key_type}: {len(keys)} keys")
        
        return self.found_keys
    
    def get_found_keys(self) -> Dict[str, Set[str]]:
        """Get all found keys"""
        return self.found_keys

