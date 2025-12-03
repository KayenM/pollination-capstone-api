#!/usr/bin/env python3
"""
Test MongoDB connection and API functionality.
"""

import os
import asyncio
import sys

# Set MongoDB connection string
os.environ["MONGODB_URL"] = "mongodb+srv://flower-api-user:n1a32gnRzcEvhnbZ@freetier.nnomdg6.mongodb.net/flower_classifications?appName=FreeTier"

async def test_mongodb_connection():
    """Test MongoDB connection."""
    print("Testing MongoDB connection...")
    
    try:
        from app.database_mongodb import connect_to_mongodb, create_indexes, get_database
        
        # Connect to MongoDB
        await connect_to_mongodb()
        print("✓ Connected to MongoDB")
        
        # Create indexes
        await create_indexes()
        print("✓ Created indexes")
        
        # Test database operations
        from app.database_mongodb import ClassificationRecord
        db = get_database()
        count = await ClassificationRecord.count()
        print(f"✓ Database accessible - Current records: {count}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_import():
    """Test if API can be imported."""
    print("\nTesting API import...")
    
    try:
        from app.main import app
        print("✓ API app imported successfully")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("MongoDB Connection Test")
    print("=" * 60)
    
    # Run async tests
    connection_ok = asyncio.run(test_mongodb_connection())
    api_ok = test_api_import()
    
    print("\n" + "=" * 60)
    if connection_ok and api_ok:
        print("✓ All tests passed!")
        print("\nYou can now start the API with:")
        print("  MONGODB_URL='mongodb+srv://...' uvicorn app.main:app --reload")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

