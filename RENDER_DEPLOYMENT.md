# Render.com Deployment Guide

Complete step-by-step guide to deploy your API to Render.com securely.

## 🔒 Security First

**IMPORTANT:** Never commit secrets to GitHub! We'll use Render's environment variables to store your MongoDB credentials securely.

## Prerequisites

- ✅ GitHub account
- ✅ Code pushed to a GitHub repository
- ✅ MongoDB Atlas account with connection string ready
- ✅ Render.com account (free tier available)

---

## Step 1: Prepare Your Code Repository

### 1.1 Remove Hardcoded Secrets

Before pushing to GitHub, make sure no secrets are hardcoded:

1. **Check for hardcoded MongoDB URLs:**
   ```bash
   # Search for any hardcoded connection strings
   grep -r "mongodb+srv://" . --exclude-dir=.git
   ```

2. **Files that should NOT be committed:**
   - `.env` files (already in .gitignore)
   - `test_api_mongodb.py` (if it has hardcoded credentials)
   - Any files with actual passwords

### 1.2 Verify .gitignore

Make sure `.gitignore` includes:
```
.env
.env.local
*.log
test_api_mongodb.py
TEST_RESULTS.md
```

### 1.3 Commit and Push to GitHub

```bash
# Add all files (except those in .gitignore)
git add .

# Commit
git commit -m "Ready for Render deployment"

# Push to GitHub
git push origin main
```

---

## Step 2: Create Render Account

1. Go to https://render.com
2. Click **"Get Started for Free"**
3. Sign up with GitHub (recommended for easy repo access)
4. Verify your email

---

## Step 3: Create New Web Service

1. In Render dashboard, click **"New +"** → **"Web Service"**
2. If prompted, **connect your GitHub account** (if not already connected)
3. **Select your repository** from the list
4. Click **"Connect"**

---

## Step 4: Configure Service Settings

### 4.1 Basic Settings

- **Name:** `tomato-flower-api` (or any name you like)
- **Region:** Choose closest to your users (e.g., `Oregon (US West)`)
- **Branch:** `main` (or your default branch)
- **Root Directory:** Leave empty (or `./` if your app is in root)
- **Runtime:** `Python 3`
- **Build Command:** 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command:**
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

### 4.2 Plan Selection

- **Free Plan:** Free tier (spins down after 15 min inactivity)
- **Starter Plan:** $7/month (always on)

For testing, **Free Plan** is fine.

### 4.3 Environment Variables ⚠️ SECURITY

**This is critical!** Add your MongoDB connection string here, NOT in code.

Click **"Add Environment Variable"** and add:

#### Required Variables:

1. **MONGODB_URL**
   - **Key:** `MONGODB_URL`
   - **Value:** Your full connection string:
     ```
     mongodb+srv://flower-api-user:YOUR_PASSWORD@freetier.nnomdg6.mongodb.net/flower_classifications?appName=FreeTier
     ```
   - ⚠️ Replace `YOUR_PASSWORD` with your actual MongoDB password
   - 🔒 This is stored securely in Render, not in your code

2. **MONGODB_DATABASE** (Optional)
   - **Key:** `MONGODB_DATABASE`
   - **Value:** `flower_classifications`
   - (This is optional, it's the default)

#### Optional Variables:

3. **CORS_ORIGINS**
   - **Key:** `CORS_ORIGINS`
   - **Value:** For development: `*`
   - **Value:** For production: `https://your-frontend.vercel.app`
   - (Allows your frontend to call the API)

4. **PORT**
   - **Key:** `PORT`
   - **Value:** `8000`
   - (Render sets this automatically, but you can specify)

### 4.4 Example Environment Variables Screen:

```
Environment Variables:
┌─────────────────────────────────────────────────────────┐
│ Key              │ Value                                 │
├──────────────────┼───────────────────────────────────────┤
│ MONGODB_URL      │ mongodb+srv://flower-api-user:...    │
│ MONGODB_DATABASE │ flower_classifications                │
│ CORS_ORIGINS     │ *                                     │
└──────────────────┴───────────────────────────────────────┘
```

**Important:**
- ✅ Secrets are stored securely in Render
- ✅ Not visible in your code
- ✅ Not committed to GitHub
- ✅ Can be updated without code changes

---

## Step 5: Create Service

1. Review all settings
2. Click **"Create Web Service"**
3. Render will:
   - Clone your repository
   - Install dependencies
   - Build your application
   - Deploy it

**Wait 3-5 minutes** for the first deployment.

---

## Step 6: Monitor Deployment

### 6.1 Check Build Logs

1. Watch the **"Logs"** tab during deployment
2. Look for:
   - ✅ "Installing dependencies..."
   - ✅ "Build successful"
   - ✅ "Starting service..."

### 6.2 Common Issues

**Issue: "Module not found"**
- Check `requirements.txt` includes all dependencies
- Verify Python version (should be 3.11+)

**Issue: "Port already in use"**
- Make sure start command uses `$PORT` environment variable
- Command should be: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Issue: "Failed to connect to MongoDB"**
- Double-check `MONGODB_URL` environment variable
- Verify MongoDB Atlas network access allows Render's IPs
- Test connection string locally first

---

## Step 7: Verify Deployment

### 7.1 Get Your API URL

After deployment, Render provides a URL:
```
https://tomato-flower-api.onrender.com
```
(Copy this URL - you'll need it!)

### 7.2 Test Health Check

Open in browser or use curl:
```bash
curl https://tomato-flower-api.onrender.com/
```

Expected response:
```json
{
    "status": "healthy",
    "database": "connected",
    "timestamp": "2025-12-03T..."
}
```

If `database: "connected"`, MongoDB is working! ✅

### 7.3 Test Classification Endpoint

```bash
curl -X POST https://tomato-flower-api.onrender.com/api/classify \
  -F "file=@IMG_1905.jpeg"
```

### 7.4 View API Documentation

Visit:
```
https://tomato-flower-api.onrender.com/docs
```

You'll see the interactive Swagger UI!

---

## Step 8: Configure MongoDB Atlas Network Access

### 8.1 Allow Render IPs

1. Go to MongoDB Atlas dashboard
2. Click **"Network Access"** (left sidebar)
3. Click **"Add IP Address"**
4. For now, click **"Allow Access from Anywhere"** (adds `0.0.0.0/0`)
   - This allows Render's servers to connect
   - You can restrict later for better security

5. Click **"Confirm"**

### 8.2 For Production (Optional)

Later, you can:
- Get Render's IP ranges (contact Render support)
- Add specific IP addresses
- Remove `0.0.0.0/0` for better security

---

## Step 9: Update Frontend (When Ready)

Once your API is deployed, update your frontend to use the Render URL:

```javascript
// In your frontend code
const API_URL = 'https://tomato-flower-api.onrender.com';

// Example fetch
const response = await fetch(`${API_URL}/api/classify`, {
  method: 'POST',
  body: formData,
});
```

---

## Security Checklist ✅

Before going live, verify:

- [ ] ✅ No secrets in GitHub repository
- [ ] ✅ `.env` file is in `.gitignore`
- [ ] ✅ MongoDB password stored only in Render environment variables
- [ ] ✅ Connection string doesn't appear in code
- [ ] ✅ Test files with secrets are not committed
- [ ] ✅ API is accessible (health check works)
- [ ] ✅ MongoDB connection is working

---

## Environment Variables Reference

### Required:
```bash
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/flower_classifications?appName=FreeTier
```

### Optional:
```bash
MONGODB_DATABASE=flower_classifications  # Default value
CORS_ORIGINS=*                           # Allow all origins
PORT=8000                                # Auto-set by Render
```

---

## Troubleshooting

### "Database: error" in Health Check

1. **Check MongoDB URL:**
   - Go to Render → Your Service → Environment
   - Verify `MONGODB_URL` is set correctly
   - Check for typos in username/password

2. **Check MongoDB Atlas:**
   - Verify cluster is running (not paused)
   - Check Network Access allows connections
   - Verify database user exists and password is correct

3. **Test Connection:**
   - Try connecting from your local machine first
   - Use the same connection string to test

### Service Keeps Crashing

1. **Check Logs:**
   - Go to Render → Your Service → Logs
   - Look for error messages
   - Common: Missing dependencies, port issues

2. **Check Start Command:**
   - Should be: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Must use `$PORT` (not hardcoded `8000`)

### Slow First Request (Free Tier)

- Free tier spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds
- This is normal for free tier
- Upgrade to Starter ($7/month) for always-on

---

## Quick Reference

### Your API URLs:

- **Health Check:** `https://your-service.onrender.com/`
- **API Docs:** `https://your-service.onrender.com/docs`
- **Classify:** `POST https://your-service.onrender.com/api/classify`
- **Heatmap Data:** `GET https://your-service.onrender.com/api/heatmap-data`

### Update Environment Variables:

1. Go to Render dashboard
2. Select your service
3. Go to **Environment** tab
4. Click **"Add Environment Variable"** or edit existing
5. Click **"Save Changes"**
6. Service will automatically redeploy

---

## Next Steps

1. ✅ API deployed on Render
2. ✅ MongoDB connected
3. 📝 Deploy frontend to Vercel
4. 📝 Update frontend to use Render API URL
5. 📝 Test full stack!

## Need Help?

- Render Docs: https://render.com/docs
- Render Status: https://status.render.com
- Check deployment logs in Render dashboard

---

**🎉 Congratulations! Your API is now live on Render.com!**

