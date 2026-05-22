from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from src.shared.config.settings import get_settings


class FallbackReason(str, Enum):
    MISSING_API_KEY = "missing_api_key"
    MODEL_ERROR = "model_error"
    LOW_CONFIDENCE = "low_confidence"
    GUARDRAIL_BLOCK = "guardrail_block"


class PromptTemplate(str, Enum):
    GREETING = "greeting"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"
    HANDOFF_SUMMARY = "handoff_summary"


class GuardrailResult(BaseModel):
    allowed: bool = True
    reason: str | None = None


class StructuredLLMResponse(BaseModel):
    reply: str
    confidence: float = Field(ge=0.0, le=1.0)
    follow_up_question: str | None = None
    template_used: PromptTemplate


class OrchestrationPayload(BaseModel):
    used_llm: bool
    response: StructuredLLMResponse | None = None
    fallback_reason: FallbackReason | None = None


@dataclass(frozen=True)
class ModelSettings:
    version: str
    model: str
    temperature: float
    max_output_tokens: int
    confidence_threshold: float
    max_reply_chars: int


PROMPT_CONFIG_VERSION = "2026-05-22.1"
PROMPT_TEMPLATES: dict[PromptTemplate, str] = {
    PromptTemplate.GREETING: "Greet the user warmly and ask one relevant vehicle-preference question.",
    PromptTemplate.FOLLOW_UP: "Generate one concise follow-up question from missing preferences.",
    PromptTemplate.CLARIFICATION: "Ask for clarification when the user's intent is ambiguous.",
    PromptTemplate.HANDOFF_SUMMARY: "Summarize conversation state and prepare handoff note.",
}


class LLMClient(Protocol):
    def generate_json(self, *, model: str, prompt: str, temperature: float, max_output_tokens: int) -> str: ...


class OpenAIJSONClient:
    def __init__(self, api_key: str):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)

    def generate_json(self, *, model: str, prompt: str, temperature: float, max_output_tokens: int) -> str:
        response = self._client.responses.create(
            model=model,
            input=prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        return response.output_text


class ChatOrchestrator:
    def __init__(self, client: LLMClient | None = None, settings: ModelSettings | None = None):
        cfg = get_settings()
        self._api_key = cfg.openai_api_key
        self._client = client if client is not None else (OpenAIJSONClient(self._api_key) if self._api_key else None)
        self._settings = settings or ModelSettings(
            version=PROMPT_CONFIG_VERSION,
            model="gpt-4.1-mini",
            temperature=0.3,
            max_output_tokens=260,
            confidence_threshold=0.55,
            max_reply_chars=380,
        )

    def build_prompt(self, *, session: dict[str, Any], user_message: str, template: PromptTemplate) -> str:
        memory = session.get("messages", [])[-6:]
        preferences = session.get("preferences", {})
        return (
            f"Prompt config version: {self._settings.version}\n"
            "You are a car buying assistant. Tone: concise, friendly, factual. "
            "Do not fabricate finance or legal claims.\n"
            f"Template: {template.value} => {PROMPT_TEMPLATES[template]}\n"
            f"Session preferences: {json.dumps(preferences, default=str)}\n"
            f"Recent messages: {json.dumps(memory, default=str)}\n"
            f"User message: {user_message}\n"
            "Return strict JSON: {\"reply\": str, \"confidence\": float, \"follow_up_question\": str|null, \"template_used\": str}"
        )

    def _guardrails(self, reply: str) -> GuardrailResult:
        lower = reply.lower()
        blocked_phrases = ["guaranteed approval", "legal advice", "financial advice"]
        if any(p in lower for p in blocked_phrases):
            return GuardrailResult(allowed=False, reason="blocked_claim")
        return GuardrailResult()

    def _bound_reply(self, reply: str) -> str:
        if len(reply) <= self._settings.max_reply_chars:
            return reply
        return reply[: self._settings.max_reply_chars - 1].rstrip() + "…"

    def run(self, *, session: dict[str, Any], user_message: str, template: PromptTemplate) -> OrchestrationPayload:
        if self._client is None:
            return OrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.MISSING_API_KEY)
        prompt = self.build_prompt(session=session, user_message=user_message, template=template)
        try:
            raw = self._client.generate_json(
                model=self._settings.model,
                prompt=prompt,
                temperature=self._settings.temperature,
                max_output_tokens=self._settings.max_output_tokens,
            )
            parsed = StructuredLLMResponse.model_validate_json(raw)
        except (TimeoutError, ValidationError, json.JSONDecodeError, Exception):
            return OrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.MODEL_ERROR)
        if parsed.confidence < self._settings.confidence_threshold:
            return OrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.LOW_CONFIDENCE)
        guard = self._guardrails(parsed.reply)
        if not guard.allowed:
            return OrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.GUARDRAIL_BLOCK)
        parsed.reply = self._bound_reply(parsed.reply)
        return OrchestrationPayload(used_llm=True, response=parsed)
