from __future__ import annotations

from typing import List, Dict, Any
from .match_score import compute_match_score


def rank_vehicles(candidate_list: List[Dict[str, Any]], pricing: Dict[str, Any], prefs: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    scored = []
    for v in candidate_list:
        vid = v.get("vehicle_id")
        p = pricing.get(vid, {})
        score = compute_match_score(prefs, v, p)
        v_copy = dict(v)
        v_copy["pricing"] = p
        for key in (
            "monthly_from_gbp",
            "list_price_gbp",
            "deposit_gbp",
            "term_months",
            "apr_percent",
        ):
            if key in p:
                v_copy[key] = p[key]
        v_copy["match_score"] = score
        scored.append(v_copy)
    scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored[:limit]
