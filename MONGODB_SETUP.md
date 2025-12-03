# MongoDB Atlas Setup Guide

This guide will walk you through setting up MongoDB Atlas (free tier) and connecting it to your API.

## Why MongoDB Atlas?

- ✅ **Free tier** with 512MB storage (plenty for development)
- ✅ **Cloud-hosted** - no server management needed
- ✅ **Works with all hosting platforms** (Render, Railway, Fly.io, etc.)
- ✅ **Persistent storage** - data survives server restarts
- ✅ **Scalable** - easy to upgrade later

## Step 1: Create MongoDB Atlas Account

1. Go to https://www.mongodb.com/cloud/atlas/register
2. Sign up for a free account (no credit card required for free tier)
3. Verify your email address

## Step 2: Create a Free Cluster

1. **Login** to MongoDB Atlas dashboard
2. Click **"Build a Database"** or **"Create"** → **"Database"**
3. Choose **FREE (M0)** tier
4. Select a **Cloud Provider** (AWS, Google Cloud, or Azure)
5. Choose a **Region** closest to your API hosting location
   - For Render.com: Choose same region as your API
   - For Railway: Any region is fine
6. Click **"Create"**

**Note:** Cluster creation takes 1-3 minutes.

## Step 3: Create Database User

1. Once cluster is created, you'll see a security dialog
2. **Create Database User:**
   - **Username:** `flower-api-user` (or any username)
   - **Password:** Click "Autogenerate Secure Password" (copy this password!)
   - **Database User Privileges:** "Read and write to any database"
3. Click **"Create Database User"**

**⚠️ IMPORTANT:** Save the password! You'll need it for the connection string.

## Step 4: Configure Network Access

1. In the security dialog, configure **Network Access**
2. Click **"Add IP Address"**
3. For development/testing, click **"Allow Access from Anywhere"** (adds `0.0.0.0/0`)
   - This allows your API to connect from any location
4. For production, you can restrict to specific IPs later
5. Click **"Finish and Close"**

## Step 5: Get Connection String

1. Click **"Connect"** button on your cluster
2. Choose **"Connect your application"**
3. Select **"Python"** and version **"3.6 or later"**
4. **Copy the connection string** - it looks like:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
5. Replace `<username>` with your database username
6. Replace `<password>` with your database password (the one you saved!)
7. Add your database name at the end (before `?`):
   ```
   mongodb+srv://flower-api-user:yourpassword@cluster0.xxxxx.mongodb.net/flower_classifications?retryWrites=true&w=majority
   ```

## Step 6: Set Environment Variables

### For Local Development

Create a `.env` file in your project root:

```bash
MONGODB_URL=mongodb+srv://flower-api-user:yourpassword@cluster0.xxxxx.mongodb.net/flower_classifications?retryWrites=true&w=majority
MONGODB_DATABASE=flower_classifications
PORT=8000
CORS_ORIGINS=*
```

### For Cloud Deployment (Render.com)

1. Go to your Render dashboard
2. Select your service
3. Go to **"Environment"** tab
4. Add environment variable:
   - **Key:** `MONGODB_URL`
   - **Value:** Your full connection string (from Step 5)
5. Add another variable:
   - **Key:** `MONGODB_DATABASE`
   - **Value:** `flower_classifications`

### For Railway.app

1. Go to your Railway project
2. Select your service
3. Go to **"Variables"** tab
4. Add environment variables:
   - `MONGODB_URL` = your connection string
   - `MONGODB_DATABASE` = `flower_classifications`

### For Fly.io

1. Set environment variables via CLI:
   ```bash
   fly secrets set MONGODB_URL="your-connection-string"
   fly secrets set MONGODB_DATABASE="flower_classifications"
   ```

## Step 7: Test Connection

After setting environment variables, test your API:

```bash
# Start your API
uvicorn app.main:app --reload

# Test health check (should show "connected")
curl http://localhost:8000/

# Test classification
curl -X POST http://localhost:8000/api/classify \
  -F "file=@IMG_1905.jpeg"
```

## Security Best Practices

### For Production:

1. **Restrict Network Access:**
   - In MongoDB Atlas, go to **Network Access**
   - Remove `0.0.0.0/0` if you added it
   - Add your API hosting platform's IP ranges (or specific IPs)

2. **Use Environment Variables:**
   - Never commit connection strings to git
   - Always use environment variables

3. **Strong Passwords:**
   - Use auto-generated secure passwords
   - Store them securely (password manager)

4. **Database User Permissions:**
   - Create specific database users with minimal required permissions
   - Don't use the admin user for API access

## Troubleshooting

### "Failed to connect to MongoDB"

1. **Check connection string:**
   - Ensure username and password are correct (no `<` or `>` brackets)
   - Ensure database name is included in the URL

2. **Check network access:**
   - Ensure your IP is whitelisted in MongoDB Atlas
   - For cloud hosting, you may need to add `0.0.0.0/0` initially

3. **Check environment variable:**
   ```bash
   echo $MONGODB_URL  # Should show your connection string
   ```

### "Authentication failed"

- Double-check username and password
- Ensure no special characters need URL encoding
- Try regenerating the database user password

### Connection Timeout

- Check if you're behind a firewall
- Ensure MongoDB Atlas cluster is running (not paused)
- Try a different region if latency is high

## Viewing Your Data

1. Go to MongoDB Atlas dashboard
2. Click **"Browse Collections"**
3. Select your database: `flower_classifications`
4. View the `classifications` collection
5. See all your stored classifications with images (as base64)

## MongoDB Atlas Free Tier Limits

- **Storage:** 512 MB (usually enough for thousands of images)
- **RAM:** Shared
- **No credit card required**
- Perfect for development and small production apps

## Next Steps

Once connected:
1. ✅ Your API will store all classifications in MongoDB
2. ✅ Images are stored as base64 in MongoDB documents
3. ✅ Data persists across server restarts
4. ✅ You can view/query data in MongoDB Atlas dashboard

## Need Help?

- MongoDB Atlas Docs: https://docs.atlas.mongodb.com/
- Connection String Help: https://docs.atlas.mongodb.com/reference/connection-string/
- MongoDB Community Forums: https://developer.mongodb.com/community/forums/

