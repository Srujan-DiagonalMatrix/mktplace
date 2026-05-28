from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from src.shared.config.settings import get_settings
from src.backend.services.ai.curated_runtime_adapter import CuratedInteractionAdapter


class FallbackReason(str, Enum):
    MISSING_API_KEY = "missing_api_key"
    MODEL_ERROR = "model_error"
    LOW_CONFIDENCE = "low_confidence"
    GUARDRAIL_BLOCK = "guardrail_block"
    DEPENDENCY_ERROR = "dependency_error"
    POLICY_MISMATCH = "policy_mismatch"


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
    assistant_action: str = "respond"
    follow_up_question: str | None = None
    follow_up_slot_tag: str | None = None
    template_used: PromptTemplate


class OrchestrationPayload(BaseModel):
    used_llm: bool
    response: StructuredLLMResponse | None = None
    fallback_reason: FallbackReason | None = None


class PolicyLLMResponse(BaseModel):
    assistant_action: str
    target_slot: str | None = None
    question_text: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class PolicyOrchestrationPayload(BaseModel):
    used_llm: bool
    response: PolicyLLMResponse | None = None
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
    def __init__(self, client: LLMClient | None = None, settings: ModelSettings | None = None, curated_adapter: CuratedInteractionAdapter | None = None):
        cfg = get_settings()
        self._api_key = cfg.openai_api_key
        self._init_error_reason: FallbackReason | None = None
        if client is not None:
            self._client = client
        elif not self._api_key:
            self._client = None
            self._init_error_reason = FallbackReason.MISSING_API_KEY
        else:
            try:
                self._client = OpenAIJSONClient(self._api_key)
            except Exception:
                self._client = None
                self._init_error_reason = FallbackReason.DEPENDENCY_ERROR
        self._settings = settings or ModelSettings(
            version=PROMPT_CONFIG_VERSION,
            model=cfg.openai_chat_model,
            temperature=0.3,
            max_output_tokens=260,
            confidence_threshold=0.55,
            max_reply_chars=380,
        )
        self._policy_mode = cfg.llm_policy_mode
        self._policy_confidence_threshold = cfg.llm_policy_confidence_threshold
        self._allowed_actions = {"respond", "ask_follow_up", "handoff"}
        self._curated_adapter = curated_adapter or CuratedInteractionAdapter()


    @property
    def model_name(self) -> str:
        return self._settings.model

    def build_prompt(
        self,
        *,
        session: dict[str, Any],
        user_message: str,
        template: PromptTemplate,
        policy_decision: dict[str, Any] | None = None,
        few_shot_exemplars: list[dict[str, Any]] | None = None,
    ) -> str:
        memory = session.get("messages", [])[-6:]
        preferences = session.get("preferences", {})
        policy = policy_decision or {}
        exemplar_text = json.dumps(few_shot_exemplars or [], default=str)
        return (
            f"Prompt config version: {self._settings.version}\n"
            "You are a car buying assistant. Tone: concise, friendly, factual. "
            "Do not fabricate finance or legal claims.\n"
            f"Template: {template.value} => {PROMPT_TEMPLATES[template]}\n"
            f"Session preferences: {json.dumps(preferences, default=str)}\n"
            f"Deterministic policy decision: {json.dumps(policy, default=str)}\n"
            f"Curated few-shot exemplars: {exemplar_text}\n"
            f"Recent messages: {json.dumps(memory, default=str)}\n"
            f"User message: {user_message}\n"
            "Return strict JSON: {\"reply\": str, \"confidence\": float, \"assistant_action\": str, "
            "\"follow_up_question\": str|null, \"follow_up_slot_tag\": str|null, \"template_used\": str}.\n"
            "Consistency rules: assistant_action SHOULD align with deterministic policy assistant_action. "
            "If assistant_action is ask_follow_up, follow_up_question must be a non-empty string and follow_up_slot_tag "
            "should be the canonical slot name (for example: budget, fuel_type, body_type)."
        )

    def _accept_llm_action(self, parsed: StructuredLLMResponse, expected_action: str | None) -> bool:
        if parsed.assistant_action not in self._allowed_actions:
            return False
        if self._policy_mode == "strict":
            return expected_action is None or parsed.assistant_action == expected_action
        if parsed.confidence < self._policy_confidence_threshold:
            return False
        if expected_action is None:
            return True
        if self._policy_mode == "hybrid":
            return parsed.assistant_action == expected_action
        return True

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

    def run(
        self,
        *,
        session: dict[str, Any],
        user_message: str,
        template: PromptTemplate,
        policy_decision: dict[str, Any] | None = None,
    ) -> OrchestrationPayload:
        if self._client is None:
            return OrchestrationPayload(
                used_llm=False,
                fallback_reason=self._init_error_reason or FallbackReason.MODEL_ERROR,
            )
        preferences = session.get("preferences", {})
        few_shot_exemplars = self._curated_adapter.get_few_shot_exemplars(
            preferences=preferences,
            hesitation_count=int(preferences.get("hesitation_count") or 0),
        )
        prompt = self.build_prompt(session=session, user_message=user_message, template=template, policy_decision=policy_decision, few_shot_exemplars=few_shot_exemplars)
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
        expected_action = (policy_decision or {}).get("assistant_action")
        target_slot = (policy_decision or {}).get("target_slot")
        if not self._accept_llm_action(parsed, expected_action):
            return OrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.POLICY_MISMATCH)
        if parsed.assistant_action == "ask_follow_up":
            if not parsed.follow_up_question or not parsed.follow_up_question.strip():
                return OrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.POLICY_MISMATCH)
            if target_slot and (parsed.follow_up_slot_tag or "").lower() != target_slot.lower():
                return OrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.POLICY_MISMATCH)
        if parsed.confidence < self._settings.confidence_threshold:
            return OrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.LOW_CONFIDENCE)
        guard = self._guardrails(parsed.reply)
        if not guard.allowed:
            return OrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.GUARDRAIL_BLOCK)
        parsed.reply = self._bound_reply(parsed.reply)
        return OrchestrationPayload(used_llm=True, response=parsed)

    def run_policy_orchestrator(
        self,
        *,
        session: dict[str, Any],
        user_message: str,
    ) -> PolicyOrchestrationPayload:
        if self._client is None:
            return PolicyOrchestrationPayload(
                used_llm=False,
                fallback_reason=self._init_error_reason or FallbackReason.MODEL_ERROR,
            )
        memory = session.get("messages", [])[-6:]
        preferences = session.get("preferences", {})
        prompt = (
            f"Prompt config version: {self._settings.version}\n"
            "You are a dialogue policy orchestrator for a car buying assistant.\n"
            f"Session preferences: {json.dumps(preferences, default=str)}\n"
            f"Recent messages: {json.dumps(memory, default=str)}\n"
            f"User message: {user_message}\n"
            "Return strict JSON with fields only: "
            '{"assistant_action": str, "target_slot": str|null, "question_text": str|null, "confidence": float, "reason": str}.\n'
            "assistant_action must be one of: ask_follow_up, clarify_with_options, summarize_and_recommend.\n"
            "If assistant_action is summarize_and_recommend, target_slot and question_text should be null."
        )
        try:
            raw = self._client.generate_json(
                model=self._settings.model,
                prompt=prompt,
                temperature=self._settings.temperature,
                max_output_tokens=self._settings.max_output_tokens,
            )
            parsed = PolicyLLMResponse.model_validate_json(raw)
        except (TimeoutError, ValidationError, json.JSONDecodeError, Exception):
            return PolicyOrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.MODEL_ERROR)

        if parsed.confidence < self._settings.confidence_threshold:
            return PolicyOrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.LOW_CONFIDENCE)
        if parsed.assistant_action not in {"ask_follow_up", "clarify_with_options", "summarize_and_recommend"}:
            return PolicyOrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.POLICY_MISMATCH)
        if parsed.assistant_action == "summarize_and_recommend" and (parsed.target_slot or parsed.question_text):
            return PolicyOrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.POLICY_MISMATCH)
        if parsed.assistant_action != "summarize_and_recommend" and (not parsed.target_slot or not parsed.question_text):
            return PolicyOrchestrationPayload(used_llm=False, fallback_reason=FallbackReason.POLICY_MISMATCH)

        return PolicyOrchestrationPayload(used_llm=True, response=parsed)
