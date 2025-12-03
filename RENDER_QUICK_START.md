# Render.com Deployment - Quick Start Guide

**Complete step-by-step instructions to deploy your API securely to Render.com**

---

## ⚠️ Security First!

**Never commit secrets to GitHub!** We'll store MongoDB credentials in Render's environment variables only.

---

## Pre-Deployment Checklist

Before starting, make sure:

- [ ] Your code is pushed to GitHub
- [ ] No hardcoded MongoDB passwords in your code
- [ ] `.gitignore` includes `.env` files
- [ ] You have your MongoDB connection string ready

---

## Step 1: Push Code to GitHub

```bash
# Make sure you're in your project directory
cd /Users/kmehta/workspace/capstone

# Check what will be committed (should NOT include .env or test files with secrets)
git status

# Add files
git add .

# Commit
git commit -m "Ready for Render deployment"

# Push to GitHub
git push origin main
```

---

## Step 2: Create Render Account

1. Go to **https://render.com**
2. Click **"Get Started for Free"**
3. Sign up with **GitHub** (easiest option)
4. Authorize Render to access your repositories
5. Verify your email

---

## Step 3: Create Web Service

1. In Render dashboard, click **"New +"** → **"Web Service"**
2. **Connect Repository:**
   - Select your GitHub repository from the list
   - Click **"Connect"**
3. **Configure Service:**
   - **Name:** `tomato-flower-api` (or your preferred name)
   - **Region:** Choose closest to your users (e.g., `Oregon (US West)`)
   - **Branch:** `main`
   - **Root Directory:** Leave empty
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** `Free` (for testing) or `Starter` ($7/month for always-on)

---

## Step 4: Add Environment Variables 🔒

**This is the most important step!**

Click **"Advanced"** → **"Add Environment Variable"**

### Add These Variables:

#### 1. MONGODB_URL (Required)
- **Key:** `MONGODB_URL`
- **Value:** Your connection string:
  ```
  mongodb+srv://flower-api-user:n1a32gnRzcEvhnbZ@freetier.nnomdg6.mongodb.net/flower_classifications?appName=FreeTier
  ```
- ⚠️ **Replace** `n1a32gnRzcEvhnbZ` with your actual MongoDB password
- ✅ This is stored securely in Render, NOT in your code

#### 2. MONGODB_DATABASE (Optional)
- **Key:** `MONGODB_DATABASE`
- **Value:** `flower_classifications`
- (This is optional, it's the default)

#### 3. CORS_ORIGINS (Optional)
- **Key:** `CORS_ORIGINS`
- **Value:** `*` (for development) or your frontend URL
- Example: `https://your-app.vercel.app`

---

## Step 5: Create and Deploy

1. Review all settings
2. Scroll down and click **"Create Web Service"**
3. **Wait 3-5 minutes** for:
   - Repository cloning
   - Dependency installation
   - Application build
   - Service deployment

Watch the **"Logs"** tab to see progress!

---

## Step 6: Get Your API URL

After deployment completes:

1. Render shows your service URL at the top:
   ```
   https://tomato-flower-api.onrender.com
   ```
2. **Copy this URL** - you'll need it!

---

## Step 7: Test Your Deployed API

### 7.1 Health Check

Open in browser or use curl:
```bash
curl https://tomato-flower-api.onrender.com/
```

**Expected response:**
```json
{
    "status": "healthy",
    "database": "connected",
    "timestamp": "2025-12-03T..."
}
```

✅ If `"database": "connected"` → MongoDB is working!

### 7.2 Test Classification

```bash
curl -X POST https://tomato-flower-api.onrender.com/api/classify \
  -F "file=@IMG_1905.jpeg"
```

### 7.3 View API Documentation

Visit in browser:
```
https://tomato-flower-api.onrender.com/docs
```

You'll see interactive Swagger UI! 🎉

---

## Step 8: Configure MongoDB Atlas Network Access

1. Go to **MongoDB Atlas Dashboard**
2. Click **"Network Access"** (left sidebar)
3. Click **"Add IP Address"**
4. Click **"Allow Access from Anywhere"** (adds `0.0.0.0/0`)
   - This allows Render's servers to connect
5. Click **"Confirm"**

⚠️ **Note:** For production, you can restrict this later for better security.

---

## Troubleshooting

### "Database: error" in Health Check

1. **Check MongoDB URL in Render:**
   - Go to Render → Your Service → Environment tab
   - Verify `MONGODB_URL` is correct
   - Check username and password

2. **Check MongoDB Atlas:**
   - Verify cluster is running
   - Check Network Access allows `0.0.0.0/0`
   - Verify user credentials

### Service Won't Start

1. **Check Logs:**
   - Go to Render → Your Service → Logs
   - Look for error messages

2. **Common Issues:**
   - Wrong start command (must use `$PORT`)
   - Missing dependencies in `requirements.txt`
   - Python version mismatch

### Slow First Request (Free Tier)

- Free tier spins down after 15 minutes
- First request after spin-down takes ~30 seconds
- This is normal! Upgrade to Starter ($7/month) for always-on

---

## Your API is Live! 🎉

Your API URL: `https://your-service.onrender.com`

### Available Endpoints:

- **Health:** `GET /`
- **Classify:** `POST /api/classify`
- **Heatmap Data:** `GET /api/heatmap-data`
- **Get Classification:** `GET /api/classifications/{id}`
- **Get Image:** `GET /api/images/{id}`
- **API Docs:** `GET /docs`

---

## Next Steps

1. ✅ API deployed
2. ✅ MongoDB connected
3. 📝 Deploy frontend to Vercel
4. 📝 Update frontend to use your Render API URL
5. 📝 Test full stack!

---

## Security Reminder

✅ **DO:**
- Store secrets in Render environment variables
- Use `.gitignore` to exclude `.env` files
- Test locally before deploying

❌ **DON'T:**
- Commit `.env` files to GitHub
- Hardcode passwords in code
- Share connection strings publicly

---

**For detailed instructions, see `RENDER_DEPLOYMENT.md`**

