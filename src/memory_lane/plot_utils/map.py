"""
Artistic elevation map using contour lines.
No country borders — pure terrain art.

Data: OpenTopoData SRTM 90m API (https://www.opentopodata.org/)

Typical usage::

    import matplotlib.pyplot as plt
    from memory_lane.plot_utils.map import (
        get_elevation_grid,
        draw_map,
        plot_points,
        PALETTE_SEPIA,
    )

    grid = get_elevation_grid(center=(59.9, 10.7), zoom=10)
    p = PALETTE_SEPIA

    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_facecolor(p.bg)
    ax.set_facecolor(p.bg)

    draw_map(ax, grid, color=p.line_color, bg=p.bg)
    plot_points(ax, [(59.91, 10.75)], color=p.point_color, edgecolor=p.bg)

    fig.tight_layout()
    fig.savefig("map.png", dpi=150, bbox_inches="tight")
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from matplotlib import patheffects
from matplotlib.axes import Axes

# ---------------------------------------------------------------------------
# Palette dataclass
# ---------------------------------------------------------------------------


@dataclass
class Palette:
    bg: str
    line_color: str
    point_color: str
    title_color: str


PALETTE_SEPIA = Palette(
    bg="#f5f0e8",
    line_color="#5c4a2a",
    point_color="#8b2020",
    title_color="#3a2a10",
)

PALETTE_INK = Palette(
    bg="#ffffff",
    line_color="#1a1a1a",
    point_color="#cc0000",
    title_color="#000000",
)

PALETTE_BLUEPRINT = Palette(
    bg="#1a2a4a",
    line_color="#a8c8f0",
    point_color="#ffcc00",
    title_color="#d0e8ff",
)

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

OPENTOPODATA_URL = "https://api.opentopodata.org/v1/srtm90m"
API_BATCH_SIZE = 100
API_RATE_LIMIT = 1.1  # seconds between batches (free tier: 1 req/s)
CACHE_DIR = Path.home() / ".cache" / "memory_lane" / "elevation"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class ElevationGrid:
    lons: np.ndarray  # 2D array, shape (grid_size, grid_size)
    lats: np.ndarray  # 2D array
    elev: np.ndarray  # 2D array, metres
    center: tuple[float, float]
    zoom: int
    grid_size: int


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _zoom_to_degrees(zoom: int) -> float:
    """zoom level → approximate half-span in degrees."""
    return 45.0 / (2 ** (zoom - 1))


def _cache_key(center: tuple[float, float], zoom: int, grid_size: int) -> str:
    lat, lon = round(center[0], 5), round(center[1], 5)
    raw = f"{lat}_{lon}_{zoom}_{grid_size}"
    return hashlib.md5(raw.encode()).hexdigest()


def _load_cache(key: str) -> Optional[ElevationGrid]:
    npy = CACHE_DIR / f"{key}.npy"
    meta = CACHE_DIR / f"{key}.json"
    if not npy.exists() or not meta.exists():
        return None
    elev = np.load(str(npy))
    with meta.open() as f:
        m = json.load(f)
    grid_size = m["grid_size"]
    lat_min, lat_max = m["lat_min"], m["lat_max"]
    lon_min, lon_max = m["lon_min"], m["lon_max"]
    lons, lats = np.meshgrid(
        np.linspace(lon_min, lon_max, grid_size),
        np.linspace(lat_min, lat_max, grid_size),
    )
    return ElevationGrid(
        lons=lons,
        lats=lats,
        elev=elev,
        center=tuple(m["center"]),  # type: ignore[arg-type]
        zoom=m["zoom"],
        grid_size=grid_size,
    )


def _save_cache(key: str, grid: ElevationGrid, bounds: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(str(CACHE_DIR / f"{key}.npy"), grid.elev)
    meta = {
        "center": list(grid.center),
        "zoom": grid.zoom,
        "grid_size": grid.grid_size,
        **bounds,
    }
    with (CACHE_DIR / f"{key}.json").open("w") as f:
        json.dump(meta, f)


def _fetch_elevations(locations: list[tuple[float, float]]) -> list[Optional[float]]:
    """Fetch elevations from OpenTopoData API, batched."""
    results: list[Optional[float]] = []
    for i in range(0, len(locations), API_BATCH_SIZE):
        batch = locations[i : i + API_BATCH_SIZE]
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in batch)
        resp = requests.get(OPENTOPODATA_URL, params={"locations": loc_str}, timeout=30)
        resp.raise_for_status()
        for r in resp.json()["results"]:
            results.append(r.get("elevation"))
        if i + API_BATCH_SIZE < len(locations):
            time.sleep(API_RATE_LIMIT)
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_elevation_grid(
    center: tuple[float, float],
    zoom: int,
    grid_size: int = 50,
) -> ElevationGrid:
    """Fetch or load cached elevation grid.

    Parameters
    ----------
    center : (lat, lon)
    zoom : 1-18, higher = closer
    grid_size : NxN sample density (more = finer contours, more API calls)

    Returns
    -------
    ElevationGrid dataclass
    """
    key = _cache_key(center, zoom, grid_size)
    cached = _load_cache(key)
    if cached is not None:
        return cached

    half = _zoom_to_degrees(zoom)
    lat0, lon0 = center
    lat_min, lat_max = lat0 - half, lat0 + half
    lon_min, lon_max = lon0 - half, lon0 + half

    lats_1d = np.linspace(lat_min, lat_max, grid_size)
    lons_1d = np.linspace(lon_min, lon_max, grid_size)
    grid_lons, grid_lats = np.meshgrid(lons_1d, lats_1d)

    locations = [
        (grid_lats[r, c], grid_lons[r, c]) for r in range(grid_size) for c in range(grid_size)
    ]

    n_batches = math.ceil(len(locations) / API_BATCH_SIZE)
    print(f"Fetching {len(locations)} elevation points ({n_batches} API requests)...")
    elevations_flat = _fetch_elevations(locations)

    elev = np.array([e if e is not None else 0.0 for e in elevations_flat], dtype=float).reshape(
        grid_size, grid_size
    )

    grid = ElevationGrid(
        lons=grid_lons,
        lats=grid_lats,
        elev=elev,
        center=center,
        zoom=zoom,
        grid_size=grid_size,
    )
    bounds = dict(lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max)
    _save_cache(key, grid, bounds)
    return grid


def draw_map(
    ax: Axes,
    grid: ElevationGrid,
    color: str = PALETTE_SEPIA.line_color,
    bg: str = PALETTE_SEPIA.bg,
) -> None:
    """Draw contour lines for terrain elevation onto ax.

    Caller is responsible for: fig/ax creation, facecolor, spines, save.

    Parameters
    ----------
    ax : matplotlib Axes
    grid : ElevationGrid from get_elevation_grid()
    color : contour line color
    bg : background color (used for label halos)
    """
    elev_min = np.nanmin(grid.elev)
    elev_max = np.nanmax(grid.elev)
    elev_range = elev_max - elev_min if elev_max > elev_min else 1.0

    n_levels = max(8, min(40, int(elev_range / 20)))
    levels = np.linspace(elev_min, elev_max, n_levels)

    ax.contour(
        grid.lons,
        grid.lats,
        grid.elev,
        levels=levels,
        colors=color,
        linewidths=0.4,
        alpha=0.5,
    )
    cs_major = ax.contour(
        grid.lons,
        grid.lats,
        grid.elev,
        levels=levels[::5],
        colors=color,
        linewidths=1.0,
        alpha=0.85,
    )
    ax.clabel(
        cs_major,
        fmt="%dm",
        fontsize=6,
        colors=color,
        inline=True,
        inline_spacing=2,
    )

    half = _zoom_to_degrees(grid.zoom)
    lat0, lon0 = grid.center
    ax.set_xlim(lon0 - half, lon0 + half)
    ax.set_ylim(lat0 - half, lat0 + half)
    ax.set_aspect("equal")


def plot_points(
    ax: Axes,
    points: list[tuple[float, float]],
    color: str = PALETTE_SEPIA.point_color,
    edgecolor: str = PALETTE_SEPIA.bg,
    size: float = 80,
    labels: list[str] | None = None,
    connect: bool = False,
) -> None:
    """Overlay GPS points onto ax.

    Parameters
    ----------
    ax : matplotlib Axes
    points : list of (lat, lon)
    color : marker fill color and label/line color
    edgecolor : marker edge color; also used as halo for lines and labels
    size : marker size
    labels : optional list of strings, one per point; empty string skips label
    connect : if True, draw a line through points in order
    """
    if not points:
        return

    if labels is not None and len(labels) != len(points):
        raise ValueError(f"labels length {len(labels)} != points length {len(points)}")

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]

    if connect:
        # halo line underneath
        ax.plot(lons, lats, color=edgecolor, linewidth=3.0, alpha=0.9, zorder=3)
        ax.plot(lons, lats, color=color, linewidth=1.0, alpha=0.7, zorder=4)

    ax.scatter(
        lons,
        lats,
        color=color,
        s=size,
        zorder=5,
        linewidths=1.2,
        edgecolors=edgecolor,
    )

    if labels:
        for lat, lon, label in zip(lats, lons, labels):
            if not label:
                continue
            ax.annotate(
                label,
                xy=(lon, lat),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                color=color,
                zorder=6,
                path_effects=[patheffects.withStroke(linewidth=2.5, foreground=edgecolor)],
            )
