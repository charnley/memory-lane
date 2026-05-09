"""Tests for map.py — mocks API, tests cache, draw_map, plot_points independently."""

from __future__ import annotations

import math
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pytest

from memory_lane.plot_utils.map import (
    PALETTE_BLUEPRINT,
    PALETTE_INK,
    PALETTE_SEPIA,
    ElevationGrid,
    draw_map,
    get_elevation_grid,
    plot_points,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _synthetic_elevations(locations):
    """Fake elevation: sin/cos terrain, no network."""
    return [
        math.sin(math.radians(lat * 10)) * math.cos(math.radians(lon * 10)) * 500 + 600
        for lat, lon in locations
    ]


def _make_grid(grid_size: int = 10) -> ElevationGrid:
    lons, lats = np.meshgrid(
        np.linspace(10.5, 10.9, grid_size), np.linspace(59.7, 60.1, grid_size)
    )
    elev = np.random.default_rng(42).uniform(100, 800, (grid_size, grid_size))
    return ElevationGrid(
        lons=lons, lats=lats, elev=elev, center=(59.9, 10.7), zoom=10, grid_size=grid_size
    )


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


@patch("memory_lane.plot_utils.map._fetch_elevations", side_effect=_synthetic_elevations)
def test_get_elevation_grid_cache_hit(mock_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr("memory_lane.plot_utils.map.CACHE_DIR", tmp_path)

    get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)
    call_count_after_first = mock_fetch.call_count

    # Second call — should load from cache, no new API call
    get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)
    assert mock_fetch.call_count == call_count_after_first


@patch("memory_lane.plot_utils.map._fetch_elevations", side_effect=_synthetic_elevations)
def test_get_elevation_grid_cache_miss_different_params(mock_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr("memory_lane.plot_utils.map.CACHE_DIR", tmp_path)

    get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)
    count_1 = mock_fetch.call_count

    # Different zoom → cache miss → new fetch
    get_elevation_grid(center=(59.9, 10.7), zoom=8, grid_size=10)
    assert mock_fetch.call_count > count_1


# ---------------------------------------------------------------------------
# draw_map
# ---------------------------------------------------------------------------


def test_draw_map_runs():
    grid = _make_grid()
    fig, ax = plt.subplots()
    draw_map(ax, grid, palette=PALETTE_SEPIA)
    plt.close(fig)


@pytest.mark.parametrize("palette", [PALETTE_SEPIA, PALETTE_INK, PALETTE_BLUEPRINT])
def test_draw_map_all_palettes(palette):
    grid = _make_grid()
    fig, ax = plt.subplots()
    draw_map(ax, grid, palette=palette)
    plt.close(fig)


def test_draw_map_custom_palette():
    grid = _make_grid()
    custom = dict(bg="#000000", line_color="#ffffff", point_color="#ff0000", title_color="#cccccc")
    fig, ax = plt.subplots()
    draw_map(ax, grid, palette=custom)
    plt.close(fig)


# ---------------------------------------------------------------------------
# plot_points
# ---------------------------------------------------------------------------


def test_plot_points_runs():
    fig, ax = plt.subplots()
    plot_points(ax, [(59.91, 10.75), (59.88, 10.65)], palette=PALETTE_SEPIA)
    plt.close(fig)


def test_plot_points_empty():
    fig, ax = plt.subplots()
    plot_points(ax, [], palette=PALETTE_INK)  # should not raise
    plt.close(fig)


# ---------------------------------------------------------------------------
# Integration: draw_map + plot_points + save (caller owns everything)
# ---------------------------------------------------------------------------


@patch("memory_lane.plot_utils.map._fetch_elevations", side_effect=_synthetic_elevations)
def test_full_workflow_saves_png(mock_fetch, tmp_path, monkeypatch):
    monkeypatch.setattr("memory_lane.plot_utils.map.CACHE_DIR", tmp_path / "cache")

    grid = get_elevation_grid(center=(59.9, 10.7), zoom=10, grid_size=10)

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(PALETTE_SEPIA["bg"])
    ax.set_facecolor(PALETTE_SEPIA["bg"])

    draw_map(ax, grid, palette=PALETTE_SEPIA)
    plot_points(ax, [(59.91, 10.75)], palette=PALETTE_SEPIA)

    out = tmp_path / "map.png"
    fig.tight_layout()
    fig.savefig(str(out), dpi=72, bbox_inches="tight")
    plt.close(fig)

    assert out.exists()
    assert out.stat().st_size > 1000
