"""
Artistic elevation map using contour lines.
No country borders — pure terrain art.

Data sources:
- Elevation: OpenTopoData API (https://www.opentopodata.org/)
- Water: Natural Earth via cartopy (bundled, cached locally)

Typical usage::

    import matplotlib.pyplot as plt
    from memory_lane.plot_utils.map import (
        get_elevation_grid,
        draw_map,
        draw_water,
        plot_points,
        PALETTE_SEPIA,
    )

    grid = get_elevation_grid(center=(59.9, 10.7), zoom=10)
    p = PALETTE_SEPIA

    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_facecolor(p.bg)
    ax.set_facecolor(p.bg)

    draw_map(ax, grid, color=p.line_color, bg=p.bg)
    draw_water(ax, center=(59.9, 10.7), zoom=10, color=p.bg, edgecolor=p.line_color)
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

import cartopy.feature as cfeature  # type: ignore
import numpy as np
import requests
from matplotlib import patheffects
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
from shapely.geometry import MultiPolygon, Polygon, box

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

OPENTOPODATA_BASE = "https://api.opentopodata.org/v1"
API_BATCH_SIZE = 100
API_RATE_LIMIT = 1.1  # seconds between batches (free tier: 1 req/s)
CACHE_DIR = Path.home() / ".cache" / "memory_lane" / "elevation"

# Dataset priority: best resolution first, widest coverage last
# (lat_min, lat_max, lon_min, lon_max, dataset_name)
_DATASET_COVERAGE: list[tuple[float, float, float, float, str]] = [
    (34.0, 72.0, -25.0, 45.0, "eudem25m"),  # Europe, 25m
    (-60.0, 60.0, -180.0, 180.0, "srtm90m"),  # Global within 60°, 90m
    (-83.0, 83.0, -180.0, 180.0, "aster30m"),  # Global, 30m
]


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
    datasets: list[str]  # datasets actually used, in order of application


# ---------------------------------------------------------------------------
# Private helpers — elevation
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
        datasets=m.get("datasets", []),
    )


def _save_cache(key: str, grid: ElevationGrid, bounds: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(str(CACHE_DIR / f"{key}.npy"), grid.elev)
    meta = {
        "center": list(grid.center),
        "zoom": grid.zoom,
        "grid_size": grid.grid_size,
        "datasets": grid.datasets,
        **bounds,
    }
    with (CACHE_DIR / f"{key}.json").open("w") as f:
        json.dump(meta, f)


def _dataset_priority(lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> list[str]:
    """Return ordered list of datasets to try for this bbox, best-first."""
    datasets = []
    for dlat_min, dlat_max, dlon_min, dlon_max, name in _DATASET_COVERAGE:
        if (
            lat_min >= dlat_min
            and lat_max <= dlat_max
            and lon_min >= dlon_min
            and lon_max <= dlon_max
        ):
            datasets.append(name)
    if "aster30m" not in datasets:
        datasets.append("aster30m")
    return datasets


def _fetch_elevations(locations: list[tuple[float, float]], dataset: str) -> list[Optional[float]]:
    """Fetch elevations from OpenTopoData API for a specific dataset, batched."""
    url = f"{OPENTOPODATA_BASE}/{dataset}"
    results: list[Optional[float]] = []
    for i in range(0, len(locations), API_BATCH_SIZE):
        batch = locations[i : i + API_BATCH_SIZE]
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in batch)
        resp = requests.get(url, params={"locations": loc_str}, timeout=30)
        resp.raise_for_status()
        for r in resp.json()["results"]:
            results.append(r.get("elevation"))
        if i + API_BATCH_SIZE < len(locations):
            time.sleep(API_RATE_LIMIT)
    return results


def _fetch_elevations_with_fallback(
    locations: list[tuple[float, float]],
    datasets: list[str],
) -> tuple[list[float], list[str]]:
    """Fetch elevations using dataset priority, falling back for null points.

    Returns (elevations, datasets_used).
    """
    results: list[Optional[float]] = [None] * len(locations)
    remaining_idx = list(range(len(locations)))
    datasets_used: list[str] = []

    for dataset in datasets:
        if not remaining_idx:
            break
        batch = [locations[i] for i in remaining_idx]
        n_batches = math.ceil(len(batch) / API_BATCH_SIZE)
        print(f"Fetching {len(batch)} elevation points via {dataset} ({n_batches} requests)...")
        fetched = _fetch_elevations(batch, dataset=dataset)
        datasets_used.append(dataset)
        still_null = []
        for i, val in zip(remaining_idx, fetched):
            if val is not None:
                results[i] = val
            else:
                still_null.append(i)
        remaining_idx = still_null

    for i in remaining_idx:
        results[i] = 0.0

    return [r if r is not None else 0.0 for r in results], datasets_used


# ---------------------------------------------------------------------------
# Private helpers — water
# ---------------------------------------------------------------------------


def _shapely_to_mpl_path(geom) -> Optional[MplPath]:
    """Convert shapely Polygon or MultiPolygon to matplotlib Path."""
    if geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    else:
        return None

    verts = []
    codes = []
    for poly in polys:
        ext = list(poly.exterior.coords)
        verts += ext + [ext[0]]
        codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(ext) - 1) + [MplPath.CLOSEPOLY]
        for interior in poly.interiors:
            ring = list(interior.coords)
            verts += ring + [ring[0]]
            codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(ring) - 1) + [MplPath.CLOSEPOLY]

    return MplPath(verts, codes)


def _draw_natural_earth_feature(
    ax: Axes,
    feature: cfeature.NaturalEarthFeature,
    bbox,
    color: str,
    edgecolor: str,
    zorder: int,
    alpha: float = 0.9,
    linewidth: float = 0.5,
) -> None:
    """Clip a cartopy NaturalEarth feature to bbox and draw onto ax."""
    for geom in feature.geometries():
        try:
            clipped = geom.intersection(bbox)
        except Exception:
            continue
        if clipped.is_empty:
            continue
        mpl_path = _shapely_to_mpl_path(clipped)
        if mpl_path is None:
            continue
        ax.add_patch(
            PathPatch(
                mpl_path,
                facecolor=color,
                edgecolor=edgecolor,
                linewidth=linewidth,
                alpha=alpha,
                zorder=zorder,
                transform=ax.transData,
            )
        )


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

    datasets = _dataset_priority(lat_min, lat_max, lon_min, lon_max)
    elevations_flat, datasets_used = _fetch_elevations_with_fallback(locations, datasets)

    elev = np.array(elevations_flat, dtype=float).reshape(grid_size, grid_size)

    grid = ElevationGrid(
        lons=grid_lons,
        lats=grid_lats,
        elev=elev,
        center=center,
        zoom=zoom,
        grid_size=grid_size,
        datasets=datasets_used,
    )
    bounds = dict(lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max)
    _save_cache(key, grid, bounds)
    return grid


def draw_map(
    ax: Axes,
    grid: ElevationGrid,
    color: str = PALETTE_SEPIA.line_color,
    bg: str = PALETTE_SEPIA.bg,
    hypsometric: bool = True,
) -> None:
    """Draw terrain elevation onto ax.

    Renders hypsometric tint (colour-filled elevation bands) with sparse
    contour lines overlaid — major every 100 m (labelled), minor every 50 m.

    Caller is responsible for: fig/ax creation, facecolor, spines, save.

    Parameters
    ----------
    ax : matplotlib Axes
    grid : ElevationGrid from get_elevation_grid()
    color : contour line color
    bg : background color; also used as the lowest-elevation tint
    hypsometric : if True (default) draw colour-filled elevation bands under
        the contours; if False draw contour lines only (sparse style)
    """
    elev = grid.elev
    elev_min = np.nanmin(elev)
    elev_max = np.nanmax(elev)

    major_step = 100.0
    minor_step = 50.0
    major_levels = np.arange(np.ceil(elev_min / major_step) * major_step, elev_max, major_step)
    minor_levels = np.arange(np.ceil(elev_min / minor_step) * minor_step, elev_max, minor_step)
    minor_levels = minor_levels[~np.isin(minor_levels, major_levels)]

    if hypsometric:
        # Sepia-family gradient: warm lowland → cool-grey highland
        colors_hyp = [bg, "#d4c5a9", "#b8a882", "#8a7a5a", "#7a8070", "#d0d4d0"]
        cmap = LinearSegmentedColormap.from_list("hyp", colors_hyp)
        ax.contourf(
            grid.lons,
            grid.lats,
            elev,
            levels=40,
            cmap=cmap,
            alpha=0.80,
            zorder=1,
        )

    if len(minor_levels):
        ax.contour(
            grid.lons,
            grid.lats,
            elev,
            levels=minor_levels,
            colors=color,
            linewidths=0.35,
            alpha=0.30,
            zorder=2,
        )
    # if len(major_levels):
    # cs = ax.contour(
    #     grid.lons, grid.lats, elev,
    #     levels=major_levels, colors=color,
    #     linewidths=0.9, alpha=0.80, zorder=2,
    # )
    # ax.clabel(cs, fmt="%dm", fontsize=6, colors=color, inline=True, inline_spacing=2)

    half = _zoom_to_degrees(grid.zoom)
    lat0, lon0 = grid.center
    ax.set_xlim(lon0 - half, lon0 + half)
    ax.set_ylim(lat0 - half, lat0 + half)
    ax.set_aspect("equal")


def draw_water(
    ax: Axes,
    center: tuple[float, float],
    zoom: int,
    color: str = PALETTE_SEPIA.bg,
    edgecolor: str = PALETTE_SEPIA.line_color,
) -> None:
    """Draw ocean and lakes from Natural Earth data onto ax.

    Uses cartopy's bundled Natural Earth shapefiles — no API calls.
    Cartopy downloads and caches the shapefiles on first use
    (~/.local/share/cartopy).

    Draw after draw_map so water sits on top of contours.

    Parameters
    ----------
    ax : matplotlib Axes
    center : (lat, lon) — same as get_elevation_grid()
    zoom : same zoom level — determines bbox
    color : fill color for ocean and lakes
    edgecolor : outline color
    """
    half = _zoom_to_degrees(zoom)
    lat0, lon0 = center
    bbox = box(lon0 - half, lat0 - half, lon0 + half, lat0 + half)

    ocean = cfeature.NaturalEarthFeature(
        "physical",
        "ocean",
        "10m",
        facecolor=color,
        edgecolor=edgecolor,
    )
    lakes = cfeature.NaturalEarthFeature(
        "physical",
        "lakes",
        "10m",
        facecolor=color,
        edgecolor=edgecolor,
    )

    _draw_natural_earth_feature(ax, ocean, bbox, color=color, edgecolor=edgecolor, zorder=3)
    _draw_natural_earth_feature(ax, lakes, bbox, color=color, edgecolor=edgecolor, zorder=3)


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
        ax.plot(lons, lats, color=edgecolor, linewidth=3.0, alpha=0.9, zorder=4)
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
