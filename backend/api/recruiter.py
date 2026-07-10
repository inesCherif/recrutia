"""
Recruiter API Routes
POST /api/recruiter/generate-job
POST /api/recruiter/score-candidates
GET  /api/recruiter/offers
POST /api/recruiter/offers

All offers are persisted in SQLite via AuthService (no more JSON files).
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

from backend.api.deps import get_current_user, auth_service
from backend.api.dependencies import get_recruiter_coordinator
from models.user import User
from agents.entrepreneur.recruiter_agents import RecruiterCoordinator
from services.anonymizer_service import anonymizer_service

router = APIRouter(prefix="/api/recruiter", tags=["Recruiter"])


# --- Request / Response Schemas ---

class GenerateJobRequest(BaseModel):
    description: str

class GenerateJobResponse(BaseModel):
    job_data: dict
    linkedin_post: str
    offer_id: str
    form_url: str

class CandidateInput(BaseModel):
    nom: str
    prenom: Optional[str] = ""
    email: Optional[str] = ""
    cv_text: str

class ScoreCandidatesRequest(BaseModel):
    candidates: List[CandidateInput]
    job_data: dict

class SaveOfferRequest(BaseModel):
    job_data: dict
    linkedin_post: str
    offer_id: str
    form_url: str


# --- Routes ---

@router.post("/generate-job", response_model=GenerateJobResponse)
def generate_job(
    req: GenerateJobRequest,
    current_user: User = Depends(get_current_user),
    coordinator: RecruiterCoordinator = Depends(get_recruiter_coordinator),
):
    """Generate a structured job description + LinkedIn post from natural language."""
    offer_id = f"OFF-{int(datetime.now().timestamp())}"
    form_url = f"http://localhost:5173/apply?offer_id={offer_id}"

    result = coordinator.create_job_posting(raw_input=req.description, form_url=form_url)

    return GenerateJobResponse(
        job_data=result.get("job_data", {}),
        linkedin_post=result.get("linkedin_post", ""),
        offer_id=offer_id,
        form_url=form_url,
    )


@router.post("/score-candidates")
def score_candidates(
    req: ScoreCandidatesRequest,
    current_user: User = Depends(get_current_user),
    coordinator: RecruiterCoordinator = Depends(get_recruiter_coordinator),
):
    """AI-score candidates against job requirements."""
    user_id = str(current_user.id)

    # Anonymize each candidate's CV before sending to the AI scoring agent.
    # This ensures real names/emails are never sent to external APIs.
    candidates_dicts = []
    for c in req.candidates:
        d = c.dict()
        d["cv_text"] = anonymizer_service.anonymize(d.get("cv_text", ""), user_id)
        candidates_dicts.append(d)

    scored = coordinator.evaluate_candidates(candidates_dicts, req.job_data)
    scored_with_plans = coordinator.plan_interviews(scored, req.job_data)

    # Deanonymize the candidate names in the results returned to the recruiter UI
    for candidate in scored_with_plans:
        if "nom" in candidate:
            candidate["nom"] = anonymizer_service.deanonymize(candidate["nom"], user_id)
        if "prenom" in candidate:
            candidate["prenom"] = anonymizer_service.deanonymize(candidate["prenom"], user_id)

    return {"scored_candidates": scored_with_plans}


@router.get("/offers")
def list_offers(current_user: User = Depends(get_current_user)):
    """List all saved offers for the current user (from SQLite)."""
    offers = auth_service.load_user_offers(current_user.id)
    return {"offers": offers}


@router.post("/offers")
def save_offer_route(req: SaveOfferRequest, current_user: User = Depends(get_current_user)):
    """Save a generated offer to SQLite."""
    auth_service.save_offer(
        user_id=current_user.id,
        job_data=req.job_data,
        linkedin_post=req.linkedin_post,
        offer_id=req.offer_id,
        form_url=req.form_url,
    )
    return {"message": "Offer saved successfully"}
