"""
Database Models - SQLAlchemy table definitions.

This module defines the database schema using SQLAlchemy ORM (Object-Relational Mapping).
Instead of writing raw SQL, we define Python classes that represent database tables.

Key concepts:
- ORM: Maps Python classes to database tables
- Relationships: Links between tables (one Run has many Prompts)
- Indexes: Speed up queries on frequently searched columns
- JSON columns: Store flexible data structures

Tables:
- Run: Represents one complete evaluation run
- Prompt: Each attack prompt sent to the model
- Response: The model's output and safety score
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Index, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Base class for all models
# All our table classes will inherit from this
Base = declarative_base()


class Run(Base):
    """
    Represents one complete evaluation run.
    
    A run is when we:
    1. Take a model
    2. Run it against a set of attacks
    3. Score all responses
    4. Calculate summary statistics
    
    Attributes:
        id: Primary key (auto-incrementing integer)
        created_at: Timestamp when run was created
        model_name: Which LLM was tested (e.g., "gpt-3.5-turbo")
        attack_set_name: Which attack set was used (e.g., "default")
        total_prompts: Number of prompts tested
        unsafe_count: How many responses were flagged as unsafe
        score: Safety score (unsafe_count / total_prompts, lower is better)
    
    Relationships:
        prompts: List of all Prompt objects in this run
    """
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_name = Column(String, nullable=False)
    attack_set_name = Column(String, nullable=False)
    total_prompts = Column(Integer, default=0)
    unsafe_count = Column(Integer, default=0)
    score = Column(Float, default=0.0)  # Percentage of unsafe responses
    
    # Relationship: one Run has many Prompts
    # This lets us do: run.prompts to get all prompts
    prompts = relationship("Prompt", back_populates="run", cascade="all, delete-orphan")


class Prompt(Base):
    """
    Represents a single attack prompt sent to the model.
    
    Attributes:
        id: Primary key
        run_id: Foreign key linking to Run
        attack_id: ID from the Attack dataclass (e.g., "jailbreak_001")
        attack_type: Category ("jailbreak", "injection", etc.)
        prompt_text: The actual prompt text sent
    
    Relationships:
        run: The Run this prompt belongs to
        response: The Response object (one-to-one relationship)
    
    Indexes:
        idx_run_id: Speeds up queries like "get all prompts for run X"
    """
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    attack_id = Column(String, nullable=False)  # From Attack dataclass
    attack_type = Column(String, nullable=False)
    prompt_text = Column(Text, nullable=False)  # Text can be long
    
    # Relationships
    run = relationship("Run", back_populates="prompts")
    response = relationship("Response", back_populates="prompt", uselist=False, cascade="all, delete-orphan")
    
    # Index for faster queries
    __table_args__ = (
        Index('idx_run_id', 'run_id'),
    )


class Response(Base):
    """
    Represents the model's response and safety evaluation.
    
    Attributes:
        id: Primary key
        prompt_id: Foreign key linking to Prompt
        model_output: The text response from the model
        is_unsafe: Boolean flag (True if unsafe)
        confidence_score: How confident we are (0.0 to 1.0)
        refused: Did the model refuse to answer? (often a good sign)
        categories: JSON list of categories (e.g., ["violence", "illegal"])
        details: JSON object with additional scoring metadata
    
    Relationships:
        prompt: The Prompt this response belongs to
    
    Indexes:
        idx_prompt_id: Speeds up queries linking responses to prompts
    """
    __tablename__ = "responses"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False, unique=True)
    model_output = Column(Text, nullable=False)
    is_unsafe = Column(Boolean, default=False, nullable=False)
    confidence_score = Column(Float, default=0.0)  # 0.0 to 1.0
    refused = Column(Boolean, default=False)  # Model refused to answer
    categories = Column(JSON)  # List of strings like ["violence", "illegal"]
    details = Column(JSON)  # Additional metadata from scoring
    
    # Relationship
    prompt = relationship("Prompt", back_populates="response")
    
    # Index for faster queries
    __table_args__ = (
        Index('idx_prompt_id', 'prompt_id'),
    )

