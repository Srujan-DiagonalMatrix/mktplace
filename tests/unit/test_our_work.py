from pathlib import Path


def test_driveway_thumbnail_is_text_svg_with_embedded_image():
    thumbnail = Path("assets/driveway-landscaping.svg")
    contents = thumbnail.read_text(encoding="utf-8")

    assert contents.startswith("<svg")
    assert "data:image/webp;base64," in contents
    assert "Driveway and landscaping transformation" in contents
