#!/usr/bin/env python3
"""
Simple standalone test script for the Tomato Plant Flower Classification API.

This script tests the API endpoints without pytest for quick verification.
Run with: python run_test.py
"""

import os
import sys
import json

# Ensure we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import create_tables

# Test image path
TEST_IMAGE_PATH = "IMG_1905.jpeg"


def print_header(text):
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}")


def print_success(text):
    print(f"  ✓ {text}")


def print_error(text):
    print(f"  ✗ {text}")


def print_json(data, indent=4):
    print(json.dumps(data, indent=indent, default=str))


def main():
    print_header("TOMATO PLANT FLOWER CLASSIFICATION API - TEST")
    
    # Check if test image exists
    if not os.path.exists(TEST_IMAGE_PATH):
        print_error(f"Test image not found: {TEST_IMAGE_PATH}")
        return 1
    
    print_success(f"Found test image: {TEST_IMAGE_PATH}")
    
    # Create test client
    create_tables()
    client = TestClient(app)
    
    # Test 1: Health Check
    print_header("TEST 1: Health Check")
    response = client.get("/")
    if response.status_code == 200:
        print_success("Health check passed")
        print_json(response.json())
    else:
        print_error(f"Health check failed: {response.status_code}")
        return 1
    
    # Test 2: Classify Image
    print_header("TEST 2: Classify Image (with EXIF GPS extraction)")
    with open(TEST_IMAGE_PATH, "rb") as f:
        image_data = f.read()
    
    response = client.post(
        "/api/classify",
        files={"file": ("test_image.jpeg", image_data, "image/jpeg")},
    )
    
    if response.status_code == 200:
        result = response.json()
        print_success("Image classification successful")
        print(f"\n  Classification Result:")
        print(f"  - ID: {result['id']}")
        print(f"  - Image Path: {result['image_path']}")
        print(f"  - Location: lat={result['location']['latitude']}, lon={result['location']['longitude']}")
        print(f"  - Timestamp: {result['timestamp']}")
        print(f"  - Flower Count: {result['flower_count']}")
        print(f"  - Stage Summary: {result['stage_summary']}")
        print(f"\n  Detected Flowers:")
        for i, flower in enumerate(result['flowers']):
            stage_names = {0: "Bud", 1: "Anthesis", 2: "Post-Anthesis"}
            print(f"    {i+1}. Stage: {stage_names[flower['stage']]} ({flower['stage']})")
            print(f"       Bounding Box: {flower['bounding_box']}")
            print(f"       Confidence: {flower['confidence']:.2%}")
        
        record_id = result['id']
    else:
        print_error(f"Classification failed: {response.status_code}")
        print_json(response.json())
        return 1
    
    # Test 3: Classify with manual coordinates
    print_header("TEST 3: Classify Image (with manual GPS coordinates)")
    response = client.post(
        "/api/classify",
        files={"file": ("test_image.jpeg", image_data, "image/jpeg")},
        data={"latitude": 37.7749, "longitude": -122.4194},
    )
    
    if response.status_code == 200:
        result = response.json()
        print_success("Classification with manual coordinates successful")
        print(f"  - Location: lat={result['location']['latitude']}, lon={result['location']['longitude']}")
        print(f"  - Flower Count: {result['flower_count']}")
    else:
        print_error(f"Classification failed: {response.status_code}")
        return 1
    
    # Test 4: Get Heatmap Data
    print_header("TEST 4: Get Heatmap Data")
    response = client.get("/api/heatmap-data")
    
    if response.status_code == 200:
        result = response.json()
        print_success(f"Heatmap data retrieved: {result['total_records']} records")
        print(f"\n  Data Points for Heatmap:")
        for point in result['data_points']:
            print(f"    - ID: {point['id'][:8]}...")
            print(f"      Location: ({point['latitude']}, {point['longitude']})")
            print(f"      Total Flowers: {point['total_flowers']}")
            print(f"      Stage Counts: Bud={point['stage_counts']['0']}, Anthesis={point['stage_counts']['1']}, Post-Anthesis={point['stage_counts']['2']}")
    else:
        print_error(f"Heatmap data retrieval failed: {response.status_code}")
        return 1
    
    # Test 5: Get Specific Classification
    print_header("TEST 5: Get Specific Classification")
    response = client.get(f"/api/classifications/{record_id}")
    
    if response.status_code == 200:
        print_success(f"Retrieved classification {record_id[:8]}...")
    else:
        print_error(f"Failed to retrieve classification: {response.status_code}")
        return 1
    
    # Test 6: Get Image
    print_header("TEST 6: Get Stored Image")
    response = client.get(f"/api/images/{record_id}")
    
    if response.status_code == 200:
        print_success(f"Retrieved image for classification {record_id[:8]}...")
        print(f"  - Content-Type: {response.headers.get('content-type')}")
        print(f"  - Size: {len(response.content)} bytes")
    else:
        print_error(f"Failed to retrieve image: {response.status_code}")
        return 1
    
    # Test 7: Invalid file type rejection
    print_header("TEST 7: Invalid File Type Rejection")
    response = client.post(
        "/api/classify",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    
    if response.status_code == 400:
        print_success("Invalid file type correctly rejected")
    else:
        print_error(f"Should have rejected invalid file: {response.status_code}")
        return 1
    
    # Test 8: 404 for non-existent record
    print_header("TEST 8: 404 for Non-existent Record")
    response = client.get("/api/classifications/fake-id-12345")
    
    if response.status_code == 404:
        print_success("404 returned for non-existent record")
    else:
        print_error(f"Should have returned 404: {response.status_code}")
        return 1
    
    # Summary
    print_header("ALL TESTS PASSED ✓")
    print("\n  API Endpoints Available:")
    print("  - POST /api/classify          - Upload and classify image")
    print("  - GET  /api/heatmap-data      - Get all data for heatmap")
    print("  - GET  /api/classifications/{id} - Get specific classification")
    print("  - GET  /api/images/{id}       - Get stored image")
    print("  - DELETE /api/classifications/{id} - Delete classification")
    print("\n  To start the server:")
    print("  $ uvicorn app.main:app --reload")
    print("\n  API documentation available at:")
    print("  - http://localhost:8000/docs (Swagger UI)")
    print("  - http://localhost:8000/redoc (ReDoc)")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

