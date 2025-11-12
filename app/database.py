"""
Database setup and session management.

This module handles:
- Creating the database and tables
- Managing database connections (sessions)
- Providing FastAPI dependency for database access

Key concepts:
- Session: A connection to the database that tracks changes
- Dependency injection: FastAPI automatically provides database sessions to routes
- Context manager: Ensures sessions are properly closed after use
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings
from app.models import Base

# Create database engine
# This is the connection pool to the database
# SQLite creates a file if it doesn't exist
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}  # SQLite-specific: allow multiple threads
)

# Create session factory
# Sessions are used to interact with the database
# Each request gets its own session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize the database by creating all tables.
    
    This should be called once when the application starts.
    It creates the database file and all tables defined in models.py.
    
    If tables already exist, this is safe to call (won't recreate them).
    """
    # Create all tables defined in Base's subclasses (Run, Prompt, Response)
    Base.metadata.create_all(bind=engine)
    print("Database initialized: tables created")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    
    This is a generator function that:
    1. Creates a new database session
    2. Yields it to the route function
    3. Closes the session after the route completes (even if there's an error)
    
    Usage in FastAPI routes:
        @app.get("/runs")
        def get_runs(db: Session = Depends(get_db)):
            # db is a database session
            runs = db.query(Run).all()
            return runs
    
    The 'yield' keyword makes this a generator, which FastAPI uses for cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Always close the session, even if an error occurs

