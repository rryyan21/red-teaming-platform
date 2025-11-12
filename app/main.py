"""
FastAPI application entry point.

This is the main web server that handles HTTP requests and serves the dashboard.
FastAPI automatically generates API documentation at /docs when running.

Key concepts:
- FastAPI: Modern Python web framework (like Flask but with automatic API docs)
- Routes: Functions that handle specific URLs (GET /health, POST /runs, etc.)
- Dependencies: Things like database sessions that get injected into route functions
- Pydantic models: Request/response validation
- Template rendering: Server-side HTML generation with Jinja2
"""

import logging
import csv
import io
from typing import List
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.models import Run, Prompt, Response as ResponseModel
from app.runner import run_evaluation

# Set up logging
# This configures Python's logging system to output formatted messages
# Format: timestamp - module name - log level - message
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Create FastAPI app instance
# This is the main application object
app = FastAPI(
    title="Red Teaming Platform",
    description="A tool for testing LLM safety with adversarial prompts",
    version="0.1.0"
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database when application starts."""
    init_db()
    logger.info("Application started, database initialized")

# Set up Jinja2 templates
# Templates are HTML files with placeholders that get filled with data
jinja_env = Environment(loader=FileSystemLoader("app/templates"))

def render_template(template_name: str, context: dict, request: Request):
    """Helper function to render Jinja2 templates."""
    template = jinja_env.get_template(template_name)
    return HTMLResponse(content=template.render(**context))

# Pydantic models for request/response validation
# These ensure incoming data matches expected format
class RunRequest(BaseModel):
    """Request body for starting a new evaluation run."""
    model_name: str
    attack_set: str = "default"


class RunSummary(BaseModel):
    """Summary of an evaluation run."""
    id: int
    created_at: datetime
    model_name: str
    attack_set_name: str
    total_prompts: int
    unsafe_count: int
    score: float


@app.get("/health")
def health():
    """
    Health check endpoint.
    
    This is a simple endpoint to verify the server is running.
    Useful for monitoring and deployment checks.
    
    Returns:
        dict: Status confirmation
    """
    logger.info("Health check requested")
    return {"status": "ok", "message": "Red Teaming Platform is running"}


@app.post("/runs", response_model=dict)
def create_run(run_request: RunRequest, db: Session = Depends(get_db)):
    """
    Start a new evaluation run.
    
    This endpoint:
    1. Validates the request (model_name, attack_set)
    2. Calls the runner to execute the evaluation
    3. Returns the run_id immediately
    
    Note: For MVP, this runs synchronously (blocks until complete).
    For 20 prompts, this might take 30-60 seconds.
    
    Args:
        run_request: Request body with model_name and attack_set
        db: Database session (injected by FastAPI)
    
    Returns:
        dict: Contains run_id
    
    Example request:
        POST /runs
        {
            "model_name": "gpt-3.5-turbo",
            "attack_set": "default"
        }
    """
    logger.info(f"Starting new run: model={run_request.model_name}, attack_set={run_request.attack_set}")
    
    try:
        run_id = run_evaluation(
            db=db,
            model_name=run_request.model_name,
            attack_set_name=run_request.attack_set
        )
        return {"run_id": run_id, "status": "completed"}
    except Exception as e:
        logger.error(f"Error creating run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create run: {str(e)}")


@app.get("/runs", response_model=List[RunSummary])
def list_runs(db: Session = Depends(get_db)):
    """
    List all evaluation runs with summary metrics.
    
    Returns a list of all runs sorted by creation date (newest first).
    Each run includes summary statistics.
    
    Args:
        db: Database session
    
    Returns:
        List of RunSummary objects
    """
    runs = db.query(Run).order_by(Run.created_at.desc()).all()
    return runs


@app.get("/runs/{run_id}", response_class=HTMLResponse)
def get_run_detail(run_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Get detailed results for a specific run.
    
    This renders an HTML page showing:
    - Run summary (model, date, statistics)
    - Table of all prompts and responses
    - Safety scores and categories
    
    Args:
        run_id: ID of the run to view
        request: FastAPI request object (needed for template rendering)
        db: Database session
    
    Returns:
        HTML page with run details
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Get all prompts and responses for this run
    prompts = db.query(Prompt).filter(Prompt.run_id == run_id).all()
    
    # Attach responses to prompts
    for prompt in prompts:
        response = db.query(ResponseModel).filter(ResponseModel.prompt_id == prompt.id).first()
        prompt.response_obj = response
    
    return render_template(
        "run_detail.html",
        {
            "run": run,
            "prompts": prompts
        },
        request
    )


@app.get("/runs/{run_id}/status", response_model=dict)
def get_run_status(run_id: int, db: Session = Depends(get_db)):
    """
    Get progress status for a run.
    
    For MVP, runs complete synchronously, so this just returns completion status.
    In future versions, this could show real-time progress.
    
    Args:
        run_id: ID of the run
        db: Database session
    
    Returns:
        dict: Status information
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Calculate progress (for MVP, if run exists, it's complete)
    progress = 100.0 if run.total_prompts > 0 else 0.0
    
    return {
        "run_id": run_id,
        "status": "completed" if run.total_prompts > 0 else "pending",
        "progress": progress,
        "total_prompts": run.total_prompts,
        "completed": run.total_prompts
    }


@app.get("/runs/{run_id}/export")
def export_run(
    run_id: int,
    format: str = Query("csv", regex="^(csv|json)$"),
    db: Session = Depends(get_db)
):
    """
    Export run data as CSV or JSON.
    
    Useful for:
    - Sharing results
    - Further analysis in Excel/Python
    - Archiving test results
    
    Args:
        run_id: ID of the run to export
        format: Export format ("csv" or "json")
        db: Database session
    
    Returns:
        CSV or JSON file download
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    prompts = db.query(Prompt).filter(Prompt.run_id == run_id).all()
    
    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow([
            "Attack ID", "Attack Type", "Prompt", "Model Output",
            "Is Unsafe", "Confidence Score", "Refused", "Categories"
        ])
        
        # Data rows
        for prompt in prompts:
            response = db.query(ResponseModel).filter(ResponseModel.prompt_id == prompt.id).first()
            if response:
                categories_str = ", ".join(response.categories) if response.categories else ""
                writer.writerow([
                    prompt.attack_id,
                    prompt.attack_type,
                    prompt.prompt_text,
                    response.model_output,
                    response.is_unsafe,
                    response.confidence_score,
                    response.refused,
                    categories_str
                ])
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=run_{run_id}.csv"}
        )
    
    else:  # JSON
        # Generate JSON
        data = {
            "run_id": run_id,
            "model_name": run.model_name,
            "created_at": run.created_at.isoformat(),
            "total_prompts": run.total_prompts,
            "unsafe_count": run.unsafe_count,
            "score": run.score,
            "results": []
        }
        
        for prompt in prompts:
            response = db.query(ResponseModel).filter(ResponseModel.prompt_id == prompt.id).first()
            if response:
                data["results"].append({
                    "attack_id": prompt.attack_id,
                    "attack_type": prompt.attack_type,
                    "prompt": prompt.prompt_text,
                    "output": response.model_output,
                    "is_unsafe": response.is_unsafe,
                    "confidence_score": response.confidence_score,
                    "refused": response.refused,
                    "categories": response.categories,
                    "details": response.details
                })
        
        return JSONResponse(content=data)


@app.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    """
    Root endpoint - shows list of all runs (dashboard home).
    
    This is the main landing page that displays all evaluation runs
    in a table format.
    
    Args:
        request: FastAPI request object
        db: Database session
    
    Returns:
        HTML page with runs list
    """
    runs = db.query(Run).order_by(Run.created_at.desc()).all()
    return render_template(
        "runs_list.html",
        {
            "runs": runs
        },
        request
    )

