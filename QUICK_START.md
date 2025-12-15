# Quick Start - Deploy to Render

## 🚀 Deploy in 3 Steps

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### Step 2: Deploy on Render
1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect GitHub and select your repository
4. Render auto-detects `render.yaml` - just click **"Apply"**

### Step 3: Access Your App
Once deployed, you'll get a URL like:
```
https://api-key-finder.onrender.com
```

Open it in your browser! 🎉

## ✅ What's Included

- ✅ `render.yaml` - Auto-configuration for Render
- ✅ `runtime.txt` - Python 3.12.0 specification
- ✅ `Procfile` - Process configuration
- ✅ `requirements.txt` - All dependencies
- ✅ Production-ready `app.py` with proper logging
- ✅ Web interface with real-time logs

## 📝 Optional: Environment Variables

In Render dashboard → Environment tab, you can set:
- `REPOS_PER_SECOND`: `100.0` (default)
- `MAX_REPOS`: `10000` (default)

## 🐛 Troubleshooting

**App won't start?**
- Check Render logs in dashboard
- Verify all files are pushed to GitHub

**No logs showing?**
- Check browser console (F12)
- Verify service is running in Render dashboard

## 📚 More Info

See `DEPLOYMENT.md` for detailed deployment guide.

