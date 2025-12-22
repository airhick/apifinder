import requests
import gzip
import json
import io
from datetime import datetime, timedelta
import concurrent.futures
import time

def save_repo_urls():
    """
    Fetch recent repositories (updated in the last week) from GitHub Archive
    """
    # Calculate date threshold (1 week ago)
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    print(f"📅 Looking for repositories updated after: {one_week_ago.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    found_urls = set()  # Use a set to avoid duplicates
    target_count = 10000
    
    # Get recent archive files (last 7 days, checking multiple hours per day)
    base_url = "https://data.gharchive.org"
    current_date = datetime.utcnow()
    
    # Try to fetch from recent hours (last 7 days, checking 4 hours per day for speed)
    hours_to_check = []
    for day_offset in range(7):  # Last 7 days
        check_date = current_date - timedelta(days=day_offset)
        # Check 4 hours per day (0, 6, 12, 18) for better coverage
        for hour in [0, 6, 12, 18]:
            hours_to_check.append((check_date, hour))
    
    print(f"📥 Checking {len(hours_to_check)} archive files for recent repositories...")
    
    for check_date, hour in hours_to_check:
        if len(found_urls) >= target_count:
            break
            
        # Format: YYYY-MM-DD-H.json.gz
        date_str = check_date.strftime('%Y-%m-%d')
        url = f"{base_url}/{date_str}-{hour}.json.gz"
        
        try:
            print(f"  📂 Checking {date_str} hour {hour}...", end=" ")
            with requests.get(url, stream=True, timeout=30) as r:
                if r.status_code != 200:
                    print(f"❌ Not available")
                    continue
                
                r.raise_for_status()
                content = r.content
                
                with gzip.open(io.BytesIO(content), 'rt', encoding='utf-8') as f:
                    events_processed = 0
                    repos_found_in_file = 0
                    
                    for line in f:
                        if len(found_urls) >= target_count:
                            break
                        
                        try:
                            event = json.loads(line)
                            
                            # Check if event is a PushEvent
                            if event.get('type') == 'PushEvent':
                                # Check event timestamp (must be within last week)
                                created_at = event.get('created_at')
                                if created_at:
                                    try:
                                        # Parse ISO 8601 format: "2024-01-01T12:00:00Z" or "2024-01-01T12:00:00+00:00"
                                        # Extract date part: YYYY-MM-DD
                                        date_part = created_at.split('T')[0]  # Get YYYY-MM-DD part
                                        time_part = created_at.split('T')[1] if 'T' in created_at else '00:00:00'
                                        time_part = time_part.split('Z')[0].split('+')[0].split('.')[0]  # Remove timezone and microseconds
                                        
                                        # Parse date and time
                                        event_date = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
                                        
                                        # Only include events from the last week
                                        if event_date >= one_week_ago:
                                            repo = event.get('repo', {})
                                            repo_name = repo.get('name')
                                            if repo_name:
                                                # Construct the full URL
                                                full_url = f"https://github.com/{repo_name}.git"
                                                found_urls.add(full_url)
                                                repos_found_in_file += 1
                                    except (ValueError, TypeError, AttributeError, IndexError):
                                        # If date parsing fails, skip this event
                                        continue
                                
                                events_processed += 1
                                
                        except (json.JSONDecodeError, KeyError):
                            continue
                    
                    print(f"✅ {repos_found_in_file} repos found ({events_processed} events processed)")
                        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {str(e)[:50]}")
            continue
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            continue

    # 2. Filter repositories with 0 stars
    print(f"\n🔍 Checking star count for {len(found_urls)} repositories...")
    print(f"   Filtering for repositories with 0 stars only...")
    
    zero_star_repos = []
    checked_count = 0
    
    def check_repo_stars(repo_url):
        """Check if a repository has 0 stars"""
        try:
            # Extract repo name from URL: https://github.com/username/repo.git
            repo_name = repo_url.replace('https://github.com/', '').replace('.git', '')
            
            # Use GitHub API to check stars (no auth needed for public repos)
            api_url = f"https://api.github.com/repos/{repo_name}"
            response = requests.get(api_url, timeout=5, headers={'Accept': 'application/vnd.github.v3+json'})
            
            if response.status_code == 200:
                repo_data = response.json()
                stars = repo_data.get('stargazers_count', -1)
                return repo_url, stars == 0
            elif response.status_code == 404:
                # Repo doesn't exist or is private
                return repo_url, False
            else:
                # Rate limited or other error - skip for now
                return repo_url, None
        except Exception as e:
            return repo_url, None
    
    # Check stars in parallel (20 workers for API calls)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(check_repo_stars, url): url for url in found_urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            checked_count += 1
            try:
                repo_url, has_zero_stars = future.result()
                
                if has_zero_stars is True:
                    zero_star_repos.append(repo_url)
                
                # Progress update every 100 repos
                if checked_count % 100 == 0:
                    print(f"   ✅ Checked {checked_count}/{len(found_urls)} repos | Found {len(zero_star_repos)} with 0 stars")
                
                # Rate limiting: small delay to avoid hitting GitHub API limits
                if checked_count % 30 == 0:
                    time.sleep(1)  # 1 second pause every 30 requests
                    
            except Exception as e:
                continue
    
    # 3. Save to a file
    print(f"\n✅ Found {len(zero_star_repos)} repositories with 0 stars (updated in last week).")
    with open("repo_list.txt", "w") as f:
        for url in zero_star_repos:
            f.write(url + "\n")
    print(f"💾 Saved list to 'repo_list.txt'")
    
    if len(zero_star_repos) < target_count:
        print(f"⚠️  Only found {len(zero_star_repos)} repos with 0 stars (target was {target_count})")
        print(f"   This is normal when filtering for recent repos with 0 stars only.")

if __name__ == "__main__":
    save_repo_urls()