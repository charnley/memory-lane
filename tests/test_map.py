"""Tests for map.py — mocks API, tests cache, draw_map, draw_water, plot_points."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import matplotlib.pyplot as plt
import numpy as np
import pytest
from shapely.geometry import Polygon

from memory_lane.plot_utils.map import (
    PALETTE_BLUEPRINT,
    PALETTE_INK,
    PALETTE_SEPIA,
    ElevationGrid,
    Palette,
    draw_map,
    draw_water,
    get_elevation_grid,
    plot_points,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _synthetic_elevations(locations, dataset="srtm90m"):
    return [
        math.sin(math.radians(lat * 10)) * math.cos(math.radians(lon * 10)) * 500 + 600
        for lat, lon in locations
    ]


def _synthetic_elevations_with_nulls(locations, dataset="srtm90m"):
    """Return None for points above 60°N when using srtm90m."""
    results = []
    for lat, lon in locations:
        if dataset == "srtm90m" and lat > 60.0:
            results.append(None)
        else:
            e = math.sin(math.radians(lat * 10)) * math.cos(math.radians(lon * 10)) * 500 + 600
            results.append(e)
    return results


def _make_grid(grid_size: int = 10) -> ElevationGrid:
    lons, lats = np.meshgrid(
        np.linspace(10.5, 10.9, grid_size),
        np.linspace(59.7, 60.1, grid_size),
    )
    elev = np.random.default_rng(42).uniform(100, 800, (grid_size, grid_size))
    return ElevationGrid(
        lons=lons,
        lats=lats,
        elev=elev,
        center=(59.9, 10.7),
        zoom=10,
        grid_size=grid_size,
        datasets=["eudem25m"],
    )


# ---------------------------------------------------------------------------
# Palette dataclass
# ---------------------------------------------------------------------------


def test_palette_is_dataclass():
    p = Palette(bg="#fff", line_color="#000", point_color="#f00", title_color="#0f0")
    assert p.bg == "#fff"
    assert p.line_color == "#000"


def test_predefined_palettes():
    for p in (PALETTE_SEPIA, PALETTE_INK, PALETTE_BLUEPRINT):
        assert isinstance(p, Palette)
        assert p.bg and p.line_color and p.point_color and p.title_color


# ---------------------------------------------------------------------------
# get_elevation_grid
# ---------------------------------------------------------------------------


@patch("memory_lane.plot_utils.map._fetch_elevations", side_effect=_synthetic_elevations)
def test_get_elevation_grid_fetches(mock_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr("memory_lane.plot_utils.map.CACHE_DIR", tmp_path)
    grid = get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)
    assert isinstance(grid, ElevationGrid)
    assert grid.elev.shape == (10, 10)
    assert mock_fetch.call_count >= 1
    assert len(grid.datasets) >= 1


@patch("memory_lane.plot_utils.map._fetch_elevations", side_effect=_synthetic_elevations)
def test_get_elevation_grid_cache_hit(mock_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr("memory_lane.plot_utils.map.CACHE_DIR", tmp_path)
    get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)
    count = mock_fetch.call_count
    get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)
    assert mock_fetch.call_count == count


@patch("memory_lane.plot_utils.map._fetch_elevations", side_effect=_synthetic_elevations)
def test_get_elevation_grid_cache_miss_different_zoom(mock_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr("memory_lane.plot_utils.map.CACHE_DIR", tmp_path)
    get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)
    count = mock_fetch.call_count
    get_elevation_grid(center=(59.9, 10.7), zoom=8, grid_size=10)
    assert mock_fetch.call_count > count


@patch(
    "memory_lane.plot_utils.map._fetch_elevations", side_effect=_synthetic_elevations_with_nulls
)
def test_get_elevation_grid_fallback_at_boundary(mock_fetch, tmp_path, monkeypatch):
    """srtm90m nulls above 60°N filled by aster30m fallback."""
    monkeypatch.setattr("memory_lane.plot_utils.map.CACHE_DIR", tmp_path)
    from memory_lane.plot_utils.map import _fetch_elevations_with_fallback

    locations = [(60.5, 10.7), (59.5, 10.7)]
    with patch(
        "memory_lane.plot_utils.map._fetch_elevations",
        side_effect=_synthetic_elevations_with_nulls,
    ):
        results, datasets_used = _fetch_elevations_with_fallback(
            locations, ["srtm90m", "aster30m"]
        )
    assert results[0] != 0.0, "Null not filled by fallback"
    assert "srtm90m" in datasets_used
    assert "aster30m" in datasets_used


@patch("memory_lane.plot_utils.map._fetch_elevations", side_effect=_synthetic_elevations)
def test_get_elevation_grid_datasets_stored(mock_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr("memory_lane.plot_utils.map.CACHE_DIR", tmp_path)
    grid = get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)
    assert isinstance(grid.datasets, list)
    assert all(isinstance(d, str) for d in grid.datasets)


# ---------------------------------------------------------------------------
# draw_map
# ---------------------------------------------------------------------------


def test_draw_map_default_colors():
    grid = _make_grid()
    fig, ax = plt.subplots()
    draw_map(ax, grid)
    plt.close(fig)


def test_draw_map_explicit_colors():
    grid = _make_grid()
    fig, ax = plt.subplots()
    draw_map(ax, grid, color="#333333", bg="#eeeeee")
    plt.close(fig)


def test_draw_map_hypsometric_false():
    grid = _make_grid()
    fig, ax = plt.subplots()
    draw_map(ax, grid, hypsometric=False)
    plt.close(fig)


def test_draw_map_hypsometric_true():
    grid = _make_grid()
    fig, ax = plt.subplots()
    draw_map(ax, grid, hypsometric=True)
    plt.close(fig)


@pytest.mark.parametrize("palette", [PALETTE_SEPIA, PALETTE_INK, PALETTE_BLUEPRINT])
def test_draw_map_with_palette(palette):
    grid = _make_grid()
    fig, ax = plt.subplots()
    draw_map(ax, grid, color=palette.line_color, bg=palette.bg, hypsometric=True)
    plt.close(fig)


# ---------------------------------------------------------------------------
# draw_water
# ---------------------------------------------------------------------------


def _make_fake_feature(polys):
    """Return a mock cartopy NaturalEarthFeature that yields given polygons."""
    mock = MagicMock()
    mock.geometries.return_value = iter(polys)
    return mock


def test_draw_water_default_colors():
    fig, ax = plt.subplots()
    poly = Polygon([(10.6, 59.8), (10.8, 59.8), (10.8, 60.0), (10.6, 60.0)])
    with patch(
        "memory_lane.plot_utils.map.cfeature.NaturalEarthFeature",
        side_effect=[
            _make_fake_feature([poly]),  # ocean
            _make_fake_feature([]),  # lakes
        ],
    ):
        draw_water(ax, center=(59.9, 10.7), zoom=10)
    plt.close(fig)


def test_draw_water_explicit_colors():
    fig, ax = plt.subplots()
    poly = Polygon([(10.6, 59.8), (10.8, 59.8), (10.8, 60.0), (10.6, 60.0)])
    with patch(
        "memory_lane.plot_utils.map.cfeature.NaturalEarthFeature",
        side_effect=[
            _make_fake_feature([poly]),
            _make_fake_feature([poly]),
        ],
    ):
        draw_water(ax, center=(59.9, 10.7), zoom=10, color="#aaddff", edgecolor="#336699")
    plt.close(fig)


def test_draw_water_no_features():
    fig, ax = plt.subplots()
    with patch(
        "memory_lane.plot_utils.map.cfeature.NaturalEarthFeature",
        side_effect=[
            _make_fake_feature([]),
            _make_fake_feature([]),
        ],
    ):
        draw_water(ax, center=(59.9, 10.7), zoom=10)
    plt.close(fig)


@pytest.mark.parametrize("palette", [PALETTE_SEPIA, PALETTE_INK, PALETTE_BLUEPRINT])
def test_draw_water_all_palettes(palette):
    fig, ax = plt.subplots()
    with patch(
        "memory_lane.plot_utils.map.cfeature.NaturalEarthFeature",
        side_effect=[
            _make_fake_feature([]),
            _make_fake_feature([]),
        ],
    ):
        draw_water(
            ax, center=(59.9, 10.7), zoom=10, color=palette.bg, edgecolor=palette.line_color
        )
    plt.close(fig)


# ---------------------------------------------------------------------------
# plot_points
# ---------------------------------------------------------------------------


def test_plot_points_default():
    fig, ax = plt.subplots()
    plot_points(ax, [(59.91, 10.75), (59.88, 10.65)])
    plt.close(fig)


def test_plot_points_explicit_colors():
    fig, ax = plt.subplots()
    plot_points(ax, [(59.91, 10.75)], color="#ff0000", edgecolor="#ffffff")
    plt.close(fig)


def test_plot_points_size():
    fig, ax = plt.subplots()
    plot_points(ax, [(59.91, 10.75)], size=120)
    plt.close(fig)


def test_plot_points_empty():
    fig, ax = plt.subplots()
    plot_points(ax, [])
    plt.close(fig)


def test_plot_points_connect():
    fig, ax = plt.subplots()
    plot_points(ax, [(59.91, 10.75), (59.88, 10.65), (59.85, 10.70)], connect=True)
    plt.close(fig)


def test_plot_points_labels():
    fig, ax = plt.subplots()
    plot_points(ax, [(59.91, 10.75), (59.88, 10.65)], labels=["Start", "End"])
    plt.close(fig)


def test_plot_points_labels_partial_empty():
    fig, ax = plt.subplots()
    plot_points(ax, [(59.91, 10.75), (59.88, 10.65)], labels=["Start", ""])
    plt.close(fig)


def test_plot_points_labels_wrong_length():
    fig, ax = plt.subplots()
    with pytest.raises(ValueError):
        plot_points(ax, [(59.91, 10.75), (59.88, 10.65)], labels=["Only one"])
    plt.close(fig)


def test_plot_points_connect_with_labels():
    fig, ax = plt.subplots()
    plot_points(
        ax,
        [(59.91, 10.75), (59.88, 10.65), (59.85, 10.70)],
        color="#8b2020",
        edgecolor="#f5f0e8",
        size=60,
        labels=["A", "B", "C"],
        connect=True,
    )
    plt.close(fig)


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


@patch("memory_lane.plot_utils.map._fetch_elevations", side_effect=_synthetic_elevations)
def test_full_workflow(mock_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr("memory_lane.plot_utils.map.CACHE_DIR", tmp_path / "cache")

    grid = get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)
    p = PALETTE_SEPIA

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(p.bg)
    ax.set_facecolor(p.bg)

    draw_map(ax, grid, color=p.line_color, bg=p.bg)

    with patch(
        "memory_lane.plot_utils.map.cfeature.NaturalEarthFeature",
        side_effect=[
            _make_fake_feature([]),
            _make_fake_feature([]),
        ],
    ):
        draw_water(ax, center=(59.9, 10.7), zoom=10, color=p.bg, edgecolor=p.line_color)

    plot_points(
        ax,
        [(59.91, 10.75), (59.88, 10.65)],
        color=p.point_color,
        edgecolor=p.bg,
        labels=["Oslo", ""],
        connect=True,
    )

    out = tmp_path / "map.png"
    fig.tight_layout()
    fig.savefig(str(out), dpi=72, bbox_inches="tight")
    plt.close(fig)

    assert out.exists()
    assert out.stat().st_size > 1000
