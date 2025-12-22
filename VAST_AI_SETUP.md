# Deploying API Key Finder on Vast.ai

This guide will help you deploy and run the API Key Finder on a Vast.ai GPU instance.

## Prerequisites

- A Vast.ai account
- Basic knowledge of SSH
- The project files ready to upload

## Step 1: Choose a Template on Vast.ai

**Recommended Template**: **Ubuntu 22.04 VM** or **Ubuntu Desktop (VM)**

Why?
- Full VM access (not containerized)
- Git pre-installed
- Python can be easily installed
- Full system control for cloning repos

**Alternative**: **Linux Desktop Container** (if you prefer containerized)

## Step 2: Set Up the Instance

### 2.1 Connect via SSH

Once your instance is running, connect via SSH:
```bash
ssh root@<vast.ai-provided-ip>
```

### 2.2 Update System and Install Python

```bash
# Update package list
apt-get update

# Install Python 3.12 and pip
apt-get install -y python3.12 python3.12-venv python3-pip git

# Verify installations
python3.12 --version
git --version
```

### 2.3 Create Project Directory

```bash
# Create project directory
mkdir -p /root/api-key-finder
cd /root/api-key-finder
```

## Step 3: Upload Your Project

### Option A: Using Git (Recommended)

If your project is on GitHub:

```bash
# Clone your repository
git clone <your-repo-url> .

# Or if you need to upload manually, use SCP from your local machine:
# scp -r /path/to/local/project/* root@<vast.ai-ip>:/root/api-key-finder/
```

### Option B: Using SCP (Manual Upload)

From your local machine:
```bash
scp -r "/Users/Eric.AELLEN/Documents/A - projets pro/API KEY FINDER/1.0"/* root@<vast.ai-ip>:/root/api-key-finder/
```

### Option C: Using Vast.ai File Upload

1. Use the Vast.ai web interface file upload feature
2. Upload all project files to `/root/api-key-finder/`

## Step 4: Install Dependencies

```bash
cd /root/api-key-finder

# Create virtual environment (recommended)
python3.12 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 5: Configure the Project

### 5.1 Create Environment File (Optional)

```bash
# Copy example env file
cp env.example .env

# Edit if needed (usually defaults are fine)
nano .env
```

### 5.2 Generate Repository List (if needed)

If `repo_list.txt` is empty or missing:

```bash
python3.12 big.py
```

This will generate `repo_list.txt` with GitHub repository URLs.

## Step 6: Run the Application

### Option A: Terminal Mode (No Web Interface)

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Run the crawler directly
python3.12 run_terminal.py

# Or directly:
python3.12 downloader.py
```

### Option B: Web Interface Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run Flask app
python3.12 app.py

# The web interface will be available at:
# http://<vast.ai-ip>:8005
```

**Note**: You may need to configure Vast.ai to expose port 8005, or use SSH tunneling:

```bash
# From your local machine, create SSH tunnel:
ssh -L 8005:localhost:8005 root@<vast.ai-ip>

# Then access http://localhost:8005 in your browser
```

### Option C: Using Gunicorn (Production)

```bash
# Activate virtual environment
source venv/bin/activate

# Run with Gunicorn
gunicorn app:app --bind 0.0.0.0:8005 --workers 2 --threads 2 --timeout 120
```

## Step 7: Monitor Progress

### View Logs in Real-Time

```bash
# If running in terminal mode, logs appear directly
# If running in background, check logs:
tail -f /root/api-key-finder/*.log

# Or check output files:
tail -f found_api_keys.txt
tail -f working_api_keys.txt
```

### Check Process Status

```bash
# Check if Python processes are running
ps aux | grep python

# Check disk usage (repos are deleted after scanning)
df -h
```

## Step 8: Keep Process Running (Optional)

### Using Screen (Recommended)

```bash
# Install screen
apt-get install -y screen

# Start a screen session
screen -S api-finder

# Run your script
source venv/bin/activate
python3.12 run_terminal.py

# Detach: Press Ctrl+A then D
# Reattach: screen -r api-finder
```

### Using nohup

```bash
# Run in background with nohup
nohup python3.12 run_terminal.py > output.log 2>&1 &

# Check status
ps aux | grep python

# View output
tail -f output.log
```

## Step 9: Download Results

### Using SCP

From your local machine:
```bash
# Download results
scp root@<vast.ai-ip>:/root/api-key-finder/found_api_keys.txt ./
scp root@<vast.ai-ip>:/root/api-key-finder/working_api_keys.txt ./
```

### Using Vast.ai File Download

Use the Vast.ai web interface to download files from `/root/api-key-finder/`

## Troubleshooting

### Issue: Git not found
```bash
apt-get install -y git
```

### Issue: Python version mismatch
```bash
# Install Python 3.12 specifically
apt-get install -y python3.12 python3.12-venv
python3.12 -m venv venv
```

### Issue: Port not accessible
- Use SSH tunneling (see Option B in Step 6)
- Or configure Vast.ai port forwarding in dashboard

### Issue: Out of disk space
```bash
# Check disk usage
df -h

# Clean up downloaded repos (they should auto-delete, but check)
rm -rf downloaded_repos/*

# The project is designed to delete repos after scanning automatically
```

### Issue: Process killed
- Check instance resources: `htop` or `free -h`
- Reduce `max_workers` in `downloader.py` if memory is limited
- Use a larger instance on Vast.ai

## Recommended Vast.ai Instance Specs

**Minimum**:
- CPU: 2+ cores
- RAM: 4GB+
- Storage: 20GB+
- Network: Good (for cloning repos)

**Recommended**:
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+
- Network: Excellent

**Note**: GPU is NOT required for this project. You can rent a CPU-only instance to save costs.

## Cost Optimization Tips

1. **Use CPU instances** - No GPU needed, saves money
2. **Monitor usage** - Stop instance when not running
3. **Use spot instances** - Cheaper but may be interrupted
4. **Pre-generate repo_list.txt** - Upload it instead of generating on instance

## Security Notes

⚠️ **Important**:
- Don't expose the web interface publicly without authentication
- Use SSH tunneling for web access
- Keep your API keys secure
- Don't commit sensitive data to git

## Next Steps

1. Choose and start a Vast.ai instance
2. Follow steps 1-6 to set up
3. Run the crawler
4. Monitor progress
5. Download results when complete

Happy crawling! 🚀

