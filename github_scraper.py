"""
GitHub scraper for finding API keys in public repositories
"""
import time
import re
from typing import List, Dict, Set
from github import Github
from github.GithubException import RateLimitExceededException, BadCredentialsException
from config import API_KEY_PATTERNS, GITHUB_SEARCH_QUERIES
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubScraper:
    def __init__(self, github_token: str = None):
        """
        Initialize GitHub scraper
        
        Args:
            github_token: GitHub personal access token (optional but recommended for higher rate limits)
        """
        if github_token:
            self.github = Github(github_token)
            logger.info("GitHub client initialized with token")
        else:
            self.github = Github()
            logger.warning("GitHub client initialized without token - lower rate limits")
        
        self.found_keys: Dict[str, Set[str]] = {key_type: set() for key_type in API_KEY_PATTERNS.keys()}
        self.processed_urls: Set[str] = set()
    
    def search_code(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search GitHub code for a specific query
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of code search results
        """
        results = []
        try:
            code_results = self.github.search_code(query, sort="indexed", order="desc")
            count = 0
            
            for code in code_results:
                if count >= max_results:
                    break
                
                try:
                    result = {
                        "url": code.html_url,
                        "repository": code.repository.full_name,
                        "path": code.path,
                        "content": code.decoded_content.decode('utf-8', errors='ignore') if code.decoded_content else "",
                    }
                    results.append(result)
                    count += 1
                except Exception as e:
                    logger.warning(f"Error processing code result: {e}")
                    continue
                    
        except RateLimitExceededException:
            logger.error("Rate limit exceeded. Waiting 60 seconds...")
            time.sleep(60)
        except BadCredentialsException:
            logger.error("Invalid GitHub credentials")
        except Exception as e:
            logger.error(f"Error searching code: {e}")
        
        return results
    
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
        Scrape GitHub for all API keys
        
        Args:
            max_results_per_query: Maximum results per search query
            
        Returns:
            Dictionary of found keys by type
        """
        logger.info(f"Starting GitHub scrape with {len(GITHUB_SEARCH_QUERIES)} search queries")
        
        for i, query in enumerate(GITHUB_SEARCH_QUERIES, 1):
            logger.info(f"Processing query {i}/{len(GITHUB_SEARCH_QUERIES)}: {query}")
            
            try:
                code_results = self.search_code(query, max_results_per_query)
                logger.info(f"Found {len(code_results)} code results for query: {query}")
                
                for result in code_results:
                    found_keys = self.extract_api_keys(result["content"], result["url"])
                    if found_keys:
                        logger.info(f"Found keys in {result['url']}: {list(found_keys.keys())}")
                
                # Rate limiting - be respectful
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
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

