from __future__ import annotations

import importlib
import sys


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlit:
    def __init__(self):
        self.markdown_calls: list[str] = []
        self.info_calls: list[str] = []
        self.button_calls: list[tuple[str, dict]] = []

    def markdown(self, body: str, **_kwargs):
        self.markdown_calls.append(body)

    def info(self, body: str):
        self.info_calls.append(body)

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_Context() for _ in range(count)]

    def button(self, label: str, **kwargs):
        self.button_calls.append((label, kwargs))
        return False


def _load_module(fake_st: _FakeStreamlit, monkeypatch):
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    sys.modules.pop("src.frontend.components.recommendation_cards", None)
    return importlib.import_module("src.frontend.components.recommendation_cards")


def test_recommendation_cards_render_vehicle_monthly_and_actions(monkeypatch):
    fake_st = _FakeStreamlit()
    module = _load_module(fake_st, monkeypatch)

    module.render_recommendation_cards(
        [
            {
                "vehicle_id": "car-1",
                "make": "Tesla",
                "model": "Model 3",
                "variant": "Long Range",
                "fuel_type": "Electric",
                "transmission": "Automatic",
                "seats": 5,
                "pricing": {"monthly_from_gbp": 449},
                "image": "assets/cars/model-3.png",
            }
        ]
    )

    rendered = "\n".join(fake_st.markdown_calls)
    assert "Tesla Model 3" in rendered
    assert "£449/mo" in rendered
    assert "View Details" in [label for label, _kwargs in fake_st.button_calls]
    assert "Shortlist" in [label for label, _kwargs in fake_st.button_calls]
    assert "Enquire" in [label for label, _kwargs in fake_st.button_calls]


def test_recommendation_cards_empty_state(monkeypatch):
    fake_st = _FakeStreamlit()
    module = _load_module(fake_st, monkeypatch)

    module.render_recommendation_cards([])

    rendered = "\n".join(fake_st.markdown_calls + fake_st.info_calls)
    assert "No recommendations yet" in rendered
    assert "chat with the assistant" in rendered.lower()
    assert fake_st.button_calls == []


def test_first_recommendation_card_includes_best_match_badge(monkeypatch):
    fake_st = _FakeStreamlit()
    module = _load_module(fake_st, monkeypatch)

    module.render_recommendation_cards(
        [
            {"make": "Ford", "model": "Puma", "pricing": {"monthly_from_gbp": 310}},
            {"make": "Kia", "model": "Niro", "pricing": {"monthly_from_gbp": 330}},
        ]
    )

    first_card_markup = next(
        call for call in fake_st.markdown_calls if "Ford Puma" in call
    )
    second_card_markup = next(
        call for call in fake_st.markdown_calls if "Kia Niro" in call
    )
    assert "Best Match" in first_card_markup
    assert "Best Match" not in second_card_markup


def test_recommendation_card_local_images_render_as_data_uris(monkeypatch):
    fake_st = _FakeStreamlit()
    module = _load_module(fake_st, monkeypatch)

    assert module._normalise_image_src("assets/placeholder.png").startswith(
        "data:image/png;base64,"
    )


def test_recommendation_card_remote_images_are_preserved(monkeypatch):
    fake_st = _FakeStreamlit()
    module = _load_module(fake_st, monkeypatch)

    assert module._normalise_image_src("https://example.com/car.png") == (
        "https://example.com/car.png"
    )


def test_recommendation_card_html_fragment_images_fallback_to_placeholder(monkeypatch):
    fake_st = _FakeStreamlit()
    module = _load_module(fake_st, monkeypatch)

    src = module._normalise_image_src('<div class="recommendation-card-heart">♡</div>')
    assert src.startswith("data:image/png;base64,")
