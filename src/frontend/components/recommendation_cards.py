from __future__ import annotations

import base64
import mimetypes
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, List
from urllib.parse import urlparse

import streamlit as st

from src.frontend.api_client.client import BackendClient
from src.shared.config.constants import DEFAULT_PLACEHOLDER_IMAGE_PATH, PROJECT_ROOT

_PLACEHOLDER_IMAGE = "/assets/placeholder.png"
_ACTION_LABELS = ("View Details", "Shortlist", "Enquire")


def _is_browser_safe_image_src(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "data"}


@lru_cache(maxsize=128)
def _image_file_to_data_uri(path_value: str) -> str | None:
    path = Path(path_value)
    candidates = [path] if path.is_absolute() else [path, PROJECT_ROOT / path]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            mime_type = mimetypes.guess_type(candidate.name)[0] or "image/png"
            encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
            return f"data:{mime_type};base64,{encoded}"
    return None


def _normalise_image_src(image_path: Any) -> str:
    """Return a browser-renderable image source for recommendation cards.

    Streamlit does not automatically serve arbitrary repository files from
    ``/assets/...`` URLs. Recommendation API responses therefore use
    project-relative paths, while this renderer converts local files to data
    URIs so the HTML card images work without extra static-file routing.
    Remote URLs and existing data URIs are preserved.
    """
    raw = str(image_path).strip() if image_path else ""
    if raw and _is_browser_safe_image_src(raw):
        return raw

    if raw:
        data_uri = _image_file_to_data_uri(raw)
        if data_uri:
            return data_uri

    placeholder_data_uri = _image_file_to_data_uri(str(DEFAULT_PLACEHOLDER_IMAGE_PATH))
    return placeholder_data_uri or _PLACEHOLDER_IMAGE


def _money(value: Any) -> str:
    if value in (None, ""):
        return "Price on request"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    if amount.is_integer():
        return f"£{int(amount):,}"
    return f"£{amount:,.2f}"


def _monthly_amount(rec: dict) -> str:
    pricing = rec.get("pricing") if isinstance(rec.get("pricing"), dict) else {}
    value = (
        rec.get("monthly_from_gbp")
        or rec.get("monthly_payment_gbp")
        or pricing.get("monthly_from_gbp")
        or pricing.get("monthly_payment_gbp")
    )
    amount = _money(value)
    if amount == "Price on request":
        return amount
    return f"{amount}/mo"


def _vehicle_title(rec: dict) -> str:
    title = " ".join(
        part
        for part in (
            str(rec.get("make") or "").strip(),
            str(rec.get("model") or "").strip(),
        )
        if part
    )
    return title or "Recommended vehicle"


def _vehicle_subtitle(rec: dict) -> str:
    subtitle = (
        rec.get("variant")
        or rec.get("subtitle")
        or rec.get("body_type")
        or "Variant details available soon"
    )
    year = rec.get("registration_year")
    if year:
        return f"{subtitle} • {year}"
    return str(subtitle)


def _spec_value(rec: dict, key: str, fallback: str = "—") -> str:
    value = rec.get(key)
    return str(value) if value not in (None, "") else fallback


def _render_empty_state() -> None:
    st.markdown(
        """
        <div class="recommendation-empty-state" role="status">
          <div class="empty-illustration">🚗</div>
          <div>
            <h3>No recommendations yet</h3>
            <p>Chat with the assistant about your budget, fuel preference, and must-haves to see tailored matches here.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        "No recommendations yet — chat with the assistant to get personalised suggestions."
    )


def _vehicle_id(rec: dict, fallback: str) -> str:
    vehicle_id = rec.get("vehicle_id") or rec.get("id") or fallback
    return str(vehicle_id)


def _render_vehicle_card_html(rec: dict, *, idx: int, variant: str) -> None:
    safe_title = escape(_vehicle_title(rec))
    safe_subtitle = escape(_vehicle_subtitle(rec))
    safe_img_src = escape(_normalise_image_src(rec.get("image")), quote=True)
    safe_fuel_type = escape(_spec_value(rec, "fuel_type"))
    safe_transmission = escape(_spec_value(rec, "transmission"))
    safe_seats = escape(_spec_value(rec, "seats"))
    safe_monthly = escape(_monthly_amount(rec))
    badge_html = "<div class='badge'>Best Match</div>" if idx == 0 else ""

    if variant == "compact":
        st.markdown(
            f"""
            <div class='car-card' data-testid='recommendation-card'>
              <div style='position:relative;'>
                <div style='position:absolute;right:12px;top:12px;' class='heart' aria-label='Shortlist vehicle'>♡</div>
                <div style='position:absolute;left:12px;top:12px;'>{badge_html}</div>
                <img class='car-img' src='{safe_img_src}' alt='{safe_title}' />
              </div>
              <div style='font-size:18px;font-weight:700;color:#0F2A5F;margin-bottom:6px;'>{safe_title}</div>
              <div style='font-size:13px;color:#526580;margin-bottom:12px;'>{safe_subtitle}</div>
              <div style='display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:14px;color:#526580;font-size:13px;'>
                <div>⛽ {safe_fuel_type}</div>
                <div>⚙️ {safe_transmission}</div>
                <div>👥 {safe_seats} seats</div>
              </div>
              <div style='font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#64748B;'>Estimated Monthly</div>
              <div style='margin-top:4px;font-size:28px;font-weight:800;color:#0B7CFF;'>{safe_monthly}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <div class='car-card car-card-hero' data-testid='recommendation-card'>
          <div style='position:relative;'>
            <div style='position:absolute;left:12px;top:12px;'>{badge_html}</div>
            <img class='car-img' src='{safe_img_src}' alt='{safe_title}' />
          </div>
          <div style='font-size:22px;font-weight:700;color:#0F2A5F;margin-bottom:6px;'>{safe_title}</div>
          <div style='font-size:14px;color:#526580;margin-bottom:12px;'>{safe_subtitle}</div>
          <div style='display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:14px;color:#526580;font-size:14px;'>
            <div>⛽ {safe_fuel_type}</div>
            <div>⚙️ {safe_transmission}</div>
            <div>👥 {safe_seats} seats</div>
          </div>
          <div style='font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#64748B;'>Estimated Monthly</div>
          <div style='margin-top:4px;font-size:30px;font-weight:800;color:#0B7CFF;'>{safe_monthly}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _handle_view_details(rec: dict) -> None:
    st.session_state["selected_vehicle_obj"] = rec
    st.session_state["selected_vehicle"] = _vehicle_id(rec, fallback="")


def _handle_shortlist(
    rec: dict, session_id: str | None, client: BackendClient | None
) -> None:
    if not client:
        st.info("Shortlist is unavailable right now.")
        return
    sid = session_id or st.session_state.get("session_id")
    if not sid:
        st.info("Start a session to shortlist vehicles.")
        return
    try:
        client.shortlist_add(str(sid), _vehicle_id(rec, fallback=""))
        st.success("Added to shortlist")
    except Exception:
        st.error("Failed to add to shortlist")


def _handle_enquire(rec: dict) -> None:
    st.session_state["selected_vehicle_obj"] = rec
    st.session_state["selected_vehicle"] = _vehicle_id(rec, fallback="")
    st.success("Enquiry form opened below")


def _render_card_actions(
    rec: dict,
    *,
    idx: int,
    session_id: str | None,
    client: BackendClient | None,
) -> None:
    st.markdown("<div class='prototype-action-row'>", unsafe_allow_html=True)
    action_cols = st.columns(3)
    for action_idx, label in enumerate(_ACTION_LABELS):
        with action_cols[action_idx]:
            if st.button(
                label,
                key=f"recommendation_{idx}_{label.lower().replace(' ', '_')}",
                use_container_width=True,
            ):
                if label == "View Details":
                    _handle_view_details(rec)
                elif label == "Shortlist":
                    _handle_shortlist(rec, session_id, client)
                else:
                    _handle_enquire(rec)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_top3_cards(
    recs: list[dict], session_id: str | None, client: BackendClient | None
) -> None:
    cols = st.columns(3)
    for idx, rec in enumerate(recs[:3]):
        with cols[idx]:
            _render_vehicle_card_html(rec, idx=idx, variant="hero")
            _render_card_actions(rec, idx=idx, session_id=session_id, client=client)


def _render_compact_cards(
    recs: list[dict], session_id: str | None, client: BackendClient | None
) -> None:
    for row_start in range(0, len(recs), 3):
        row_recs = recs[row_start : row_start + 3]
        cols = st.columns(len(row_recs))
        for offset, rec in enumerate(row_recs):
            idx = row_start + offset
            with cols[offset]:
                _render_vehicle_card_html(rec, idx=idx, variant="compact")
                _render_card_actions(rec, idx=idx, session_id=session_id, client=client)


def render_recommendation_cards(
    recs: list[dict],
    *,
    variant: str = "top3",
    session_id: str | None = None,
    client: BackendClient | None = None,
) -> None:
    st.markdown(
        """
        <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;">
          <div style="font-size:24px;font-weight:700;color:#0F172A;">Top Recommendations</div>
          <div style="color:#4F6690;">Results tailored to your answers</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not recs:
        _render_empty_state()
        return

    if variant == "compact":
        _render_compact_cards(recs, session_id, client)
        return
    _render_top3_cards(recs[:3], session_id, client)
