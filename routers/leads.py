# routers/leads.py
from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from db import get_db
from services.leads_service import create_lead_row, send_confirmation_emails


router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCreateRequest(BaseModel):
    conversation_id: Optional[str] = None

    name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=7)
    email: Optional[EmailStr] = None

    preferred_contact_time: Optional[str] = None

    # selection
    selection_type: Optional[str] = Field(default="project", description="project|unit")
    interest_project_id: Optional[int] = None
    interest_unit_id: Optional[int] = None
    interest_area: Optional[str] = None
    selection_snapshot: Optional[Dict[str, Any]] = None

    # visit
    visit_mode: str = Field(..., description="office|unit")
    preferred_visit_times: Optional[Any] = None  # jsonb array or object
    visit_address: Optional[str] = None

    source: Optional[str] = None
    notes: Optional[str] = None


class LeadCreateResponse(BaseModel):
    lead_id: str
    status: str


@router.post("", response_model=LeadCreateResponse)
def create_lead(payload: LeadCreateRequest, db: Session = Depends(get_db)) -> LeadCreateResponse:
    # Light guardrails
    if payload.visit_mode not in ("office", "unit"):
        raise HTTPException(status_code=400, detail="visit_mode must be 'office' or 'unit'")

    # Insert lead
    lead = create_lead_row(db, payload.model_dump())

    # Send emails + update lead row status
    lead = send_confirmation_emails(db, lead)

    return LeadCreateResponse(lead_id=str(lead.id), status=lead.status or "unknown")
