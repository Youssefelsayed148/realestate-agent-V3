# rag/orchestrator.py
from __future__ import annotations

import re
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from rag.state_manager import StateManager, StateUpdate
from rag.intent_router import OllamaIntentRouter
from rag.search_service import search_units, min_price_for_filters


class ChatOrchestrator:
    """
    Deterministic Phase 2 Orchestrator:
    - LLM extracts intent + entities only (when not in follow-up answer mode)
    - Orchestrator computes missing slots from DB state (fixed order)
    - Follow-up answers are handled deterministically
    - When required slots are filled -> runs DB search and returns top matches
    """

    REQUIRED_ORDER = ["location_area", "budget_max", "unit_type"]
    NICE_TO_HAVE_ORDER = ["bedrooms", "payment_plan"]
    OPTIONAL_SLOTS = {"budget_min", "delivery_year"}

    def __init__(self, db: Session, model: str = "llama3.1:8b", channel_default: str = "web"):
        self.db = db
        self.sm = StateManager(db)
        self.router = OllamaIntentRouter(model=model)
        self.channel_default = channel_default

    def handle_user_message(
        self,
        user_text: str,
        conversation_id: Optional[UUID] = None,
        channel: Optional[str] = None,
        user_identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            # 1) Create/get conversation
            conv = self.sm.get_or_create_conversation(
                conversation_id=conversation_id,
                channel=channel or self.channel_default,
                user_identifier=user_identifier,
            )

            # 2) Save user message
            self.sm.add_message(conversation_id=conv.id, role="user", content=user_text)

            # 3) Load state + recent messages
            state = self.sm.get_state(conv.id)
            recent = self.sm.get_last_messages(conv.id, limit=10)

            last_assistant = None
            for m in reversed(recent):
                if m.role == "assistant":
                    last_assistant = m
                    break

            # -------------------------
            # A) Follow-up answer mode
            # -------------------------
            if last_assistant and last_assistant.intent == "follow_up":
                asked_slot = self._asked_slot_from_followup(last_assistant)
                if asked_slot:
                    extracted = self._extract_slot_value(asked_slot, user_text)

                    if extracted is not None:
                        upd = self._state_update_for_slot(asked_slot, extracted)
                        if upd:
                            self.sm.merge_state(state, upd)

                        missing = self._compute_missing_slots_from_state(state)

                        if missing:
                            q = self._question_for_slot(missing[0])
                            self.sm.add_message(
                                conversation_id=conv.id,
                                role="assistant",
                                content=q,
                                intent="follow_up",
                                entities_json={"missing_slots": missing},
                            )
                            self.sm.commit()
                            return {
                                "conversation_id": conv.id,
                                "reply": q,
                                "intent": state.last_intent or "search_projects",
                                "entities": {asked_slot: extracted},
                                "missing_slots": missing,
                            }

                        # Nothing missing -> run search
                        return self._run_search_and_reply(
                            conversation_id=conv.id,
                            state=state,
                            extra_entities={asked_slot: extracted},
                        )

            # -------------------------
            # B) Normal mode -> call LLM for intent/entities
            # -------------------------
            state_dict = {
                "budget_min": state.budget_min,
                "budget_max": state.budget_max,
                "location_area": state.location_area,
                "unit_type": state.unit_type,
                "bedrooms": state.bedrooms,
                "delivery_year": state.delivery_year,
                "payment_plan": state.payment_plan,
                "last_intent": state.last_intent,
                "last_project_ids": state.last_project_ids,
            }
            last_msgs = [{"role": m.role, "content": m.content} for m in recent[-6:]]

            res = self.router.route(
                user_text=user_text,
                conversation_state=state_dict,
                last_messages=last_msgs,
            )

            # Merge extracted entities into state
            upd = StateUpdate(
                budget_min=res.entities.get("budget_min"),
                budget_max=res.entities.get("budget_max"),
                location_area=res.entities.get("location_area"),
                unit_type=res.entities.get("unit_type"),
                bedrooms=res.entities.get("bedrooms"),
                delivery_year=res.entities.get("delivery_year"),
                payment_plan=res.entities.get("payment_plan"),
                last_intent=res.intent,
            )
            self.sm.merge_state(state, upd)

            missing = self._compute_missing_slots_from_state(state)

            if missing:
                q = self._question_for_slot(missing[0])
                self.sm.add_message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=q,
                    intent="follow_up",
                    entities_json={"missing_slots": missing, "intent": res.intent, "entities": res.entities},
                )
                self.sm.commit()
                return {
                    "conversation_id": conv.id,
                    "reply": q,
                    "intent": res.intent,
                    "entities": res.entities,
                    "missing_slots": missing,
                }

            return self._run_search_and_reply(
                conversation_id=conv.id,
                state=state,
                extra_entities=res.entities,
            )

        except Exception:
            self.sm.rollback()
            raise

    # -------------------------
    # Search + reply
    # -------------------------
    def _run_search_and_reply(
        self,
        conversation_id: UUID,
        state,
        extra_entities: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        extra_entities = extra_entities or {}

        budget_max = float(state.budget_max) if state.budget_max is not None else 0.0

        results = search_units(
            db=self.db,
            location_area=state.location_area or "",
            unit_type=state.unit_type or "",
            budget_max=budget_max,
            bedrooms=state.bedrooms,
            limit=5,
        )

        if not results:
            min_p = min_price_for_filters(
                db=self.db,
                location_area=state.location_area or "",
                unit_type=state.unit_type or "",
            )

            if min_p is not None:
                reply = (
                    "I couldn’t find matches with these filters.\n"
                    f"Lowest available in {state.location_area} for {state.unit_type} is about {int(min_p):,} EGP.\n"
                    "Do you want to increase your budget, or change area/unit type?"
                )
            else:
                reply = (
                    "I couldn’t find matches with these filters.\n"
                    "Do you want to increase your budget, or change area/unit type?"
                )

            payload = {
                "filters": self._state_filters_dict(state),
                "results": [],
                "extra_entities": extra_entities,
                "min_price_hint": min_p,
            }

            # StateManager will sanitize entities_json automatically
            self.sm.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=reply,
                intent=state.last_intent or "search_projects",
                entities_json=payload,
            )
            self.sm.commit()

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "intent": state.last_intent or "search_projects",
                "entities": payload,  # OK to return; test prints may still show Decimals if any exist (we avoid here)
                "missing_slots": [],
            }

        # Save UNIQUE last_project_ids
        seen: set[int] = set()
        project_ids: list[int] = []
        for r in results:
            pid = r.get("project_id")
            if pid is None:
                continue
            try:
                pid_int = int(pid)
            except Exception:
                continue
            if pid_int not in seen:
                seen.add(pid_int)
                project_ids.append(pid_int)

        self.sm.merge_state(state, StateUpdate(last_project_ids=project_ids))

        # Format reply
        lines = ["Here are the best matches I found:"]
        for i, r in enumerate(results, 1):
            project_name = r.get("project_name", "Unknown Project")
            project_area = r.get("project_area", "")
            utype = r.get("unit_type", "")
            unit_area = r.get("unit_area_sqm", "")
            price = r.get("unit_price", "")

            try:
                price_fmt = f"{int(float(price)):,} EGP"
            except Exception:
                price_fmt = f"{price} EGP"

            lines.append(f"{i}) {project_name} ({project_area}) — {utype} — {unit_area} m² — {price_fmt}")

        lines.append("\nWould you like details about one of these projects (e.g., Bloomfields or Sarai)?")
        reply = "\n".join(lines)

        payload = {
            "filters": self._state_filters_dict(state),
            "results": results,
            "extra_entities": extra_entities,
        }

        self.sm.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=reply,
            intent=state.last_intent or "search_projects",
            entities_json=payload,  # ✅ sanitized in StateManager
        )
        self.sm.commit()

        # IMPORTANT: return a JSON-safe version for API / printing
        safe_payload = self.sm.json_safe(payload)

        return {
            "conversation_id": conversation_id,
            "reply": reply,
            "intent": state.last_intent or "search_projects",
            "entities": safe_payload,  # ✅ Decimals converted
            "missing_slots": [],
        }

    def _state_filters_dict(self, state) -> Dict[str, Any]:
        return {
            "location_area": state.location_area,
            "budget_max": float(state.budget_max) if state.budget_max is not None else None,
            "budget_min": float(state.budget_min) if state.budget_min is not None else None,
            "unit_type": state.unit_type,
            "bedrooms": state.bedrooms,
            "payment_plan": state.payment_plan,
            "delivery_year": state.delivery_year,
            "last_project_ids": state.last_project_ids,
        }

    # -------------------------
    # Missing slots
    # -------------------------
    def _compute_missing_slots_from_state(self, state) -> list[str]:
        missing: list[str] = []

        def is_missing(val: Any) -> bool:
            return val is None or val == "" or val == []

        for slot in self.REQUIRED_ORDER:
            if is_missing(getattr(state, slot, None)):
                missing.append(slot)

        if missing:
            return missing

        for slot in self.NICE_TO_HAVE_ORDER:
            if slot in self.OPTIONAL_SLOTS:
                continue
            if is_missing(getattr(state, slot, None)):
                missing.append(slot)

        return missing

    def _asked_slot_from_followup(self, last_assistant_msg) -> Optional[str]:
        if isinstance(last_assistant_msg.entities_json, dict):
            ms = last_assistant_msg.entities_json.get("missing_slots")
            if isinstance(ms, list) and ms and isinstance(ms[0], str):
                return ms[0]
        return None

    # -------------------------
    # Slot extraction (deterministic)
    # -------------------------
    def _extract_slot_value(self, slot: str, text: str) -> Any:
        t = text.strip().lower()

        if slot == "unit_type":
            if "apartment" in t or "apt" in t or "شقة" in t:
                return "apartment"
            if "villa" in t or "فيلا" in t:
                return "villa"
            if "chalet" in t or "شاليه" in t:
                return "chalet"
            if "townhouse" in t:
                return "townhouse"
            if "duplex" in t:
                return "duplex"
            if "studio" in t:
                return "studio"
            if "penthouse" in t:
                return "penthouse"
            return None

        if slot == "payment_plan":
            if "cash" in t or "كاش" in t:
                return "cash"
            if "installment" in t or "installments" in t or "تقسيط" in t or "اقساط" in t:
                return "installments"
            if "either" in t or "any" in t or "مش فارقة" in t:
                return "either"
            return None

        if slot == "bedrooms":
            m = re.search(r"\b(\d{1,2})\b", t)
            return int(m.group(1)) if m else None

        if slot in ("budget_max", "budget_min"):
            m = re.search(r"(\d+(\.\d+)?)\s*(m|million)\b", t)
            if m:
                return float(m.group(1)) * 1_000_000
            m = re.search(r"(\d+(\.\d+)?)\s*(k|thousand)\b", t)
            if m:
                return float(m.group(1)) * 1_000
            m = re.search(r"\b(\d{5,9})\b", t)
            return float(m.group(1)) if m else None

        return None

    def _state_update_for_slot(self, slot: str, value: Any) -> Optional[StateUpdate]:
        if slot == "unit_type":
            return StateUpdate(unit_type=value)
        if slot == "payment_plan":
            return StateUpdate(payment_plan=value)
        if slot == "bedrooms":
            return StateUpdate(bedrooms=value)
        if slot == "budget_max":
            return StateUpdate(budget_max=value)
        if slot == "budget_min":
            return StateUpdate(budget_min=value)
        if slot == "location_area":
            return StateUpdate(location_area=value)
        if slot == "delivery_year":
            return StateUpdate(delivery_year=value)
        return None

    def _question_for_slot(self, slot: str) -> str:
        mapping = {
            "budget_max": "What is your maximum budget (in EGP)?",
            "budget_min": "Do you have a minimum budget?",
            "location_area": "Which area do you prefer (e.g., New Cairo, Sheikh Zayed, 6th of October)?",
            "unit_type": "Do you prefer apartment, villa, or chalet?",
            "bedrooms": "How many bedrooms do you need?",
            "delivery_year": "Do you need a specific delivery year?",
            "payment_plan": "Do you prefer cash or installments?",
        }
        return mapping.get(slot, f"Quick question: what is your {slot.replace('_', ' ')}?")
