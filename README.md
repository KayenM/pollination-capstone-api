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
# Quick standalone test
python run_test.py

# Full pytest suite
pytest tests/test_api.py -v
```

### 3. Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

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
  "image_path": "uploads/images/uuid.jpg",
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

When the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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
├── run_test.py              # Standalone test script
├── MONGODB_SETUP.md         # MongoDB Atlas setup guide
├── ARCHITECTURE.md          # Full system architecture guide
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

### Setting Up MongoDB

1. **Create a free MongoDB Atlas account** at https://www.mongodb.com/cloud/atlas/register
2. **Create a free cluster** (M0 tier, 512MB storage)
3. **Get your connection string** from the Atlas dashboard
4. **Set environment variable:**
   ```bash
   export MONGODB_URL="mongodb+srv://username:password@cluster.mongodb.net/flower_classifications"
   ```

See **[MONGODB_SETUP.md](MONGODB_SETUP.md)** for detailed setup instructions.

### Local Development

For local testing without MongoDB, the API will show a warning but still start. You'll need MongoDB configured for full functionality.

## Deployment

This API is ready for cloud deployment with MongoDB Atlas!

### Quick Deploy Steps:

1. **Set up MongoDB Atlas** (see [MONGODB_SETUP.md](MONGODB_SETUP.md))
2. **Deploy to Render.com:**
   - Push code to GitHub
   - Create new Web Service on Render
   - Set `MONGODB_URL` environment variable
   - Deploy!

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for full system architecture including frontend (Vercel) + backend (Render) + MongoDB.

## Environment Variables

```bash
# Required for MongoDB
MONGODB_URL=mongodb+srv://...  # Your MongoDB Atlas connection string
MONGODB_DATABASE=flower_classifications  # Optional, defaults to this

# Optional
PORT=8000  # Server port (auto-set by hosting platform)
CORS_ORIGINS=*  # Allowed frontend origins (comma-separated)
```

