from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests


@dataclass
class IntentResult:
    intent: str
    entities: Dict[str, Any]
    missing_slots: List[str]
    confidence: float


class OllamaIntentRouter:
    """
    Free local intent router using Ollama.

    Uses /api/chat (more compatible across Ollama setups).
    Default endpoint: http://localhost:11434
    """

    def __init__(
        self,
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        timeout_s: int = 30,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def route(
        self,
        user_text: str,
        conversation_state: Dict[str, Any],
        last_messages: Optional[List[Dict[str, str]]] = None,
    ) -> IntentResult:
        prompt = self._build_prompt(
            user_text=user_text,
            conversation_state=conversation_state,
            last_messages=last_messages or [],
        )

        raw = self._ollama_chat(prompt)
        data = self._extract_json(raw)

        # ---- Type-safe parsing (Pylance friendly) ----
        intent = str(data.get("intent", "general_question")).strip()

        raw_entities = data.get("entities")
        entities: Dict[str, Any] = raw_entities if isinstance(raw_entities, dict) else {}

        raw_missing = data.get("missing_slots")
        missing_slots: List[str] = raw_missing if isinstance(raw_missing, list) else []

        confidence_raw = data.get("confidence", 0.5)
        try:
            confidence = float(confidence_raw)
        except Exception:
            confidence = 0.5

        # ---- Hard guards ----
        allowed_intents = {
            "search_projects",
            "filter_units",
            "project_details",
            "compare_projects",
            "schedule_visit",
            "budget_check",
            "general_question",
        }
        if intent not in allowed_intents:
            intent = "general_question"

        allowed_slots = {
            "budget_min",
            "budget_max",
            "location_area",
            "unit_type",
            "bedrooms",
            "delivery_year",
            "payment_plan",
            "project_name",
            "compare_list",
            "phone",
            "name",
        }
        missing_slots = [s for s in missing_slots if isinstance(s, str) and s in allowed_slots]

        # Normalize entity keys/values (money parsing, unit type, etc.)
        entities = self._normalize_entities(entities, user_text=user_text)

        return IntentResult(
            intent=intent,
            entities=entities,
            missing_slots=missing_slots,
            confidence=max(0.0, min(1.0, confidence)),
        )

    # -------------------------
    # Ollama call (/api/chat)
    # -------------------------
    def _ollama_chat(self, prompt: str) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 350,
            },
        }
        r = requests.post(url, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        j = r.json()
        msg = j.get("message") or {}
        return msg.get("content", "") or ""

    # -------------------------
    # JSON serialization helper
    # -------------------------
    def _json_default(self, obj: Any) -> Any:
        """
        Allows json.dumps() to serialize SQLAlchemy Numeric (Decimal) values in state.
        """
        if isinstance(obj, Decimal):
            return float(obj)
        # UUID, datetime, etc. -> string fallback
        return str(obj)

    # -------------------------
    # Prompt
    # -------------------------
    def _build_prompt(
        self,
        user_text: str,
        conversation_state: Dict[str, Any],
        last_messages: List[Dict[str, str]],
    ) -> str:
        history = "\n".join(
            f"{m.get('role','user')}: {m.get('content','')}".strip()
            for m in last_messages[-6:]
            if isinstance(m, dict)
        )

        # ✅ IMPORTANT: default=self._json_default prevents Decimal crash
        state_json = json.dumps(conversation_state, ensure_ascii=False, default=self._json_default)

        return f"""
You are an intent and entity extraction engine for a real-estate chatbot in Egypt.
Return ONLY valid JSON. No markdown. No explanations.

Allowed intents:
- search_projects
- filter_units
- project_details
- compare_projects
- schedule_visit
- budget_check
- general_question

Entity keys you may output (only if present):
- budget_min (number)
- budget_max (number)
- location_area (string)
- unit_type (string: apartment|villa|chalet|townhouse|duplex|studio|penthouse|any)
- bedrooms (integer)
- delivery_year (integer)
- payment_plan (string: cash|installments|either)
- project_name (string)
- compare_list (array of strings project names)
- name (string)
- phone (string)

Rules:
1) Use conversation_state as memory; don't ask for things already known.
2) missing_slots: list ONLY what is required to proceed for this intent.
3) If user asks to compare, fill compare_list.
4) If user asks for project details, fill project_name if mentioned.
5) Budget examples: "3M" => 3000000, "3.5m" => 3500000.
6) If user says "under", "max", "at most", "أقل من", "بحد أقصى" => it's budget_max.
7) location_area should be a clean area like: New Cairo, Sheikh Zayed, 6th of October, North Coast, Ain Sokhna, New Capital.

Return JSON with EXACT keys:
{{
  "intent": "...",
  "entities": {{ ... }},
  "missing_slots": ["..."],
  "confidence": 0.0
}}

conversation_state (memory):
{state_json}

recent_history:
{history}

user_text:
{user_text}
""".strip()

    # -------------------------
    # JSON extraction
    # -------------------------
    def _extract_json(self, text: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            block = m.group(0)
            try:
                parsed = json.loads(block)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        return {
            "intent": "general_question",
            "entities": {},
            "missing_slots": [],
            "confidence": 0.3,
        }

    # -------------------------
    # Normalization
    # -------------------------
    def _normalize_entities(self, entities: Dict[str, Any], user_text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = dict(entities)

        # Convert budget strings like "3M" -> number
        for k in ("budget_min", "budget_max"):
            if k in out:
                out[k] = self._coerce_money(out.get(k))

        # ✅ Fix common LLM confusion: "under X" should be budget_max
        if "budget_min" in out and "budget_max" not in out:
            if self._text_implies_max_budget(user_text):
                out["budget_max"] = out["budget_min"]
                out.pop("budget_min", None)

        # Bedrooms int
        if "bedrooms" in out:
            try:
                out["bedrooms"] = int(out["bedrooms"])
            except Exception:
                out.pop("bedrooms", None)

        # Delivery year int
        if "delivery_year" in out:
            try:
                out["delivery_year"] = int(out["delivery_year"])
            except Exception:
                out.pop("delivery_year", None)

        # Unit type normalize
        if "unit_type" in out and isinstance(out["unit_type"], str):
            u = out["unit_type"].strip().lower()
            mapping = {
                "apt": "apartment",
                "apartment": "apartment",
                "flat": "apartment",
                "villa": "villa",
                "chalet": "chalet",
                "townhouse": "townhouse",
                "duplex": "duplex",
                "studio": "studio",
                "penthouse": "penthouse",
                "any": "any",
                "either": "any",
            }
            out["unit_type"] = mapping.get(u, out["unit_type"])

        # Payment plan normalize
        if "payment_plan" in out and isinstance(out["payment_plan"], str):
            p = out["payment_plan"].strip().lower()
            if p in ("cash", "installments", "either"):
                out["payment_plan"] = p
            else:
                out.pop("payment_plan", None)

        # compare_list ensure list[str]
        if "compare_list" in out:
            if isinstance(out["compare_list"], list):
                out["compare_list"] = [str(x).strip() for x in out["compare_list"] if str(x).strip()]
            else:
                out.pop("compare_list", None)

        return out

    def _text_implies_max_budget(self, text: str) -> bool:
        t = text.lower()
        triggers = [
            "under",
            "max",
            "maximum",
            "at most",
            "less than",
            "below",
            "أقل من",
            "بحد أقصى",
            "حد أقصى",
        ]
        return any(k in t for k in triggers)

    def _coerce_money(self, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (int, float)):
            return float(v)

        s = str(v).strip().lower().replace(",", "")

        # 3m, 3.5m, 3 million
        m = re.match(r"^(\d+(\.\d+)?)\s*(m|million)$", s)
        if m:
            return float(m.group(1)) * 1_000_000

        # 250k
        m = re.match(r"^(\d+(\.\d+)?)\s*(k|thousand)$", s)
        if m:
            return float(m.group(1)) * 1_000

        try:
            return float(s)
        except Exception:
            return None
