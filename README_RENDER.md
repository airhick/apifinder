# Deploying API Key Finder on Render

This guide will help you deploy the API Key Finder application on Render.

## Prerequisites

- A Render account (free tier works)
- A GitHub repository with this code

## Deployment Steps

### Option 1: Using Render Dashboard (Recommended)

1. **Go to Render Dashboard**
   - Visit https://dashboard.render.com
   - Sign up or log in

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository containing this code

3. **Configure the Service**
   - **Name**: `api-key-finder` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120`
   - **Plan**: Free tier is fine for testing

4. **Environment Variables** (Optional)
   - `REPOS_PER_SECOND`: Default is 100.0 (adjust as needed)
   - `MAX_REPOS`: Maximum repos to scan (default: 10000)

5. **Deploy**
   - Click "Create Web Service"
   - Render will build and deploy your app
   - Wait for deployment to complete

6. **Access Your App**
   - Once deployed, you'll get a URL like: `https://api-key-finder.onrender.com`
   - Open it in your browser to see the dashboard

### Option 2: Using render.yaml

1. **Push to GitHub**
   - Make sure `render.yaml` is in your repository root

2. **Import in Render**
   - Go to Render Dashboard
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml` and create the service automatically

## Features

Once deployed, you can:

- **Start/Stop Crawler**: Control the API key discovery process
- **View Real-time Logs**: See what's happening as it runs
- **Monitor Statistics**: Track repos scanned, keys found, and working keys
- **View Working Keys**: See the most recent working API keys found

## Important Notes

1. **Disk Space**: The app creates temporary files. Free tier has limited disk space.
2. **Rate Limiting**: GitHub may rate limit requests. The app handles this automatically.
3. **Webhook**: Make sure your webhook URL in `webhook_notifier.py` is accessible.
4. **Persistence**: Files are stored on the Render disk. They persist between deployments.

## Troubleshooting

### App won't start
- Check the logs in Render dashboard
- Make sure all dependencies are in `requirements.txt`
- Verify the start command is correct

### No logs appearing
- Check browser console for errors
- Verify Server-Sent Events (SSE) is working
- Check Render service logs

### Keys not being found
- Make sure `repo_list.txt` is being generated
- Check that `big.py` is working correctly
- Verify network connectivity

## Updating the App

1. Push changes to GitHub
2. Render will automatically detect and redeploy
3. Or manually trigger a deploy from the Render dashboard

## Cost

- **Free Tier**: 750 hours/month, 512MB RAM, 1GB disk
- **Starter Plan**: $7/month for more resources

For production use, consider upgrading to a paid plan for better performance.

