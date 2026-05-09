"""Tests for draw_map — mocks API to avoid network calls."""

from unittest.mock import patch


def make_fake_fetch(n: int):
    """Return a mock _fetch_elevations that yields synthetic elevation data."""

    def fake_fetch(locations):
        # Simple synthetic terrain: elevation = sin(lat) * cos(lon) * 500 + 600
        results = []
        for lat, lon in locations:
            import math

            e = math.sin(math.radians(lat * 10)) * math.cos(math.radians(lon * 10))
            results.append(e * 500 + 600)
        return results

    return fake_fetch


@patch("memory_lane.plot_utils.map._fetch_elevations")
def test_draw_map_creates_file(mock_fetch, tmp_path):
    mock_fetch.side_effect = make_fake_fetch(0)

    from memory_lane.plot_utils.map import draw_map

    out = str(tmp_path / "test_map.png")
    fig = draw_map(
        center=(59.9, 10.7),  # Oslo
        zoom=10,
        points=[(59.91, 10.75), (59.88, 10.65)],
        output=out,
        grid_size=10,  # small grid for speed
    )

    import os

    assert os.path.exists(out), "PNG not created"
    assert os.path.getsize(out) > 1000, "PNG suspiciously small"
    fig.clf()


@patch("memory_lane.plot_utils.map._fetch_elevations")
def test_draw_map_styles(mock_fetch, tmp_path):
    mock_fetch.side_effect = make_fake_fetch(0)

    from memory_lane.plot_utils.map import draw_map

    for style in ("sepia", "ink", "blueprint"):
        out = str(tmp_path / f"map_{style}.png")
        fig = draw_map(
            center=(59.9, 10.7),
            zoom=10,
            output=out,
            grid_size=10,
            style=style,
        )
        import os

        assert os.path.exists(out), f"PNG not created for style={style}"
        fig.clf()


@patch("memory_lane.plot_utils.map._fetch_elevations")
def test_draw_map_no_points(mock_fetch, tmp_path):
    mock_fetch.side_effect = make_fake_fetch(0)

    from memory_lane.plot_utils.map import draw_map

    out = str(tmp_path / "map_nopoints.png")
    fig = draw_map(center=(48.85, 2.35), zoom=8, output=out, grid_size=10)

    import os

    assert os.path.exists(out)
    fig.clf()
