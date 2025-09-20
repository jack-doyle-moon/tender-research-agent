"""FastAPI server for the research system."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.orchestrator import ResearchWorkflow
from app.store.logger import get_logger

app = FastAPI(
    title="Multi-Agent Research & Validation System",
    description="API for RFP research and tender response generation",
    version="0.1.0"
)

logger = get_logger("api")


class RunRequest(BaseModel):
    """Request model for starting a research run."""
    company_name: str
    max_iterations: Optional[int] = None


class RunResponse(BaseModel):
    """Response model for research run."""
    run_id: str
    status: str
    message: str


class RunStatus(BaseModel):
    """Run status response."""
    run_id: str
    is_complete: bool
    iterations: int
    coverage_score: Optional[float] = None
    errors: List[str] = []


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {"message": "Multi-Agent Research & Validation System API", "version": "0.1.0"}


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/config")
async def get_config() -> Dict[str, any]:
    """Get current configuration."""
    return {
        "openai_model": settings.openai_model,
        "max_iterations": settings.max_iterations,
        "cache_ttl_hours": settings.cache_ttl_hours,
        "pii_redaction": settings.enable_pii_redaction,
        "has_openai_key": bool(settings.openai_api_key),
        "has_serpapi_key": bool(settings.serpapi_api_key),
        "has_tavily_key": bool(settings.tavily_api_key),
    }


@app.post("/runs", response_model=RunResponse)
async def create_run(
    file: UploadFile = File(..., description="RFP document (PDF or DOCX)"),
    company_name: str = Form(..., description="Target company name"),
    max_iterations: Optional[int] = Form(None, description="Maximum refinement iterations")
) -> RunResponse:
    """Start a new research run."""
    
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(400, "Only PDF and DOCX files are supported")
    
    try:
        # Save uploaded file
        temp_dir = settings.data_dir / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info("File uploaded", filename=file.filename, size=len(content))
        
        # Start workflow
        workflow = ResearchWorkflow()
        result = workflow.run(
            rfp_path=str(file_path),
            company_name=company_name,
            max_iterations=max_iterations or settings.max_iterations
        )
        
        # Clean up temp file
        file_path.unlink(missing_ok=True)
        
        return RunResponse(
            run_id=result["run_id"],
            status="completed" if result.get("is_complete") else "failed",
            message="Research workflow completed successfully"
        )
        
    except Exception as e:
        logger.error("Run creation failed", error=str(e))
        raise HTTPException(500, f"Failed to create run: {str(e)}")


@app.get("/runs", response_model=List[RunStatus])
async def list_runs(limit: int = 10) -> List[RunStatus]:
    """List recent runs."""
    runs_dir = settings.data_dir / "runs"
    
    if not runs_dir.exists():
        return []
    
    runs = []
    run_dirs = sorted(runs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
    
    for run_dir in run_dirs[:limit]:
        if run_dir.is_dir():
            summary_file = run_dir / "summary.json"
            if summary_file.exists():
                try:
                    with open(summary_file) as f:
                        summary = json.load(f)
                    
                    runs.append(RunStatus(
                        run_id=run_dir.name,
                        is_complete=summary.get("is_complete", False),
                        iterations=summary.get("iterations", 0),
                        coverage_score=summary.get("coverage_score"),
                        errors=summary.get("errors", [])
                    ))
                except Exception as e:
                    logger.warning("Failed to load run summary", run_id=run_dir.name, error=str(e))
    
    return runs


@app.get("/runs/{run_id}", response_model=RunStatus)
async def get_run(run_id: str) -> RunStatus:
    """Get details for a specific run."""
    run_dir = settings.data_dir / "runs" / run_id
    summary_file = run_dir / "summary.json"
    
    if not summary_file.exists():
        raise HTTPException(404, "Run not found")
    
    try:
        with open(summary_file) as f:
            summary = json.load(f)
        
        return RunStatus(
            run_id=run_id,
            is_complete=summary.get("is_complete", False),
            iterations=summary.get("iterations", 0),
            coverage_score=summary.get("coverage_score"),
            errors=summary.get("errors", [])
        )
    except Exception as e:
        logger.error("Failed to load run", run_id=run_id, error=str(e))
        raise HTTPException(500, "Failed to load run details")


@app.get("/runs/{run_id}/findings")
async def get_run_findings(run_id: str) -> Dict:
    """Get research findings for a run."""
    run_dir = settings.data_dir / "runs" / run_id
    findings_file = run_dir / "findings.json"
    
    if not findings_file.exists():
        raise HTTPException(404, "Findings not found")
    
    try:
        with open(findings_file) as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load findings", run_id=run_id, error=str(e))
        raise HTTPException(500, "Failed to load findings")


@app.get("/runs/{run_id}/validation")
async def get_run_validation(run_id: str) -> Dict:
    """Get validation report for a run."""
    run_dir = settings.data_dir / "runs" / run_id
    validation_file = run_dir / "validation.json"
    
    if not validation_file.exists():
        raise HTTPException(404, "Validation report not found")
    
    try:
        with open(validation_file) as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load validation", run_id=run_id, error=str(e))
        raise HTTPException(500, "Failed to load validation report")


@app.get("/runs/{run_id}/outline")
async def get_run_outline(run_id: str) -> str:
    """Get bid outline for a run."""
    run_dir = settings.data_dir / "runs" / run_id
    outline_file = run_dir / "outline.md"
    
    if not outline_file.exists():
        raise HTTPException(404, "Bid outline not found")
    
    try:
        with open(outline_file) as f:
            return f.read()
    except Exception as e:
        logger.error("Failed to load outline", run_id=run_id, error=str(e))
        raise HTTPException(500, "Failed to load bid outline")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
