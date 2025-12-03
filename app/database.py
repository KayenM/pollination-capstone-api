"""
Database setup and models for storing classification results.
Uses SQLite with SQLAlchemy for simplicity.
"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "sqlite:///./flower_classifications.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ClassificationRecord(Base):
    """
    Database model for storing image classification results.
    """
    __tablename__ = "classifications"

    id = Column(String, primary_key=True, index=True)
    image_path = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    results_json = Column(Text, nullable=False)  # JSON string of flower detections

    @property
    def flowers(self) -> list:
        """Parse the JSON results into a list of flower detections."""
        return json.loads(self.results_json)

    @flowers.setter
    def flowers(self, value: list):
        """Serialize flower detections to JSON."""
        self.results_json = json.dumps(value)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

