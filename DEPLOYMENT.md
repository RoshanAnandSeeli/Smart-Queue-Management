# Railway Deployment Guide for SmartQ

## Prerequisites
- GitHub account (to host your code)
- Railway account (free at railway.app)

---

## Step 1: Initialize Git Repository

Navigate to your project folder and initialize git:

```bash
cd "c:\Users\Roshan Anand\Documents\Karunya\Semester-2\Entrepreneurship\Micro Project\Prototype site\Smart Queue Management"

git init
git add .
git commit -m "Initial commit - SmartQ deployment"
```

---

## Step 2: Create a GitHub Repository

1. Go to **github.com** and create a new repository called `smartq-queue-management`
2. Follow the instructions to push your local code:

```bash
git remote add origin https://github.com/YOUR_USERNAME/smartq-queue-management.git
git branch -M main
git push -u origin main
```

---

## Step 3: Deploy to Railway

### Option A: Using Railway Dashboard (Easiest)

1. Go to **railway.app** and sign up with GitHub
2. Click **"New Project"** → **"GitHub Repo"**
3. Search and select your `smartq-queue-management` repository
4. Railway will automatically:
   - Detect Python from `runtime.txt`
   - Install dependencies from `requirements.txt`
   - Run the app using `Procfile`

### Option B: Using Railway CLI

1. Install Railway CLI: https://docs.railway.app/develop/cli
2. Login:
   ```bash
   railway login
   ```
3. Create and deploy:
   ```bash
   railway init
   railway up
   ```

---

## Step 4: Configure Environment Variables (Important!)

In Railway Dashboard, go to **Variables** and add:

```
GROQ_API_KEY = your_groq_api_key_here
```

⚠️ **Note:** Move your API key to environment variables in production (don't hardcode in app.py)

---

## Step 5: Get Your Public URL

Once deployed, Railway will give you a public URL like:
```
https://smartq-xyz123.railway.app
```

This is your live app! ✅

---

## Files You Now Have:

✅ **requirements.txt** - Python dependencies  
✅ **Procfile** - How to run your app  
✅ **runtime.txt** - Python version  
✅ **app.py** - Updated with environment variables  
✅ **.gitignore** - What to exclude from git  

---

## Important Notes:

1. **Data Persistence**: Your current app stores queue data in memory. When Railway restarts your app, data is lost. For production, use a database:
   - PostgreSQL (Railway has built-in support)
   - MongoDB
   - SQLite with file storage

2. **Admin Password**: Change `admin123` to something secure in production

3. **GROQ API Key**: Keep this secret! Move it to Railway environment variables

4. **Multiple Instances**: If you want to run multiple queues simultaneously (multiple stores), each needs its own Railway project or deploy multiple services.

---

## Updating Your App

After deploying, to update your app:

```bash
git add .
git commit -m "Update: your changes here"
git push origin main
```

Railway will automatically redeploy!

---

## Troubleshooting

- Check logs in Railway Dashboard
- Make sure `requirements.txt` has all your dependencies
- Verify `Procfile` format is correct: `web: python app.py`
- Check environment variables are set correctly

