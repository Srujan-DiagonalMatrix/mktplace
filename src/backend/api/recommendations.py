from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Optional

from src.backend.api.image_paths import recommendation_image_path
from src.backend.startup import get_catalog
from src.shared.config.constants import DEFAULT_PLACEHOLDER_IMAGE_PATH
from src.backend.services.ai.conversation_orchestrator import get_preferences
from src.backend.services.recommendations.filtering import apply_filters
from src.backend.services.recommendations.ranker import rank_vehicles
from src.backend.services.recommendations.explanations import build_explanation

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/from_session")
def recommendations_from_session(session_id: Optional[str] = None, limit: int = 3):
    # Keep endpoint default aligned with ranker default/top-N product requirement.
    catalog = get_catalog()
    if not catalog:
        raise HTTPException(status_code=503, detail="Catalog not loaded")
    prefs = get_preferences(session_id or "")
    vehicles = [v.model_dump() for v in catalog.vehicles.values()]
    pricing = {k: v.model_dump() for k, v in catalog.pricing.items()}
    candidates = apply_filters(vehicles, pricing, prefs)
    ranked = rank_vehicles(candidates, pricing, prefs, limit=limit)
    # attach explanations
    for r in ranked:
        vid = r.get("vehicle_id")
        r["explanation"] = build_explanation(prefs, r, pricing.get(vid, {}))
        # attach resolved image path (backend knows mounted assets)
        try:
            img_path, is_placeholder = catalog.resolve_vehicle_image(vid)
            r["image"] = recommendation_image_path(img_path)
            r["is_placeholder"] = bool(is_placeholder)
        except Exception:
            r["image"] = recommendation_image_path(DEFAULT_PLACEHOLDER_IMAGE_PATH)
            r["is_placeholder"] = True
    return ranked
