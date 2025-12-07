# Tomato Plant Flower Classification API

A FastAPI backend for detecting and classifying tomato plant flowers by growth stage using ML.

## Features

- **Image Classification**: Upload images of tomato plants to detect flowers and classify their growth stage
- **GPS Extraction**: Automatically extracts location from image EXIF metadata
- **Database Storage**: Stores all classifications with images for later retrieval
- **Heatmap Data**: Returns all location and classification data for frontend heatmap visualization

## Software Architecture

The API follows a three-tier architecture deployed on the cloud. The **presentation layer** consists of RESTful endpoints built with FastAPI, handling HTTP requests and responses with automatic OpenAPI documentation. The **business logic layer** processes images by extracting GPS coordinates from EXIF metadata and running ML classification to detect and classify flowers by growth stage. The **data layer** uses MongoDB Atlas, a cloud-hosted NoSQL database that stores all classifications and images (as base64) persistently. The entire application is deployed on Render.com as a containerized service, making it scalable and accessible from anywhere. Images flow through the system: uploaded via API, processed for GPS and classification, then stored in MongoDB where they can be retrieved later for heatmap visualization or individual queries.

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

### 2. Configure Environment

The `.env` file is already configured with MongoDB credentials. If you need to update it, edit `.env`:

```bash
# .env file
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/flower_classifications
MONGODB_DATABASE=flower_classifications
PORT=8000
```

**Note:** The `.env` file is in `.gitignore` and won't be committed to git.

### 3. Run Tests

```bash
# Run all integration tests (recommended)
python test_integration.py

# Run specific tests
python test_integration.py --test model      # Test YOLO model only
python test_integration.py --test database   # Test MongoDB only
python test_integration.py --test e2e        # Test end-to-end flow
python test_integration.py --test api        # Test API endpoints (requires running server)

# Run original pytest suite
pytest tests/test_api.py -v

# Test live deployed API
curl https://capstone-077z.onrender.com/
```

### 4. Start the Server

```bash
# The .env file is automatically loaded
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

**Note:** MongoDB URL is loaded from `.env` file.

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

### Quick Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    External Clients                          │
│  (Frontend, API Clients, Browser)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Render.com (FastAPI Application)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Routes:                                         │   │
│  │  - POST /api/classify                                │   │
│  │  - GET /api/heatmap-data                             │   │
│  │  - GET /api/classifications/{id}                     │   │
│  │  - GET /api/images/{id}                              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Services:                                           │   │
│  │  - ML Model (Classification)                         │   │
│  │  - Image Processing (EXIF GPS)                       │   │
│  │  - MongoDB Client (Motor)                            │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ MongoDB Connection
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              MongoDB Atlas (Cloud Database)                  │
│  - Stores classifications                                    │
│  - Stores images as base64                                   │
│  - Persistent storage                                        │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
capstone/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application and routes
│   ├── database_mongodb.py  # MongoDB database setup
│   ├── config.py            # Environment variable configuration
│   ├── models.py            # Pydantic request/response models
│   ├── ml_model.py          # YOLO model integration
│   └── utils.py             # EXIF GPS extraction utilities
├── tests/
│   ├── __init__.py
│   └── test_api.py          # Pytest test suite
├── ml_model.pt              # YOLOv8 trained model
├── requirements.txt
├── Dockerfile               # Docker configuration for Render
├── run_test.py              # Standalone test script
├── test_ml_model.py         # ML model unit tests
├── test_yolo_integration.py # Quick YOLO integration test
└── README.md
```

## ML Model Integration

The `app/ml_model.py` file implements **YOLOv8 from Ultralytics** for flower detection and classification. The model is **automatically downloaded from Hugging Face Hub** to ensure you always have the latest version.

### Model Interface

```python
def classify_image(image_bytes: bytes, confidence_threshold: float = 0.25) -> List[Dict]:
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

### Features
- **Hugging Face Integration**: Automatically downloads latest model from `deenp03/tomato_pollination_stage_classifier`
- **Model Caching**: Model is loaded once and cached for subsequent requests
- **Automatic Updates**: Always uses the latest model version from Hugging Face
- **Fallback Support**: Falls back to local model if Hugging Face is unavailable
- **Confidence Threshold**: Adjustable threshold for filtering detections (default: 0.25)
- **Automatic RGB Conversion**: Handles various image formats (RGBA, grayscale, etc.)
- **GPU Support**: Automatically uses GPU if available, falls back to CPU

### Testing the Model

Run the integration test to verify the model downloads and works:
```bash
# Test all components including Hugging Face download
python test_integration.py

# Or test just the model
python test_integration.py --test model
```

The first run will download the model from Hugging Face (~50MB, takes 5-10 seconds).
Subsequent runs use the cached model and are much faster.

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
   - Deploy!
   - Everytime your GitHub repo is updated, Render will redeploy

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

