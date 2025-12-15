import requests
import gzip
import json
import io

def save_repo_urls():
    # 1. Connect to the archive stream
    url = "https://data.gharchive.org/2024-01-01-15.json.gz"
    print(f"📥 Streaming URLs from: {url}")
    
    found_urls = set() # Use a set to avoid duplicates
    target_count = 10000

    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with gzip.open(io.BytesIO(r.content), 'rt', encoding='utf-8') as f:
                for line in f:
                    if len(found_urls) >= target_count:
                        break
                    try:
                        event = json.loads(line)
                        if event.get('type') == 'PushEvent':
                            repo = event.get('repo', {})
                            repo_name = repo.get('name')
                            # Construct the full URL
                            full_url = f"https://github.com/{repo_name}.git"
                            found_urls.add(full_url)
                    except:
                        continue
                        
    except Exception as e:
        print(f"Error: {e}")

    # 2. Save to a file
    print(f"✅ Found {len(found_urls)} unique URLs.")
    with open("repo_list.txt", "w") as f:
        for url in found_urls:
            f.write(url + "\n")
    print("💾 Saved list to 'repo_list.txt'")

if __name__ == "__main__":
    save_repo_urls()