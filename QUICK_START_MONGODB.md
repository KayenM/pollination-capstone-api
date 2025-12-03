# Quick Start: MongoDB Setup

## Overview

Your API now uses **MongoDB Atlas** (free tier) for persistent storage instead of SQLite. Here's how to set it up:

## Step-by-Step Setup

### 1. Create MongoDB Atlas Account (5 minutes)

1. Go to https://www.mongodb.com/cloud/atlas/register
2. Sign up (no credit card required for free tier)
3. Verify email

### 2. Create Free Cluster (3 minutes)

1. Click **"Build a Database"**
2. Select **FREE (M0)** tier
3. Choose provider/region (any is fine)
4. Click **"Create"**
5. Wait 1-3 minutes for cluster to be ready

### 3. Create Database User (2 minutes)

1. In security dialog, create user:
   - Username: `flower-api-user` (or your choice)
   - Password: Click **"Autogenerate Secure Password"** (COPY THIS!)
   - Click **"Create Database User"**

2. Configure Network Access:
   - Click **"Add IP Address"**
   - Click **"Allow Access from Anywhere"** (adds `0.0.0.0/0`)
   - Click **"Finish and Close"**

### 4. Get Connection String (2 minutes)

1. Click **"Connect"** on your cluster
2. Choose **"Connect your application"**
3. Select **Python** → **3.6 or later**
4. Copy the connection string

5. **Edit the connection string:**
   ```
   Original: mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   
   Replace <username> with: flower-api-user (or your username)
   Replace <password> with: your-password (the one you copied!)
   Add database name: mongodb+srv://flower-api-user:your-password@cluster0.xxxxx.mongodb.net/flower_classifications?retryWrites=true&w=majority
   ```

### 5. Set Environment Variable

#### For Local Testing:

Create `.env` file (or export):
```bash
export MONGODB_URL="mongodb+srv://flower-api-user:your-password@cluster0.xxxxx.mongodb.net/flower_classifications?retryWrites=true&w=majority"
```

#### For Render.com Deployment:

1. Go to Render dashboard → Your service
2. Go to **Environment** tab
3. Add variable:
   - **Key:** `MONGODB_URL`
   - **Value:** Your full connection string
4. Save

#### For Railway.app Deployment:

1. Go to Railway dashboard → Your service
2. Go to **Variables** tab
3. Add:
   - `MONGODB_URL` = your connection string

### 6. Test It!

```bash
# Start your API
uvicorn app.main:app --reload

# Check health (should show "connected")
curl http://localhost:8000/

# Test classification
curl -X POST http://localhost:8000/api/classify \
  -F "file=@IMG_1905.jpeg"
```

## Complete Example Connection String

```
mongodb+srv://flower-api-user:MySecureP@ssw0rd123@cluster0.abc123.mongodb.net/flower_classifications?retryWrites=true&w=majority
```

**Important:** 
- Replace username and password with your actual values
- Keep the database name `flower_classifications` (or change it everywhere)

## Troubleshooting

**"Failed to connect to MongoDB"**
- ✅ Check username/password are correct (no `<` `>` brackets)
- ✅ Ensure database name is in URL: `/flower_classifications?`
- ✅ Check network access allows `0.0.0.0/0` (for now)

**"Authentication failed"**
- ✅ Double-check password (no typos)
- ✅ Make sure you copied the password correctly

**Connection timeout**
- ✅ Ensure cluster is running (not paused)
- ✅ Check your internet connection
- ✅ Try different region if latency is high

## What's Next?

1. ✅ Set up MongoDB Atlas (you just did this!)
2. ✅ Deploy backend to Render/Railway with `MONGODB_URL`
3. ✅ Deploy frontend to Vercel
4. ✅ Connect frontend to backend URL

See `ARCHITECTURE.md` for full system overview!

## Need More Help?

- Detailed setup: See `MONGODB_SETUP.md`
- Architecture: See `ARCHITECTURE.md`
- MongoDB Atlas docs: https://docs.atlas.mongodb.com/

---

**Note about Vercel:** Vercel is for your **frontend**. Your backend (this API) goes on Render/Railway/Fly.io. They connect to MongoDB Atlas. See `ARCHITECTURE.md` for details!

