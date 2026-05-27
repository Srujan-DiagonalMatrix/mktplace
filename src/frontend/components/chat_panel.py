from __future__ import annotations

from datetime import datetime
from html import escape
import os
from typing import Any

import streamlit as st

from src.frontend.api_client.client import BackendClient
from src.frontend.state.session_state import get_session_id, set_preferences

client = BackendClient()

PREFERENCE_KEYS = {
    "intent",
    "monthly_budget",
    "monthly_from_gbp",
    "deposit_gbp",
    "term_months",
    "fuel_type",
    "body_type",
    "transmission",
    "family_size",
    "mileage_range",
    "doors",
    "seats",
    "annual_mileage_limit",
    "employment_status",
    "part_exchange",
    "callback_opt_in",
}
INITIAL_MESSAGE_TEXTS = [
    "👋 Hi there! I'm your AI car buying assistant.",
    "I’ll ask a few quick questions to find your best-fit car.",
    "To begin, what monthly budget feels right for you?",
]


def _message_time() -> str:
    return datetime.now().strftime("%H:%M")


def _create_message(
    role: str,
    text: str,
    *,
    quick_replies: list[str] | None = None,
    assistant_action: str | None = None,
    target_slot: str | None = None,
    question_metadata: dict[str, Any] | None = None,
    confidence: float | None = None,
    time: str | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "role": role,
        "text": text,
        "time": time or _message_time(),
    }
    if quick_replies:
        message["quick_replies"] = quick_replies
    if assistant_action:
        message["assistant_action"] = assistant_action
    if target_slot:
        message["target_slot"] = target_slot
    if question_metadata:
        message["question_metadata"] = question_metadata
    if confidence is not None:
        message["confidence"] = confidence
    return message


def _initial_messages() -> list[dict[str, Any]]:
    return [_create_message("ai", text) for text in INITIAL_MESSAGE_TEXTS]


def _ensure_messages() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = _initial_messages()


def _extract_preferences(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {}

    if isinstance(response.get("preferences"), dict):
        source = response["preferences"]
    else:
        source = response

    return {
        key: source.get(key)
        for key in PREFERENCE_KEYS
        if source.get(key) is not None
    }


def _safe_text(value: Any) -> str:
    return escape(str(value), quote=True)


def _render_message(message: dict[str, Any]) -> None:
    safe_text = _safe_text(message.get("text", ""))
    safe_time = _safe_text(message.get("time", ""))

    if message.get("role") == "ai":
        st.markdown(
            (
                "<div class='msg-ai'>"
                "<div class='ai-avatar'>🤖</div>"
                f"<div><div>{safe_text}</div><div class='msg-time'>{safe_time}</div></div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='msg-user'>{safe_text}<div class='msg-time'>{safe_time}</div></div>",
            unsafe_allow_html=True,
        )


def _render_messages_frame(messages: list[dict[str, Any]]) -> None:
    parts: list[str] = [f"<div class='chat-scroll-frame' data-message-count='{len(messages)}'>"]
    for message in messages:
        safe_text = _safe_text(message.get("text", ""))
        safe_time = _safe_text(message.get("time", ""))
        if message.get("role") == "ai":
            parts.append(
                "<div class='msg-ai'>"
                "<div class='ai-avatar'>🤖</div>"
                f"<div><div>{safe_text}</div><div class='msg-time'>{safe_time}</div></div>"
                "</div>"
            )
        else:
            parts.append(
                f"<div class='msg-user'>{safe_text}<div class='msg-time'>{safe_time}</div></div>"
            )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)
    try:
        import streamlit.components.v1 as components

        components.html(
            """
            <script>
            const root = window.parent;
            const frames = root.document.querySelectorAll('.chat-scroll-frame');
            if (!frames.length) return;
            const frame = frames[frames.length - 1];

            const forceBottom = () => { frame.scrollTop = frame.scrollHeight; };
            forceBottom();
            requestAnimationFrame(forceBottom);
            setTimeout(forceBottom, 50);
            setTimeout(forceBottom, 150);
            setTimeout(forceBottom, 300);

            if (!frame.dataset.observeBottom) {
              const observer = new MutationObserver(() => forceBottom());
              observer.observe(frame, { childList: true, subtree: true, characterData: true });
              frame.dataset.observeBottom = "1";
            }
            </script>
            """,
            height=0,
        )
    except Exception:
        pass


def _latest_quick_replies() -> list[str]:
    messages = st.session_state.get("chat_messages", [])
    if not messages:
        return []
    latest = messages[-1]
    if latest.get("role") == "ai" and latest.get("quick_replies"):
        return list(latest["quick_replies"])
    return []


def _latest_ai_message() -> dict[str, Any] | None:
    messages = st.session_state.get("chat_messages", [])
    for message in reversed(messages):
        if message.get("role") == "ai":
            return message
    return None


def _is_dev_badge_enabled() -> bool:
    if os.getenv("FRONTEND_DEV_BADGE", "").lower() in {"1", "true", "yes", "on"}:
        return True
    return bool(st.session_state.get("dev_mode"))


def _clarification_options(message: dict[str, Any]) -> list[str]:
    metadata = message.get("question_metadata") or {}
    options = metadata.get("options")
    if isinstance(options, list) and options:
        return [str(option) for option in options]
    quick_replies = message.get("quick_replies")
    if isinstance(quick_replies, list):
        return [str(option) for option in quick_replies]
    return []


def chat_panel() -> None:
    _ensure_messages()
    session_id = get_session_id()

    st.markdown(
        "<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;'>"
        "<div style=\"font-size:18px;font-weight:700;\">Conversation</div>"
        "<div style='display:none;'>Hi! I&#x27;m your AI car buying assistant.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    msg_area = st.container()
    with msg_area:
        _render_messages_frame(st.session_state["chat_messages"])

    quick_replies = _latest_quick_replies()
    latest_ai_message = _latest_ai_message()
    assistant_action = (latest_ai_message or {}).get("assistant_action")

    if _is_dev_badge_enabled() and latest_ai_message:
        confidence = latest_ai_message.get("confidence")
        confidence_text = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "n/a"
        st.caption(
            f"[dev] action={latest_ai_message.get('assistant_action', 'n/a')} "
            f"target_slot={latest_ai_message.get('target_slot', 'n/a')} "
            f"confidence={confidence_text}"
        )

    if assistant_action == "clarify_with_options" and latest_ai_message:
        quick_replies = _clarification_options(latest_ai_message)
    elif assistant_action == "summarize_and_recommend":
        quick_replies = ["Yes, show recommendations", "Adjust preferences"]

    if quick_replies:
        if assistant_action == "clarify_with_options":
            st.caption("Please choose one option so I can continue:")
        elif assistant_action == "summarize_and_recommend":
            st.caption("Does this summary look right before I recommend cars?")
        cols = st.columns(len(quick_replies))
        for index, reply in enumerate(quick_replies):
            with cols[index]:
                st.button(
                    reply,
                    key=f"quick_reply_{reply}",
                    on_click=_send_quick_reply,
                    args=(reply, session_id),
                )

    input_cols = st.columns([0.9, 0.1])
    with input_cols[0]:
        st.text_input(
            "message",
            placeholder="Type your answer...",
            key="chat_input",
            label_visibility="hidden",
        )
    with input_cols[1]:
        st.button(
            "➤",
            key="chat_send",
            on_click=_send_input_message,
            args=(session_id,),
        )


def _send_input_message(session_id: str | None = None) -> None:
    txt = str(st.session_state.get("chat_input", "")).strip()
    if not txt:
        return
    _send_message(txt, session_id)
    st.session_state["chat_input"] = ""


def _send_quick_reply(txt: str, session_id: str | None = None) -> None:
    _send_message(txt, session_id)


def _send_message(
    txt: str,
    session_id: str | None = None,
    backend_client: BackendClient | None = None,
) -> None:
    _ensure_messages()
    active_client = backend_client or client

    st.session_state["chat_messages"].append(_create_message("user", txt))

    try:
        response = active_client.post_chat({"session_id": session_id, "message": txt})
        returned_preferences = _extract_preferences(response)
        if returned_preferences:
            set_preferences(returned_preferences)

        st.session_state["chat_messages"].append(
            _create_message(
                "ai",
                response.get("reply", "Thanks! Tell me a little more so I can refine your options."),
                quick_replies=response.get("quick_replies") or None,
                assistant_action=response.get("assistant_action"),
                target_slot=response.get("target_slot"),
                question_metadata=response.get("question_metadata")
                if isinstance(response.get("question_metadata"), dict)
                else None,
                confidence=response.get("confidence")
                if isinstance(response.get("confidence"), (int, float))
                else None,
            )
        )
    except Exception:
        st.session_state["chat_messages"].append(
            _create_message("ai", "Sorry, failed to reach backend.")
        )
