# services/leads_service.py
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.rag_leads import RagLead
from .email_service import send_email, EmailSendError


def _to_uuid_or_none(value: Optional[str]) -> Optional[uuid.UUID]:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_lead_row(db: Session, data: Dict[str, Any]) -> RagLead:
    """
    Creates a lead row. If conversation_id FK fails, retry with NULL conversation_id.
    """
    def _make_lead(conversation_uuid: Optional[uuid.UUID]) -> RagLead:
        return RagLead(
            conversation_id=conversation_uuid,
            name=data.get("name"),
            phone=data.get("phone"),
            email=data.get("email"),
            preferred_contact_time=data.get("preferred_contact_time"),
            selection_type=data.get("selection_type"),
            interest_project_id=data.get("interest_project_id"),
            interest_unit_id=data.get("interest_unit_id"),
            interest_area=data.get("interest_area"),
            selection_snapshot=data.get("selection_snapshot"),
            visit_mode=data.get("visit_mode"),
            preferred_visit_times=data.get("preferred_visit_times"),
            visit_address=data.get("visit_address"),
            status="email_pending",
            source=data.get("source"),
            notes=data.get("notes"),
        )

    conv_uuid = _to_uuid_or_none(data.get("conversation_id"))

    lead = _make_lead(conv_uuid)
    db.add(lead)

    try:
        db.commit()
        db.refresh(lead)
        return lead

    except IntegrityError as e:
        db.rollback()

        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        # FK fails because conversation_id doesn't exist -> retry with NULL conversation_id
        if "rag_leads_conversation_id_fkey" in msg:
            lead = _make_lead(None)
            db.add(lead)
            db.commit()
            db.refresh(lead)
            return lead

        raise


def update_lead_status(
    db: Session,
    lead: RagLead,
    *,
    status: str,
    last_error: Optional[str] = None,
    email_user_sent: bool = False,
    email_office_sent: bool = False,
    provider_message_id: Optional[str] = None,
) -> RagLead:
    """
    Updates status and timestamps. Saves provider message id (last one sent).
    """
    lead.status = status

    if last_error is not None:
        # store even empty string if you want to explicitly clear
        lead.last_error = last_error

    now = _now_utc()
    if email_user_sent:
        lead.email_user_sent_at = now
    if email_office_sent:
        lead.email_office_sent_at = now
    if provider_message_id:
        lead.email_provider_message_id = provider_message_id

    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def send_confirmation_emails(db: Session, lead: RagLead) -> RagLead:
    """
    Sends:
      1) User confirmation email (if lead.email exists)
      2) Office notification email (required)
    Status outcomes:
      - email_sent: office email sent successfully (user email optional)
      - failed: missing config or any send failure
    """
    office_email = os.getenv("OFFICE_EMAIL")
    if not office_email:
        return update_lead_status(
            db,
            lead,
            status="failed",
            last_error="Missing OFFICE_EMAIL env var",
        )

    reply_to = os.getenv("EMAIL_REPLY_TO")  # optional

    # Build minimal, trustworthy email from snapshot only (DB is source of truth)
    snap = lead.selection_snapshot or {}
    title = snap.get("project_name") or snap.get("project") or "Selected option"
    location = snap.get("location") or snap.get("interest_area") or (lead.interest_area or "")

    user_subject = "Viewing request received"
    user_html = f"""
    <p>Hi {lead.name or ""},</p>
    <p>We received your request and an agent will contact you shortly.</p>
    <p>
      <b>Selection:</b> {title}<br/>
      <b>Location:</b> {location}<br/>
      <b>Visit:</b> {lead.visit_mode or "N/A"}<br/>
    </p>
    <p>Thank you.</p>
    """

    office_subject = "New lead from chatbot"
    office_html = f"""
    <p><b>New Lead</b></p>
    <p>
      <b>Name:</b> {lead.name or ""}<br/>
      <b>Phone:</b> {lead.phone or ""}<br/>
      <b>Email:</b> {lead.email or ""}<br/>
      <b>Visit mode:</b> {lead.visit_mode or ""}<br/>
      <b>Preferred times:</b> {lead.preferred_visit_times or ""}<br/>
      <b>Selection type:</b> {lead.selection_type or ""}<br/>
      <b>Project ID:</b> {lead.interest_project_id or ""}<br/>
      <b>Unit ID:</b> {lead.interest_unit_id or ""}<br/>
      <b>Snapshot:</b> {snap}<br/>
    </p>
    """

    try:
        # Start: clear last_error and keep email_pending
        lead = update_lead_status(db, lead, status="email_pending", last_error=None)

        # 1) User email (optional)
        if lead.email:
            user_provider_id = send_email(
                to_email=lead.email,
                subject=user_subject,
                html_content=user_html,
                reply_to=reply_to,
            )
            lead = update_lead_status(
                db,
                lead,
                status="email_pending",
                email_user_sent=True,
                provider_message_id=user_provider_id or lead.email_provider_message_id,
            )

        # 2) Office email (required)
        office_provider_id = send_email(
            to_email=office_email,
            subject=office_subject,
            html_content=office_html,
            reply_to=reply_to,
        )
        lead = update_lead_status(
            db,
            lead,
            status="email_sent",
            email_office_sent=True,
            provider_message_id=office_provider_id or lead.email_provider_message_id,
        )

        return lead

    except EmailSendError as e:
        return update_lead_status(db, lead, status="failed", last_error=str(e))
    except Exception as e:
        return update_lead_status(db, lead, status="failed", last_error=f"Unexpected: {e}")
