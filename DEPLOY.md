# Quick Deploy Guide

## Deploy to Render in 5 Minutes

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Add web interface for Render deployment"
git push origin main
```

### Step 2: Deploy on Render

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub account
4. Select your repository
5. Configure:
   - **Name**: `api-key-finder`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120`
6. Click "Create Web Service"
7. Wait for deployment (2-3 minutes)

### Step 3: Access Your App

Once deployed, you'll get a URL like:
```
https://api-key-finder.onrender.com
```

Open it in your browser to see the dashboard!

## Features

✅ **Web Dashboard**: Beautiful interface to control the crawler
✅ **Real-time Logs**: See what's happening live
✅ **Statistics**: Track progress in real-time
✅ **Start/Stop**: Control the crawler from the web interface
✅ **Working Keys**: View recently found working API keys

## Local Testing

Before deploying, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web app
python app.py

# Or use gunicorn (production-like)
gunicorn app:app --bind 0.0.0.0:5000 --workers 2
```

Then open http://localhost:5000 in your browser.

## Environment Variables (Optional)

In Render dashboard, you can set:
- `REPOS_PER_SECOND`: Speed of crawling (default: 100.0)
- `MAX_REPOS`: Maximum repos to scan (default: 10000)

## Troubleshooting

**App won't start?**
- Check Render logs
- Make sure all files are committed to GitHub
- Verify `requirements.txt` has all dependencies

**No logs showing?**
- Check browser console (F12)
- Verify Server-Sent Events is enabled
- Check Render service logs

**Keys not being found?**
- Make sure `big.py` can access GitHub
- Check network connectivity
- Verify rate limits aren't blocking

## Notes

- Free tier has 750 hours/month
- Files persist on Render disk
- Webhook notifications are sent automatically
- All working keys are saved to `working_api_keys.txt`

