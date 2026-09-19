"""LLM provider abstraction — Groq primary, deterministic fallback when unconfigured."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from backend.app.agent.evidence import format_report
from backend.app.config import get_settings, resolve_llm_backend


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def plan_investigation(self, question: str, month_resolution: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_report(self, evidence: dict[str, Any]) -> str:
        raise NotImplementedError


class DeterministicLLMProvider(LLMProvider):
    name = "deterministic_fallback"

    def plan_investigation(self, question: str, month_resolution: dict[str, Any]) -> dict[str, Any]:
        return {
            "tools": [
                "variance",
                "sql_query:revenue_by_state",
                "sql_query:festivals_in_range",
                "forecast",
                "anomaly_check",
            ],
            "rationale": (
                "Deterministic planner selected standard investigation toolchain "
                f"for mode={month_resolution.get('mode')}."
            ),
            "provider": self.name,
        }

    def generate_report(self, evidence: dict[str, Any]) -> str:
        report = format_report(evidence)
        return (
            f"{report}\n\n"
            f"[Report provider: {self.name} — GROQ_API_KEY not configured]"
        )


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self) -> None:
        settings = get_settings()
        from langchain_groq import ChatGroq

        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required for GroqProvider")
        self._llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0,
        )

    def plan_investigation(self, question: str, month_resolution: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "You are the MarketLens investigation planner. Choose MCP tools only from this list:\n"
            "variance, sql_query:revenue_by_state, sql_query:festivals_in_range, forecast, anomaly_check, rag_search\n"
            "Return JSON with keys: tools (array of strings), rationale (string).\n"
            "Do not invent numbers or SQL.\n"
            f"Question: {question}\n"
            f"Resolved month context: {json.dumps(month_resolution)}\n"
        )
        response = self._llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = DeterministicLLMProvider().plan_investigation(question, month_resolution)
        payload["provider"] = self.name
        return payload

    def generate_report(self, evidence: dict[str, Any]) -> str:
        prompt = (
            "Write an evidence-backed investigation report using ONLY the JSON evidence below.\n"
            "Rules:\n"
            "- Every numeric value must come from the evidence JSON.\n"
            "- Cite evidence IDs from supporting_query_ids.\n"
            "- Do not claim anomalies/festivals are causal; describe as associations only.\n"
            "- Do not query databases or invent figures.\n"
            "- Forecast comparisons are category-grain only.\n\n"
            f"Evidence JSON:\n{json.dumps(evidence, default=str)}\n"
        )
        response = self._llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        return f"{text}\n\n[Report provider: {self.name}]"


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.groq_api_key:
        return GroqProvider()
    return DeterministicLLMProvider()


def llm_status() -> dict[str, Any]:
    settings = get_settings()
    provider = get_llm_provider()
    return {
        "active_provider": provider.name,
        "resolved_backend": resolve_llm_backend(),
        "groq_configured": bool(settings.groq_api_key),
        "groq_model": settings.groq_model,
        "using_fallback": provider.name == "deterministic_fallback",
    }


def probe_groq_api() -> dict[str, Any]:
    """Minimal live Groq call through provider abstraction. Never returns secrets."""
    settings = get_settings()
    if not settings.groq_api_key:
        return {"ok": False, "reason": "no_groq_api_key", "groq_configured": False}
    try:
        provider = GroqProvider()
        response = provider._llm.invoke("Reply with exactly: GROQ_OK")
        text = response.content if hasattr(response, "content") else str(response)
        return {
            "ok": "GROQ_OK" in str(text).upper(),
            "groq_configured": True,
            "model": settings.groq_model,
            "provider": provider.name,
        }
    except Exception as exc:
        return {
            "ok": False,
            "groq_configured": True,
            "reason": exc.__class__.__name__,
            "provider": "groq",
        }
