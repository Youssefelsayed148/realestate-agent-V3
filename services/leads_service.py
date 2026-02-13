# services/leads_service.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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


def create_lead_row(db: Session, data: Dict[str, Any]) -> RagLead:
    lead = RagLead(
        conversation_id=_to_uuid_or_none(data.get("conversation_id")),
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
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


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
    lead.status = status
    if last_error:
        lead.last_error = last_error

    now = datetime.now(timezone.utc)
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
    office_email = (lead.source and None)  # no-op; keeps lint quiet

    office_email = __import__("os").getenv("OFFICE_EMAIL")
    if not office_email:
        return update_lead_status(db, lead, status="failed", last_error="Missing OFFICE_EMAIL")

    reply_to = __import__("os").getenv("EMAIL_REPLY_TO")

    # Build minimal, trustworthy email from snapshot only (DB is source of truth)
    snap = lead.selection_snapshot or {}
    title = snap.get("project_name") or snap.get("project") or "Selected option"
    location = snap.get("location") or snap.get("interest_area") or lead.interest_area or ""

    user_subject = "Viewing request received"
    user_html = f"""
    <p>Hi {lead.name or ""},</p>
    <p>We received your request and an agent will contact you shortly.</p>
    <p><b>Selection:</b> {title}<br/>
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

    # Send user email first, then office email
    try:
        provider_id_1 = ""
        if lead.email:
            provider_id_1 = send_email(
                to_email=lead.email,
                subject=user_subject,
                html_content=user_html,
                reply_to=reply_to,
            )
            lead = update_lead_status(db, lead, status="email_pending", email_user_sent=True, provider_message_id=provider_id_1)

        provider_id_2 = send_email(
            to_email=office_email,
            subject=office_subject,
            html_content=office_html,
            reply_to=reply_to,
        )
        lead = update_lead_status(db, lead, status="email_sent", email_office_sent=True, provider_message_id=provider_id_2 or lead.email_provider_message_id)

        return lead

    except EmailSendError as e:
        return update_lead_status(db, lead, status="failed", last_error=str(e))
    except Exception as e:
        return update_lead_status(db, lead, status="failed", last_error=f"Unexpected: {e}")
