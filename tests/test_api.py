"""
Tests for the Tomato Plant Flower Classification API.

Run with: pytest tests/test_api.py -v
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Test image path
TEST_IMAGE_PATH = "IMG_1905.jpeg"


@pytest.fixture(scope="module")
def client():
    """Create a test client with MongoDB."""
    # Check for MongoDB connection
    mongodb_url = os.environ.get("MONGODB_URL")
    if not mongodb_url:
        pytest.skip("MONGODB_URL environment variable not set. Set it to run tests.")
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_image():
    """Load the test image."""
    if not os.path.exists(TEST_IMAGE_PATH):
        pytest.skip(f"Test image not found: {TEST_IMAGE_PATH}")
    
    with open(TEST_IMAGE_PATH, "rb") as f:
        return f.read()


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test that the health check endpoint returns healthy status."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "timestamp" in data
        print(f"\n✓ Health check passed: {data}")


class TestClassifyEndpoint:
    """Tests for the /api/classify endpoint."""

    def test_classify_image_success(self, client, test_image):
        """Test successful image classification."""
        response = client.post(
            "/api/classify",
            files={"file": ("test_image.jpeg", test_image, "image/jpeg")},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "image_path" in data
        assert "location" in data
        assert "timestamp" in data
        assert "flowers" in data
        assert "flower_count" in data
        assert "stage_summary" in data
        
        # Verify flowers have correct structure
        assert len(data["flowers"]) > 0
        for flower in data["flowers"]:
            assert "bounding_box" in flower
            assert len(flower["bounding_box"]) == 4
            assert "stage" in flower
            assert flower["stage"] in [0, 1, 2]
            assert "confidence" in flower
            assert 0 <= flower["confidence"] <= 1
        
        print(f"\n✓ Classification successful:")
        print(f"  - ID: {data['id']}")
        print(f"  - Location: {data['location']}")
        print(f"  - Flower count: {data['flower_count']}")
        print(f"  - Stage summary: {data['stage_summary']}")
        print(f"  - Sample flower: {data['flowers'][0]}")
        
        return data["id"]

    def test_classify_with_manual_coordinates(self, client, test_image):
        """Test classification with manually provided GPS coordinates."""
        response = client.post(
            "/api/classify",
            files={"file": ("test_image.jpeg", test_image, "image/jpeg")},
            data={"latitude": 37.7749, "longitude": -122.4194},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["location"]["latitude"] == 37.7749
        assert data["location"]["longitude"] == -122.4194
        
        print(f"\n✓ Manual coordinates applied: {data['location']}")

    def test_classify_invalid_file_type(self, client):
        """Test that non-image files are rejected."""
        response = client.post(
            "/api/classify",
            files={"file": ("test.txt", b"not an image", "text/plain")},
        )
        
        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()
        print("\n✓ Invalid file type correctly rejected")


class TestHeatmapEndpoint:
    """Tests for the /api/heatmap-data endpoint."""

    def test_heatmap_data_empty(self, client):
        """Test heatmap endpoint with no data."""
        response = client.get("/api/heatmap-data")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_records" in data
        assert "data_points" in data
        print(f"\n✓ Heatmap endpoint working, records: {data['total_records']}")

    def test_heatmap_data_with_classifications(self, client, test_image):
        """Test heatmap endpoint after adding classifications."""
        # First, add some classifications
        for i in range(3):
            client.post(
                "/api/classify",
                files={"file": (f"test_{i}.jpeg", test_image, "image/jpeg")},
                data={"latitude": 37.7749 + i * 0.01, "longitude": -122.4194 + i * 0.01},
            )
        
        # Get heatmap data
        response = client.get("/api/heatmap-data")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_records"] >= 3
        
        # Verify data point structure
        for point in data["data_points"]:
            assert "id" in point
            assert "latitude" in point
            assert "longitude" in point
            assert "timestamp" in point
            assert "flowers" in point
            assert "total_flowers" in point
            assert "stage_counts" in point
        
        print(f"\n✓ Heatmap data retrieved:")
        print(f"  - Total records: {data['total_records']}")
        for point in data["data_points"][:3]:
            print(f"  - Point: lat={point['latitude']}, lon={point['longitude']}, flowers={point['total_flowers']}")


class TestGetClassification:
    """Tests for the /api/classifications/{id} endpoint."""

    def test_get_classification_success(self, client, test_image):
        """Test retrieving a specific classification."""
        # First, create a classification
        create_response = client.post(
            "/api/classify",
            files={"file": ("test.jpeg", test_image, "image/jpeg")},
        )
        record_id = create_response.json()["id"]
        
        # Get the classification
        response = client.get(f"/api/classifications/{record_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == record_id
        print(f"\n✓ Retrieved classification {record_id}")

    def test_get_classification_not_found(self, client):
        """Test 404 for non-existent classification."""
        response = client.get("/api/classifications/non-existent-id")
        assert response.status_code == 404
        print("\n✓ 404 returned for non-existent classification")


class TestDeleteClassification:
    """Tests for the DELETE /api/classifications/{id} endpoint."""

    def test_delete_classification(self, client, test_image):
        """Test deleting a classification."""
        # First, create a classification
        create_response = client.post(
            "/api/classify",
            files={"file": ("test.jpeg", test_image, "image/jpeg")},
        )
        record_id = create_response.json()["id"]
        image_path = create_response.json()["image_path"]
        
        # Delete it
        response = client.delete(f"/api/classifications/{record_id}")
        assert response.status_code == 200
        
        # Verify it's gone
        get_response = client.get(f"/api/classifications/{record_id}")
        assert get_response.status_code == 404
        
        # Note: Images are stored in MongoDB, not filesystem
        print(f"\n✓ Classification {record_id} deleted successfully")


class TestImageEndpoint:
    """Tests for the /api/images/{id} endpoint."""

    def test_get_image(self, client, test_image):
        """Test retrieving an image file."""
        # First, create a classification
        create_response = client.post(
            "/api/classify",
            files={"file": ("test.jpeg", test_image, "image/jpeg")},
        )
        record_id = create_response.json()["id"]
        
        # Get the image
        response = client.get(f"/api/images/{record_id}")
        assert response.status_code == 200
        assert "image" in response.headers.get("content-type", "")
        
        print(f"\n✓ Image retrieved for classification {record_id}")


def run_all_tests():
    """Run all tests and print summary."""
    print("=" * 60)
    print("TOMATO PLANT FLOWER CLASSIFICATION API - TEST SUITE")
    print("=" * 60)
    
    # Run pytest programmatically
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("ALL TESTS PASSED ✓")
    else:
        print(f"SOME TESTS FAILED (exit code: {exit_code})")
    print("=" * 60)
    
    return exit_code


if __name__ == "__main__":
    run_all_tests()

