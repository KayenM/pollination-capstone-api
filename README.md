# Tomato Plant Flower Classification API

A FastAPI backend for detecting and classifying tomato plant flowers by growth stage using ML.

## Features

- **Image Classification**: Upload images of tomato plants to detect flowers and classify their growth stage
- **GPS Extraction**: Automatically extracts location from image EXIF metadata
- **Database Storage**: Stores all classifications with images for later retrieval
- **Heatmap Data**: Returns all location and classification data for frontend heatmap visualization

## Flower Stages

| Stage | Name | Description |
|-------|------|-------------|
| 0 | Bud | Early flower bud stage |
| 1 | Anthesis | Active flowering stage |
| 2 | Post-Anthesis | After flowering, fruit development |

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Tests

```bash
# Quick standalone test (local)
python run_test.py

# Full pytest suite (local)
pytest tests/test_api.py -v

# Test live deployed API
curl https://capstone-077z.onrender.com/
```

### 3. Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

**Note:** You'll need MongoDB configured. See Database section below.

## API Endpoints

### `POST /api/classify`
Upload an image for flower classification.

**Request:**
- `file`: Image file (JPEG, PNG, etc.)
- `latitude` (optional): Manual GPS latitude
- `longitude` (optional): Manual GPS longitude

**Response:**
```json
{
  "id": "uuid",
  "image_path": "/api/images/uuid",
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  "timestamp": "2025-12-03T10:30:00Z",
  "flowers": [
    {
      "bounding_box": [100, 150, 200, 250],
      "stage": 1,
      "confidence": 0.95
    }
  ],
  "flower_count": 5,
  "stage_summary": {"0": 2, "1": 2, "2": 1}
}
```

### `GET /api/heatmap-data`
Get all classification data for heatmap visualization.

**Response:**
```json
{
  "total_records": 10,
  "data_points": [
    {
      "id": "uuid",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "timestamp": "2025-12-03T10:30:00Z",
      "flowers": [...],
      "total_flowers": 5,
      "stage_counts": {"0": 2, "1": 2, "2": 1}
    }
  ]
}
```

### `GET /api/classifications/{id}`
Get a specific classification by ID.

### `GET /api/images/{id}`
Get the original image for a classification.

### `DELETE /api/classifications/{id}`
Delete a classification and its image.

## API Documentation

**Live API:** https://capstone-077z.onrender.com

- **Swagger UI:** https://capstone-077z.onrender.com/docs

For local development:
- Swagger UI: http://localhost:8000/docs

## Project Structure

```
capstone/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application and routes
│   ├── database_mongodb.py  # MongoDB database setup
│   ├── config.py            # Environment variable configuration
│   ├── models.py            # Pydantic request/response models
│   ├── ml_model.py          # ML model interface (dummy for now)
│   └── utils.py             # EXIF GPS extraction utilities
├── tests/
│   ├── __init__.py
│   └── test_api.py          # Pytest test suite
├── requirements.txt
├── Dockerfile               # Docker configuration for Render
├── run_test.py              # Standalone test script
└── README.md
```

## ML Model Integration

The `app/ml_model.py` file contains a dummy implementation that will be replaced with the actual PyTorch model. The interface is:

```python
def classify_image(image_bytes: bytes) -> List[Dict]:
    """
    Returns list of detections:
    [
        {
            "bounding_box": [x_min, y_min, x_max, y_max],
            "stage": 0|1|2,
            "confidence": 0.0-1.0
        }
    ]
    """
```

To integrate your actual model:
1. Replace `load_model()` with your PyTorch model loading code
2. Update `preprocess_image()` with your model's preprocessing
3. Update `run_inference()` with your model's inference code

## Database

**Uses MongoDB Atlas** for persistent cloud storage. Images are stored as base64 in MongoDB documents.

### Setting Up MongoDB Atlas

1. Go to https://www.mongodb.com/cloud/atlas/register
2. Create a free cluster (M0 tier, 512MB storage)
3. Create a database user and get your connection string
4. Configure network access to allow connections
5. Set environment variable with your connection string

### Local Development

Set the MongoDB connection string as an environment variable:
```bash
export MONGODB_URL="mongodb+srv://username:password@cluster.mongodb.net/flower_classifications"
```

Then start the server:
```bash
uvicorn app.main:app --reload
```

## Deployment

This API is deployed on **Render.com** with **MongoDB Atlas** for persistent storage.

### Live Deployment

**API URL:** https://capstone-077z.onrender.com

The API is fully deployed and operational. All data is stored in MongoDB Atlas.

### Deploying Your Own Instance

1. **Set up MongoDB Atlas:**
   - Create account at https://www.mongodb.com/cloud/atlas
   - Create free cluster (M0 tier)
   - Get connection string

2. **Deploy to Render.com:**
   - Push code to GitHub
   - Create new Web Service on Render
   - Set `MONGODB_URL` environment variable with your connection string
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Deploy!

### Architecture

- **Frontend:** Can be deployed on Vercel or any static hosting
- **Backend API:** Deployed on Render.com (this repository)
- **Database:** MongoDB Atlas (cloud-hosted MongoDB)
- **Storage:** Images stored as base64 in MongoDB documents

## Environment Variables

```bash
# Required - MongoDB connection string
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/flower_classifications?appName=FreeTier

# Optional
MONGODB_DATABASE=flower_classifications  # Defaults to this if not specified
PORT=8000  # Server port (auto-set by Render, uses $PORT)
CORS_ORIGINS=*  # Allowed frontend origins (comma-separated, * for all)
```

### Setting Environment Variables on Render

1. Go to Render dashboard → Your service
2. Click "Environment" tab
3. Add `MONGODB_URL` with your connection string
4. Add any other variables as needed
5. Service will auto-redeploy

**Important:** Never commit `.env` files or connection strings to GitHub! Always use environment variables.

