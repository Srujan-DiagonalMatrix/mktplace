from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.models.inventory import InventoryVehicle, VehiclePricing

client = TestClient(app)


class _ContractCatalog:
    def __init__(self):
        self.vehicles = {
            "veh-001": InventoryVehicle(
                car_id="veh-001",
                make="Ford",
                model="Focus",
                fuel_type="Petrol",
                transmission="Automatic",
                seats=5,
            )
        }
        self.pricing = {
            "veh-001": VehiclePricing(
                price_id="price-001",
                car_id="veh-001",
                list_price_gbp=22000,
                monthly_from_gbp=399,
                apr_percent=6.2,
                term_months=36,
            )
        }

    def resolve_vehicle_image(self, vehicle_id: str):
        return f"assets/vehicles/{vehicle_id}.png", False

    def get_pricing(self, vehicle_id: str):
        return self.pricing.get(vehicle_id)

    def filter(self, **_kwargs):
        return list(self.vehicles.values())

    def get_vehicle(self, vehicle_id: str):
        return self.vehicles.get(vehicle_id)


def test_chat_contract_has_stable_core_fields():
    response = client.post("/chat/message", json={"message": "budget £500 petrol"})
    assert response.status_code == 200
    body = response.json()
    assert {"reply", "session_id", "intent", "monthly_budget"}.issubset(body.keys())


def test_catalog_contract_list_and_detail_shape_stable(monkeypatch):
    monkeypatch.setattr("src.backend.api.catalog.get_catalog", lambda: _ContractCatalog())

    list_response = client.get("/catalog/")
    assert list_response.status_code == 200
    items = list_response.json()
    assert isinstance(items, list)
    assert items
    first = items[0]
    assert {"vehicle_id", "make", "model", "fuel_type"}.issubset(first.keys())

    detail_response = client.get(f"/catalog/{first['vehicle_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert "vehicle" in detail and "pricing" in detail
    assert detail["vehicle"].get("make") == first.get("make")


def test_recommendation_and_finance_contracts_stable(monkeypatch):
    monkeypatch.setattr("src.backend.api.recommendations.get_catalog", lambda: _ContractCatalog())
    monkeypatch.setattr("src.backend.api.finance.get_catalog", lambda: _ContractCatalog())

    chat = client.post("/chat/message", json={"message": "budget £450 automatic"}).json()
    recs_response = client.get(
        "/recommendations/from_session", params={"session_id": chat["session_id"], "limit": 3}
    )
    assert recs_response.status_code == 200
    recs = recs_response.json()
    assert isinstance(recs, list)
    if recs:
        rec = recs[0]
        assert {"vehicle_id", "match_score", "explanation"}.issubset(rec.keys())

        finance_response = client.get(
            "/finance/estimate",
            params={"vehicle_id": rec["vehicle_id"], "deposit": 0, "term_months": 36},
        )
        assert finance_response.status_code == 200
        finance = finance_response.json()
        assert {"estimate", "disclaimer"}.issubset(finance.keys())


def test_enquiry_contract_create_shape_stable_when_db_unavailable():
    payload = {
        "session_id": "contract-test",
        "vehicle_id": "veh-001",
        "full_name": "Contract User",
        "email": "contract@example.com",
        "phone": "01234567890",
        "monthly_budget": 500,
        "deposit": 1000,
        "buying_timeframe": "1-3 months",
        "consent_contact": True,
    }
    create_response = client.post("/enquiries/", json=payload)
    assert create_response.status_code in {201, 202}
    created = create_response.json()
    if create_response.status_code == 201:
        assert {"enquiry_id", "status", "payload"}.issubset(created.keys())
    else:
        assert "detail" in created
