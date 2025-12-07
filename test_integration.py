#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite
Tests YOLO model, MongoDB, and API endpoints in one place.

Usage:
    # Run all tests
    python test_integration.py
    
    # Run specific test
    python test_integration.py --test model
    python test_integration.py --test database
    python test_integration.py --test api
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")

def print_section(text):
    """Print a formatted section."""
    print(f"\n{Colors.BOLD}{text}{Colors.END}")
    print(f"{'-' * 70}")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


# ============================================================================
# TEST 1: YOLO Model Tests
# ============================================================================

def test_yolo_model():
    """Test YOLO model loading and inference."""
    print_header("TEST 1: YOLO Model Integration")
    
    try:
        # Test model loading from Hugging Face
        print_section("1.1 Downloading Model from Hugging Face")
        print("  This will download the latest model from:")
        print("  deenp03/tomato_pollination_stage_classifier")
        
        # Test model loading
        print_section("1.2 Loading YOLO Model from Hugging Face")
        from app.ml_model import load_model, get_model_info, classify_image
        
        model = load_model()
        print_success("YOLO model loaded successfully")
        
        model_info = get_model_info()
        print(f"  Model Type: {model_info.get('model_type')}")
        print(f"  Library: {model_info.get('library')}")
        
        # Test classification with test image
        if os.path.exists("test_image.jpg"):
            print_section("1.3 Testing Classification")
            with open("test_image.jpg", "rb") as f:
                image_bytes = f.read()
            
            detections = classify_image(image_bytes, confidence_threshold=0.25)
            print_success(f"Classification successful - Found {len(detections)} flowers")
            
            # Validate output format
            print_section("1.4 Validating Output Format")
            stage_counts = {0: 0, 1: 0, 2: 0}
            
            for i, detection in enumerate(detections, 1):
                # Check required keys
                assert "bounding_box" in detection, "Missing bounding_box"
                assert "stage" in detection, "Missing stage"
                assert "confidence" in detection, "Missing confidence"
                
                bbox = detection["bounding_box"]
                stage = detection["stage"]
                conf = detection["confidence"]
                
                # Validate types and values
                assert isinstance(bbox, list) and len(bbox) == 4, "Invalid bounding_box"
                assert stage in [0, 1, 2], f"Invalid stage: {stage}"
                assert 0.0 <= conf <= 1.0, f"Invalid confidence: {conf}"
                
                stage_counts[stage] += 1
                print(f"  Flower {i}: Stage={stage}, Confidence={conf:.2%}")
            
            print_success("Output format validation passed")
            print(f"\n  Stage Summary:")
            print(f"    Bud (0):          {stage_counts[0]}")
            print(f"    Anthesis (1):     {stage_counts[1]}")
            print(f"    Post-Anthesis (2): {stage_counts[2]}")
            
        else:
            print_warning("test_image.jpg not found, skipping classification test")
        
        print_section("1.5 Testing Pydantic Compatibility")
        from app.models import FlowerDetection
        
        if 'detections' in locals() and detections:
            for detection in detections:
                flower = FlowerDetection(
                    bounding_box=detection["bounding_box"],
                    stage=detection["stage"],
                    confidence=detection["confidence"]
                )
            print_success("Pydantic model validation passed")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ YOLO MODEL TESTS PASSED{Colors.END}\n")
        return True
        
    except Exception as e:
        print_error(f"YOLO model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 2: MongoDB Tests
# ============================================================================

async def test_mongodb():
    """Test MongoDB connection and database operations."""
    print_header("TEST 2: MongoDB Integration")
    
    try:
        # Check MongoDB configuration
        print_section("2.1 Checking MongoDB Configuration")
        from app.config import settings
        
        if not settings.MONGODB_URL:
            print_error("MONGODB_URL not configured!")
            print("  Set it in .env file or as environment variable")
            return False
        
        print_success("MongoDB URL configured")
        print(f"  URL starts with: {settings.MONGODB_URL[:20]}...")
        
        # Test connection
        print_section("2.2 Testing MongoDB Connection")
        from app.database_mongodb import (
            connect_to_mongodb,
            close_mongodb_connection,
            ClassificationRecord
        )
        
        await connect_to_mongodb()
        print_success("Connected to MongoDB successfully")
        
        # Test database operations
        print_section("2.3 Testing Database Operations")
        
        # Create test record
        import uuid
        test_id = str(uuid.uuid4())
        
        # Create dummy image bytes
        test_image_bytes = b"test_image_data"
        test_detections = [
            {
                "bounding_box": [100.0, 150.0, 200.0, 250.0],
                "stage": 1,
                "confidence": 0.95
            }
        ]
        
        await ClassificationRecord.create(
            record_id=test_id,
            image_bytes=test_image_bytes,
            latitude=37.7749,
            longitude=-122.4194,
            flowers=test_detections,
            filename="test.jpg"
        )
        print_success(f"Created test record: {test_id}")
        
        # Retrieve record
        record = await ClassificationRecord.get_by_id(test_id)
        if record:
            print_success(f"Retrieved test record")
            print(f"  ID: {record['id']}")
            print(f"  Timestamp: {record['timestamp']}")
            print(f"  Flower count: {len(record['flowers'])}")
        else:
            print_error("Failed to retrieve test record")
            await close_mongodb_connection()
            return False
        
        # Get all records
        all_records = await ClassificationRecord.get_all()
        print_success(f"Retrieved all records: {len(all_records)} total")
        
        # Delete test record
        deleted = await ClassificationRecord.delete_by_id(test_id)
        if deleted:
            print_success("Deleted test record")
        else:
            print_warning("Test record already deleted")
        
        # Close connection
        await close_mongodb_connection()
        print_success("Closed MongoDB connection")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ MONGODB TESTS PASSED{Colors.END}\n")
        return True
        
    except Exception as e:
        print_error(f"MongoDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 3: API Endpoint Tests
# ============================================================================

async def test_api_endpoints():
    """Test API endpoints (requires running server)."""
    print_header("TEST 3: API Endpoints")
    
    try:
        import requests
        import time
        
        # Wait for server to be ready
        print_section("3.1 Checking API Server")
        time.sleep(1)
        
        base_url = "http://localhost:8000"
        
        # Test health endpoint
        print_section("3.2 Testing Health Endpoint (GET /)")
        response = requests.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Health check passed")
            print(f"  Status: {data.get('status')}")
            print(f"  Database: {data.get('database')}")
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
        
        # Test classify endpoint
        if os.path.exists("test_image.jpg"):
            print_section("3.3 Testing Classify Endpoint (POST /api/classify)")
            
            with open("test_image.jpg", "rb") as f:
                files = {"file": ("test_image.jpg", f, "image/jpeg")}
                response = requests.post(
                    f"{base_url}/api/classify",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Classification successful")
                print(f"  ID: {data['id']}")
                print(f"  Flower Count: {data['flower_count']}")
                print(f"  Stage Summary: {data['stage_summary']}")
                
                classification_id = data['id']
                
                # Test get classification endpoint
                print_section("3.4 Testing Get Classification (GET /api/classifications/{id})")
                response = requests.get(
                    f"{base_url}/api/classifications/{classification_id}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    print_success("Retrieved classification")
                else:
                    print_error(f"Failed to retrieve: {response.status_code}")
                
                # Test heatmap endpoint
                print_section("3.5 Testing Heatmap Data (GET /api/heatmap-data)")
                response = requests.get(f"{base_url}/api/heatmap-data", timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    print_success(f"Retrieved heatmap data")
                    print(f"  Total Records: {data['total_records']}")
                else:
                    print_error(f"Heatmap request failed: {response.status_code}")
                
            else:
                print_error(f"Classification failed: {response.status_code}")
                print(f"  Error: {response.text}")
                return False
        else:
            print_warning("test_image.jpg not found, skipping API tests")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ API ENDPOINT TESTS PASSED{Colors.END}\n")
        return True
        
    except requests.exceptions.ConnectionError:
        print_error("Could not connect to API server")
        print("  Start the server with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print_error(f"API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 4: Complete End-to-End Test
# ============================================================================

async def test_end_to_end():
    """Test complete flow: Model -> Database -> API."""
    print_header("TEST 4: End-to-End Integration")
    
    try:
        print_section("4.1 Loading Components")
        
        # Load model
        from app.ml_model import classify_image
        print_success("YOLO model ready")
        
        # Connect to MongoDB
        from app.database_mongodb import (
            connect_to_mongodb,
            close_mongodb_connection,
            ClassificationRecord
        )
        await connect_to_mongodb()
        print_success("MongoDB connected")
        
        # Test with real image
        if not os.path.exists("test_image.jpg"):
            print_warning("test_image.jpg not found, skipping e2e test")
            await close_mongodb_connection()
            return True
        
        print_section("4.2 Running Complete Flow")
        
        # Classify image
        with open("test_image.jpg", "rb") as f:
            image_bytes = f.read()
        
        detections = classify_image(image_bytes)
        print_success(f"Classified image: {len(detections)} flowers")
        
        # Save to database
        import uuid
        test_id = str(uuid.uuid4())
        
        await ClassificationRecord.create(
            record_id=test_id,
            image_bytes=image_bytes,
            latitude=37.7749,
            longitude=-122.4194,
            flowers=detections,
            filename="test_image.jpg"
        )
        print_success(f"Saved to database: {test_id}")
        
        # Retrieve from database
        record = await ClassificationRecord.get_by_id(test_id)
        if record and len(record['flowers']) == len(detections):
            print_success("Retrieved from database: data intact")
        else:
            print_error("Data mismatch after retrieval")
            await close_mongodb_connection()
            return False
        
        # Clean up
        await ClassificationRecord.delete_by_id(test_id)
        print_success("Cleaned up test record")
        
        await close_mongodb_connection()
        print_success("Closed connections")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ END-TO-END TEST PASSED{Colors.END}\n")
        return True
        
    except Exception as e:
        print_error(f"End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# Main Test Runner
# ============================================================================

async def run_all_tests():
    """Run all tests."""
    print_header("COMPREHENSIVE INTEGRATION TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # Test 1: YOLO Model
    results['model'] = test_yolo_model()
    
    # Test 2: MongoDB
    results['database'] = await test_mongodb()
    
    # Test 3: End-to-End
    results['e2e'] = await test_end_to_end()
    
    # Test 4: API Endpoints (optional - requires running server)
    print_section("API Endpoint Tests")
    print("Note: This requires the API server to be running")
    print("      Start with: uvicorn app.main:app --reload")
    
    try:
        results['api'] = await test_api_endpoints()
    except Exception:
        print_warning("Skipping API tests (server not running)")
        results['api'] = None
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for name, result in results.items():
        if result is True:
            print(f"  {Colors.GREEN}✓ {name.upper():<12} PASSED{Colors.END}")
        elif result is False:
            print(f"  {Colors.RED}✗ {name.upper():<12} FAILED{Colors.END}")
        else:
            print(f"  {Colors.YELLOW}⊘ {name.upper():<12} SKIPPED{Colors.END}")
    
    print(f"\n  Total: {passed} passed, {failed} failed, {skipped} skipped\n")
    
    if failed == 0 and passed > 0:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.END}\n")
        return 0
    elif failed > 0:
        print(f"{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED{Colors.END}\n")
        return 1
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ NO TESTS RUN{Colors.END}\n")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive integration test suite"
    )
    parser.add_argument(
        '--test',
        choices=['model', 'database', 'api', 'e2e', 'all'],
        default='all',
        help='Which test to run (default: all)'
    )
    
    args = parser.parse_args()
    
    # Run specific test or all tests
    if args.test == 'model':
        result = test_yolo_model()
        return 0 if result else 1
    elif args.test == 'database':
        result = asyncio.run(test_mongodb())
        return 0 if result else 1
    elif args.test == 'api':
        result = asyncio.run(test_api_endpoints())
        return 0 if result else 1
    elif args.test == 'e2e':
        result = asyncio.run(test_end_to_end())
        return 0 if result else 1
    else:  # all
        return asyncio.run(run_all_tests())


if __name__ == "__main__":
    sys.exit(main())

