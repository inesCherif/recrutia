"""
Student API Routes
POST /api/student/analyze-cv
POST /api/student/search-jobs
POST /api/student/generate-application
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

from backend.api.deps import get_current_user
from backend.api.dependencies import get_cv_analyzer, get_student_coordinator
from models.user import User
from agents.student.multi_agent_system import CVAnalyzerAgent, CoordinatorAgent
from services.anonymizer_service import anonymizer_service

router = APIRouter(prefix="/api/student", tags=["Student"])


# --- Request / Response Schemas ---

class AnalyzeCVRequest(BaseModel):
    cv_text: str

class AnalyzeCVResponse(BaseModel):
    analysis: dict

class SearchJobsRequest(BaseModel):
    cv_text: str
    cv_analysis: Optional[dict] = None
    jobs_per_site: int = 5
    demo_mode: bool = False
    location: str = ""
    include_remote: bool = True
    selected_sources: Optional[List[str]] = None

class GenerateApplicationRequest(BaseModel):
    cv_text: str
    job: dict  # { title, company, location, description, ... }


# --- Routes ---

@router.post("/analyze-cv", response_model=AnalyzeCVResponse)
def analyze_cv(
    req: AnalyzeCVRequest,
    current_user: User = Depends(get_current_user),
    analyzer: CVAnalyzerAgent = Depends(get_cv_analyzer),
):
    """Analyze CV text and extract skills, experience, recommendations."""
    analysis = analyzer.analyze_cv(req.cv_text)
    return AnalyzeCVResponse(analysis=analysis)


@router.post("/search-jobs")
def search_jobs(
    req: SearchJobsRequest,
    current_user: User = Depends(get_current_user),
    coordinator: CoordinatorAgent = Depends(get_student_coordinator),
):
    """Run intelligent multi-source job search powered by AI agents."""
    jobs = coordinator.intelligent_job_search(
        cv_text=req.cv_text,
        jobs_per_site=req.jobs_per_site,
        use_demo=req.demo_mode,
        user_location=req.location,
        selected_sources=req.selected_sources,
        include_remote=req.include_remote,
        cached_cv_analysis=req.cv_analysis,
    )

    # Deduplicate
    seen = {}
    for job in jobs:
        key = (job.get("title", "").lower().strip(), job.get("company", "").lower().strip())
        if key not in seen or job.get("ai_match_score", 0) > seen[key].get("ai_match_score", 0):
            seen[key] = job
    unique_jobs = list(seen.values())

    return {"jobs": unique_jobs, "total": len(unique_jobs)}


@router.post("/generate-application")
def generate_application(
    req: GenerateApplicationRequest,
    current_user: User = Depends(get_current_user),
    coordinator: CoordinatorAgent = Depends(get_student_coordinator),
):
    """Generate optimized CV, cover letter, and LinkedIn message for a specific job."""
    results = coordinator.run_full_pipeline(req.cv_text, req.job)

    # Deanonymize: restore real names/emails in the user-facing output
    user_id = str(current_user.id)
    optimized_cv     = anonymizer_service.deanonymize(results.get("optimized_cv", ""), user_id)
    cover_letter     = anonymizer_service.deanonymize(results.get("cover_letter", ""), user_id)
    linkedin_message = anonymizer_service.deanonymize(results.get("linkedin_message", ""), user_id)

    return {
        "optimized_cv": optimized_cv,
        "cover_letter": cover_letter,
        "linkedin_message": linkedin_message,
        "job_analysis": results.get("job_analysis", {}),
    }
