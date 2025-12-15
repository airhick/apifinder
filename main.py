"""
Main script for GitHub API Key Finder
"""
import os
import json
import subprocess
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from github_crawler import GitHubCrawler
from colorama import init, Fore, Style
import logging

# Initialize colorama for colored output
init(autoreset=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def print_banner():
    """Print application banner"""
    banner = f"""
    {Fore.CYAN}{'='*60}
    {Fore.CYAN}  GitHub API Key Finder & Validator
    {Fore.CYAN}{'='*60}
    {Style.RESET_ALL}
    """
    print(banner)


def save_results(valid_keys: dict, invalid_keys: dict, found_keys: dict, output_dir: str = "results"):
    """Save results to JSON files"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save all found keys
    found_keys_serializable = {k: list(v) for k, v in found_keys.items()}
    with open(f"{output_dir}/found_keys_{timestamp}.json", "w") as f:
        json.dump(found_keys_serializable, f, indent=2)
    
    # Save valid keys
    valid_keys_serializable = {
        k: [{"key": key, "valid": valid, "message": msg} for key, valid, msg in v]
        for k, v in valid_keys.items()
    }
    with open(f"{output_dir}/valid_keys_{timestamp}.json", "w") as f:
        json.dump(valid_keys_serializable, f, indent=2)
    
    # Save invalid keys
    invalid_keys_serializable = {k: list(v) for k, v in invalid_keys.items()}
    with open(f"{output_dir}/invalid_keys_{timestamp}.json", "w") as f:
        json.dump(invalid_keys_serializable, f, indent=2)
    
    logger.info(f"Results saved to {output_dir}/")


def print_summary(valid_keys: dict, invalid_keys: dict):
    """Print summary of results"""
    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"{Fore.GREEN}  SUMMARY")
    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
    
    total_valid = sum(len(keys) for keys in valid_keys.values())
    total_invalid = sum(len(keys) for keys in invalid_keys.values())
    
    print(f"{Fore.CYAN}Valid Keys Found: {Fore.GREEN}{total_valid}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Invalid Keys: {Fore.YELLOW}{total_invalid}{Style.RESET_ALL}\n")
    
    if valid_keys:
        print(f"{Fore.GREEN}Valid Keys by Type:{Style.RESET_ALL}")
        for key_type, keys in valid_keys.items():
            if keys:
                print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {key_type}: {len(keys)} keys")
                for key, valid, message in keys[:5]:  # Show first 5
                    print(f"    - {key[:20]}... ({message})")
                if len(keys) > 5:
                    print(f"    ... and {len(keys) - 5} more")
                print()
    
    if invalid_keys:
        print(f"{Fore.YELLOW}Invalid Keys by Type:{Style.RESET_ALL}")
        for key_type, keys in invalid_keys.items():
            if keys:
                print(f"  {Fore.YELLOW}✗{Style.RESET_ALL} {key_type}: {len(keys)} keys")


def main():
    """Main execution function"""
    print_banner()
    
    # Configuration
    repos_per_second = float(os.getenv("REPOS_PER_SECOND", "100.0"))  # Default: 100 repos/sec
    max_repos = int(os.getenv("MAX_REPOS", "10000"))
    
    # Info message for high speed
    if repos_per_second >= 100:
        print(f"{Fore.GREEN}High-speed mode: {repos_per_second} repos/second{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Note: This is very aggressive and may trigger rate limits.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}The program will handle rate limits automatically.{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}Starting full GitHub crawl (no token required!){Style.RESET_ALL}")
    print(f"{Fore.CYAN}Target speed: {repos_per_second} repos/second{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Max repos to crawl: {max_repos}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}🎯 Targeting unpopular repos (0-5 stars) for better key discovery{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}📁 Focusing on code files in each repository{Style.RESET_ALL}\n")
    print(f"{Fore.YELLOW}Keys will be saved immediately to:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}  - found_api_keys.txt (all found keys){Style.RESET_ALL}")
    print(f"{Fore.YELLOW}  - working_api_keys.txt (only working keys){Style.RESET_ALL}\n")
    print(f"{Fore.CYAN}Note: Initial repository discovery may take a moment...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}If you see rate limit warnings, the program will wait and retry.{Style.RESET_ALL}\n")
    
    try:
        print(f"{Fore.CYAN}Step 1: Fetching repository URLs from GitHub archive...{Style.RESET_ALL}")
        
        # Step 1: Run big.py to get repo URLs
        try:
            import big
            big.save_repo_urls()
            print(f"{Fore.GREEN}✅ Repository URLs saved to repo_list.txt{Style.RESET_ALL}\n")
        except Exception as e:
            logger.error(f"Error fetching repo URLs: {e}")
            print(f"{Fore.RED}Failed to fetch repo URLs. Make sure big.py is working.{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}Step 2: Downloading and scanning repositories for API keys...{Style.RESET_ALL}\n")
        
        # Step 2: Run downloader.py to download and scan repos
        try:
            import downloader
            downloader.bulk_downloader()
        except Exception as e:
            logger.error(f"Error in downloader: {e}")
            print(f"{Fore.RED}Error during download/scan: {e}{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}Process completed successfully!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Check found_api_keys.txt and working_api_keys.txt for results.{Style.RESET_ALL}")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Process interrupted by user (Ctrl+C).{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Results saved so far are in found_api_keys.txt and working_api_keys.txt{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()

