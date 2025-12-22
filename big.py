import requests
import gzip
import json
import io
from datetime import datetime, timedelta, timezone

def save_repo_urls():
    """
    Fetch recent repositories (updated in the last week) from GitHub Archive
    """
    # Calculate date threshold (1 week ago)
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    print(f"📅 Looking for repositories updated after: {one_week_ago.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    found_urls = set()  # Use a set to avoid duplicates
    target_count = 10000
    
    # Get recent archive files (last 7 days, checking multiple hours per day)
    base_url = "https://data.gharchive.org"
    current_date = datetime.now(timezone.utc)
    
    # Try to fetch from recent hours (last 7 days, checking multiple hours per day)
    hours_to_check = []
    for day_offset in range(7):  # Last 7 days
        check_date = current_date - timedelta(days=day_offset)
        # Check more hours per day for better coverage (every 3 hours)
        for hour in range(0, 24, 3):  # 0, 3, 6, 9, 12, 15, 18, 21
            hours_to_check.append((check_date, hour))
    
    print(f"📥 Checking {len(hours_to_check)} archive files for recent repositories...")
    print(f"🎯 Target: {target_count} repositories\n")
    
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
                                        if event_date >= one_week_ago.replace(tzinfo=None):
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
                    
                    print(f"✅ {repos_found_in_file} repos found ({events_processed} events processed) | Total: {len(found_urls)}/{target_count}")
                        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {str(e)[:50]}")
            continue
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            continue

    # Save to file
    print(f"\n✅ Found {len(found_urls)} unique recent repositories (updated in last week).")
    with open("repo_list.txt", "w") as f:
        for url in found_urls:
            f.write(url + "\n")
    print(f"💾 Saved list to 'repo_list.txt'")
    
    if len(found_urls) < target_count:
        print(f"⚠️  Only found {len(found_urls)} repos (target was {target_count})")
        print(f"   This is normal when filtering for recent repos only.")
    else:
        print(f"🎉 Successfully found {len(found_urls)} repos! Target reached!")

if __name__ == "__main__":
    save_repo_urls()
