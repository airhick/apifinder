# Deployment Guide - Render via GitHub

This guide will help you deploy the API Key Finder application on Render using GitHub.

## Prerequisites

- A GitHub account
- A Render account (free tier works)
- Your code pushed to a GitHub repository

## Step-by-Step Deployment

### Step 1: Prepare Your Repository

1. **Ensure all files are committed**:
   ```bash
   git add .
   git commit -m "Ready for Render deployment"
   ```

2. **Push to GitHub**:
   ```bash
   git push origin main
   ```
   (Replace `main` with your branch name if different)

### Step 2: Deploy on Render

#### Option A: Using render.yaml (Recommended - Automatic)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Blueprint"
3. Connect your GitHub account (if not already connected)
4. Select your repository
5. Render will automatically detect `render.yaml` and configure everything
6. Review the settings and click "Apply"
7. Wait for deployment (2-5 minutes)

#### Option B: Manual Setup

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub account (if not already connected)
4. Select your repository
5. Configure the service:
   - **Name**: `api-key-finder` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -`
   - **Python Version**: `3.12.0` (or leave blank to auto-detect)
6. Click "Create Web Service"

### Step 3: Configure Environment Variables (Optional)

In the Render dashboard, go to your service → "Environment" tab:

- `REPOS_PER_SECOND`: `100.0` (default, adjust as needed)
- `MAX_REPOS`: `10000` (default, adjust as needed)

### Step 4: Access Your Application

Once deployed, Render will provide a URL like:
```
https://api-key-finder.onrender.com
```

Open this URL in your browser to access the web dashboard.

## File Structure for Deployment

The following files are required for deployment:

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── runtime.txt           # Python version (3.12.0)
├── render.yaml           # Render configuration (optional but recommended)
├── Procfile              # Process file (optional, render.yaml takes precedence)
├── templates/
│   └── index.html        # Web interface
├── config.py             # Configuration
├── downloader.py         # Download module
├── github_crawler.py     # Crawler module
├── key_validator.py      # Key validation
├── webhook_notifier.py   # Webhook notifications
└── big.py                # Repository URL fetcher
```

## Important Notes

### Disk Persistence

Render provides persistent disk storage. Files created during runtime (like `found_api_keys.txt`, `working_api_keys.txt`, `repo_list.txt`) will persist between deployments.

### Rate Limiting

- GitHub may rate limit requests
- The app handles rate limits automatically
- Consider adjusting `REPOS_PER_SECOND` if you encounter issues

### Resource Limits (Free Tier)

- **RAM**: 512MB
- **CPU**: Shared
- **Disk**: 1GB (can be increased with disk mount)
- **Hours**: 750 hours/month
- **Sleep**: Services sleep after 15 minutes of inactivity

### Upgrading to Paid Plans

For production use, consider upgrading:
- **Starter**: $7/month - More RAM, no sleep
- **Standard**: $25/month - Even more resources

## Troubleshooting

### App Won't Start

1. **Check Build Logs**:
   - Go to your service in Render dashboard
   - Click "Logs" tab
   - Look for build errors

2. **Common Issues**:
   - Missing dependencies in `requirements.txt`
   - Python version mismatch (check `runtime.txt`)
   - Port binding issues (should use `$PORT`)

### No Logs Showing in Web Interface

1. **Check Browser Console** (F12):
   - Look for JavaScript errors
   - Check Network tab for failed requests

2. **Check Render Logs**:
   - Verify the app is running
   - Check for Server-Sent Events (SSE) errors

### Keys Not Being Found

1. **Check Network Connectivity**:
   - Verify GitHub is accessible
   - Check rate limiting status

2. **Check Logs**:
   - Look for error messages in the web interface
   - Check Render service logs

### Service Keeps Sleeping (Free Tier)

Free tier services sleep after 15 minutes of inactivity. To prevent this:
- Upgrade to a paid plan
- Use a cron job to ping your service periodically
- Accept that the service will sleep and wake up on first request

## Updating Your Deployment

1. **Make Changes Locally**:
   ```bash
   # Make your changes
   git add .
   git commit -m "Update application"
   git push origin main
   ```

2. **Render Auto-Deploys**:
   - Render automatically detects pushes to your repository
   - It will rebuild and redeploy automatically
   - You can also manually trigger a deploy from the dashboard

## Monitoring

### View Logs

- **Render Dashboard**: Go to your service → "Logs" tab
- **Web Interface**: Real-time logs in the dashboard
- **API Endpoint**: `/api/logs` returns all logs

### View Statistics

- **Web Dashboard**: Real-time stats displayed
- **API Endpoint**: `/api/stats` returns current statistics

## Security Considerations

⚠️ **Important**: 
- Never commit `.env` files or API keys to GitHub
- Use Render's environment variables for sensitive data
- The `.gitignore` file excludes sensitive files
- Review found keys responsibly

## Support

If you encounter issues:
1. Check Render's documentation: https://render.com/docs
2. Review the application logs
3. Check GitHub issues (if applicable)

## Next Steps

After deployment:
1. Access your web dashboard
2. Click "Start Crawler" to begin
3. Monitor logs and statistics
4. View found working keys

Enjoy your deployed API Key Finder! 🚀

