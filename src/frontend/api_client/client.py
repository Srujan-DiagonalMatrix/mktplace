from __future__ import annotations

import requests
from typing import Any
from src.shared.config.settings import get_settings

settings = get_settings()


class BackendClient:
    def __init__(self, base_url: str | None = None):
        self.base = base_url or f"http://{settings.fastapi_host}:{settings.fastapi_port}"

    def health(self) -> Any:
        return requests.get(f"{self.base}/health").json()

    def list_catalog(self, **params) -> Any:
        return requests.get(f"{self.base}/catalog/", params=params).json()

    def post_chat(self, payload: dict) -> Any:
        return requests.post(f"{self.base}/chat/message", json=payload).json()

    def create_enquiry(self, payload: dict) -> Any:
        return requests.post(f"{self.base}/enquiries/", json=payload)

    def get_recommendations(self, session_id: str | None = None, limit: int = 9) -> Any:
        params = {"limit": limit}
        if session_id:
            params["session_id"] = session_id
        return requests.get(f"{self.base}/recommendations/from_session", params=params, timeout=10).json()

    def shortlist_add(self, session_id: str, vehicle_id: str) -> Any:
        return requests.post(f"{self.base}/shortlist/add", params={"session_id": session_id, "vehicle_id": vehicle_id})

    def shortlist_remove(self, session_id: str, vehicle_id: str) -> Any:
        return requests.post(f"{self.base}/shortlist/remove", params={"session_id": session_id, "vehicle_id": vehicle_id})

    def shortlist_list(self, session_id: str) -> Any:
        return requests.get(f"{self.base}/shortlist/list", params={"session_id": session_id}).json()

    def get_finance(self, vehicle_id: str, deposit: float = 0.0, term_months: int = 36) -> Any:
        return requests.get(f"{self.base}/finance/estimate", params={"vehicle_id": vehicle_id, "deposit": deposit, "term_months": term_months}).json()

    def get_analytics_dashboard(self, **params) -> Any:
        clean = {k: v for k, v in params.items() if v is not None and v != "None"}
        return requests.get(f"{self.base}/analytics/dashboard", params=clean).json()
