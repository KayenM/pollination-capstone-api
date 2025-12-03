# Architecture Overview

This document explains how all the pieces fit together for your full-stack application.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vercel)                       │
│  Your React/Next.js/Vue/etc. application                    │
│  - Calls API endpoints                                       │
│  - Displays heatmaps and classifications                    │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP Requests (CORS-enabled)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Backend API (Render/Railway/Fly.io)              │
│  FastAPI Application                                         │
│  - /api/classify - Upload and classify images               │
│  - /api/heatmap-data - Get all classification data          │
│  - /api/images/{id} - Get stored images                     │
└────────────────────┬────────────────────────────────────────┘
                     │ MongoDB Connection
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              MongoDB Atlas (Cloud Database)                  │
│  - Stores all classifications                                │
│  - Stores images as base64                                   │
│  - Persistent storage                                        │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend (Vercel)

**What it is:**
- Your React, Next.js, Vue, or any frontend framework
- Hosted on Vercel (free tier available)

**What it does:**
- Users upload images through your UI
- Displays heatmaps showing flower classifications
- Shows individual classification results

**Configuration:**
- Set API endpoint to your backend URL (e.g., `https://your-api.onrender.com`)
- Make HTTP requests to `/api/classify`, `/api/heatmap-data`, etc.

### 2. Backend API (Render/Railway/Fly.io)

**What it is:**
- FastAPI Python application (this repository)
- Hosted on cloud platform (Render.com recommended)

**What it does:**
- Receives image uploads from frontend
- Runs ML model for classification
- Stores data in MongoDB
- Serves heatmap data to frontend

**Environment Variables:**
```bash
MONGODB_URL=mongodb+srv://...  # From MongoDB Atlas
MONGODB_DATABASE=flower_classifications
PORT=8000  # Auto-set by platform
CORS_ORIGINS=https://your-frontend.vercel.app
```

### 3. MongoDB Atlas (Database)

**What it is:**
- Cloud-hosted MongoDB database
- Free tier: 512MB storage

**What it does:**
- Stores all classification records
- Stores images as base64-encoded strings
- Provides persistent storage (survives server restarts)

**Configuration:**
- Connection string from MongoDB Atlas dashboard
- Set as `MONGODB_URL` environment variable in backend

## Deployment Flow

### Step 1: Set Up MongoDB Atlas

1. Create account at https://www.mongodb.com/cloud/atlas
2. Create free cluster
3. Get connection string
4. See `MONGODB_SETUP.md` for detailed instructions

### Step 2: Deploy Backend API

1. Push code to GitHub
2. Deploy to Render.com/Railway/Fly.io
3. Set environment variables (including `MONGODB_URL`)
4. Get backend URL (e.g., `https://your-api.onrender.com`)

### Step 3: Deploy Frontend

1. Deploy frontend to Vercel
2. Set API endpoint to backend URL
3. Configure CORS (already done in backend if you set `CORS_ORIGINS`)

## Important Notes

### About Vercel

**Vercel is for your FRONTEND**, not the backend:
- ✅ Deploy your React/Next.js frontend to Vercel
- ❌ Cannot run Python/FastAPI backend on Vercel
- ✅ Backend goes on Render/Railway/Fly.io
- ✅ Backend connects to MongoDB Atlas

### Data Flow

1. **User uploads image** → Frontend (Vercel)
2. **Frontend sends image** → Backend API (Render)
3. **Backend processes image** → ML model classification
4. **Backend saves data** → MongoDB Atlas
5. **Backend returns results** → Frontend
6. **Frontend displays** → User sees classification

### CORS Configuration

The backend allows requests from your frontend domain:

```bash
# In backend environment variables
CORS_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
```

Or for development:
```bash
CORS_ORIGINS=*
```

## Example Frontend Code

```javascript
// In your frontend (React example)
const API_URL = 'https://your-api.onrender.com';

async function classifyImage(imageFile) {
  const formData = new FormData();
  formData.append('file', imageFile);
  
  const response = await fetch(`${API_URL}/api/classify`, {
    method: 'POST',
    body: formData,
  });
  
  const result = await response.json();
  console.log('Classification:', result);
}

async function getHeatmapData() {
  const response = await fetch(`${API_URL}/api/heatmap-data`);
  const data = await response.json();
  return data.data_points;
}
```

## Security Considerations

1. **CORS:** Restrict to your frontend domain in production
2. **MongoDB:** Use strong passwords, restrict network access
3. **Environment Variables:** Never commit secrets to git
4. **API Keys:** If you add authentication later, store securely

## Cost Breakdown (Free Tier)

- **Vercel Frontend:** Free (hobby plan)
- **Render Backend:** Free (spins down after inactivity)
- **MongoDB Atlas:** Free (512MB storage)
- **Total:** $0/month 🎉

## Quick Start Checklist

- [ ] Set up MongoDB Atlas (see `MONGODB_SETUP.md`)
- [ ] Deploy backend to Render/Railway (see `DEPLOYMENT.md`)
- [ ] Set `MONGODB_URL` environment variable in backend
- [ ] Deploy frontend to Vercel
- [ ] Set API endpoint in frontend to backend URL
- [ ] Test full flow!

## Need Help?

- Backend deployment: See `DEPLOYMENT.md`
- MongoDB setup: See `MONGODB_SETUP.md`
- API documentation: Visit `https://your-api-url/docs` when deployed

